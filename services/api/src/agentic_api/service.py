"""Application use cases with enforceable data-governance decisions."""

import re
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from agentic_governance.models import (
    DataCategory,
    ProcessingContext,
    ProcessingOperation,
    ProcessingPurpose,
)
from agentic_governance.ports import DataClassifier, PolicyDecisionPoint
from agentic_runtime import EvaluationGateBlocked, PromptInjectionBlocked
from agentic_runtime.models import PlanningInput

from agentic_api.domain import Principal, Role, Workflow
from agentic_api.errors import (
    ApprovalExpired,
    ComplianceOverlayUnavailable,
    DataProcessingDenied,
    EvaluationGateRejected,
    IdempotencyConflict,
    InvalidWorkflowState,
    NoPendingTask,
    PermissionDenied,
    PromptInjectionRejected,
    WorkflowNotFound,
)
from agentic_api.execution import (
    ExecutionTask,
    create_approval_decision,
    create_execution_task,
    create_tool_proposal,
)
from agentic_api.ports import (
    AgentRuntime,
    AuditSink,
    TaskQueue,
    ToolExecutor,
    WorkflowRepository,
)


class WorkflowService:
    """Orchestrate request creation and resource-aware access policy."""

    def __init__(
        self,
        repository: WorkflowRepository,
        audit: AuditSink,
        runtime: AgentRuntime,
        classifier: DataClassifier,
        policy: PolicyDecisionPoint,
        task_queue: TaskQueue,
        tool_executor: ToolExecutor,
        id_factory: Callable[[], str] | None = None,
        now_factory: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._audit = audit
        self._runtime = runtime
        self._classifier = classifier
        self._policy = policy
        self._task_queue = task_queue
        self._tool_executor = tool_executor
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self._now_factory = now_factory or (lambda: datetime.now(UTC))

    def create(
        self,
        *,
        principal: Principal,
        request: str,
        requested_locale: str,
        idempotency_key: str,
        correlation_id: str,
        declared_categories: set[DataCategory] | None = None,
        purpose: ProcessingPurpose = ProcessingPurpose.DELIVERY_PLANNING,
        jurisdiction: str = "US",
        overlay_ids: tuple[str, ...] = ("common-us-baseline",),
    ) -> Workflow:
        if not principal.roles.intersection({Role.REQUESTER, Role.ADMINISTRATOR}):
            self._audit.record(
                action="workflow.create",
                outcome="denied",
                subject=principal.subject,
                resource_id=None,
                correlation_id=correlation_id,
            )
            raise PermissionDenied("The current role cannot create service requests.")

        normalized_request = re.sub(r"\s+", " ", request).strip()
        if set(overlay_ids) != {"common-us-baseline"}:
            raise ComplianceOverlayUnavailable(
                "Only the reviewed common-us-baseline overlay is active in this phase."
            )
        profile = self._classifier.classify(normalized_request, declared_categories)
        processing_context = ProcessingContext(
            subjectId=principal.subject,
            purpose=purpose,
            operation=ProcessingOperation.WORKFLOW_INTAKE,
            provider="local-api",
            jurisdiction=jurisdiction,
            dataProfile=profile,
            overlayIds=overlay_ids,
        )
        decision = self._policy.evaluate(processing_context)
        self._audit.record(
            action="data_processing.workflow_intake",
            outcome=decision.outcome.value,
            subject=principal.subject,
            resource_id=None,
            correlation_id=correlation_id,
        )
        if not decision.execution_allowed:
            raise DataProcessingDenied(decision.reasons[0])
        workflow = Workflow.receive(
            workflow_id=self._id_factory(),
            owner_id=principal.subject,
            request=normalized_request,
            requested_locale=requested_locale.lower(),
            correlation_id=correlation_id,
            processing_context=processing_context,
            governance_decision=decision,
        )
        stored = self._repository.create(workflow, idempotency_key)
        self._audit.record(
            action="workflow.create",
            outcome="accepted",
            subject=principal.subject,
            resource_id=stored.workflow_id,
            correlation_id=correlation_id,
        )
        return stored

    def get(self, *, principal: Principal, workflow_id: str, correlation_id: str) -> Workflow:
        workflow = self._repository.get(workflow_id)
        can_inspect_any = bool(
            principal.roles.intersection({Role.REVIEWER, Role.OPERATOR, Role.ADMINISTRATOR})
        )
        if workflow is None or (workflow.owner_id != principal.subject and not can_inspect_any):
            self._audit.record(
                action="workflow.read",
                outcome="not_found",
                subject=principal.subject,
                resource_id=workflow_id,
                correlation_id=correlation_id,
            )
            raise WorkflowNotFound("The workflow does not exist or is not accessible.")

        self._audit.record(
            action="workflow.read",
            outcome="allowed",
            subject=principal.subject,
            resource_id=workflow_id,
            correlation_id=correlation_id,
        )
        return workflow

    def plan(self, *, principal: Principal, workflow_id: str, correlation_id: str) -> Workflow:
        """Run deterministic planning once for an owned workflow."""

        workflow = self._repository.get(workflow_id)
        if workflow is None or (
            workflow.owner_id != principal.subject and Role.ADMINISTRATOR not in principal.roles
        ):
            self._audit.record(
                action="workflow.plan",
                outcome="not_found",
                subject=principal.subject,
                resource_id=workflow_id,
                correlation_id=correlation_id,
            )
            raise WorkflowNotFound("The workflow does not exist or is not accessible.")
        if workflow.planning_result is not None:
            return workflow
        if workflow.status != "received":
            raise InvalidWorkflowState("Only a received workflow can be planned.")

        planning_context = workflow.processing_context.model_copy(
            update={
                "operation": ProcessingOperation.AGENT_PLANNING,
                "provider": "deterministic-local",
            }
        )
        decision = self._policy.evaluate(planning_context)
        self._audit.record(
            action="data_processing.agent_planning",
            outcome=decision.outcome.value,
            subject=principal.subject,
            resource_id=workflow_id,
            correlation_id=correlation_id,
        )
        if not decision.execution_allowed:
            raise DataProcessingDenied(decision.reasons[0])

        try:
            result = self._runtime.plan(
                PlanningInput(
                    workflow_id=workflow.workflow_id,
                    owner_id=workflow.owner_id,
                    request=workflow.request,
                    requested_locale=workflow.requested_locale,
                    correlation_id=correlation_id,
                )
            )
        except PromptInjectionBlocked as error:
            self._audit.record(
                action="guardrail.input",
                outcome="blocked",
                subject=principal.subject,
                resource_id=workflow_id,
                correlation_id=correlation_id,
            )
            raise PromptInjectionRejected(str(error)) from error
        except EvaluationGateBlocked as error:
            self._audit.record(
                action="evaluation.planning_gate",
                outcome="failed",
                subject=principal.subject,
                resource_id=workflow_id,
                correlation_id=correlation_id,
            )
            raise EvaluationGateRejected(str(error)) from error
        proposal = create_tool_proposal(workflow.workflow_id, result, self._now_factory())
        planned = workflow.apply_planning_result(result, decision, proposal)
        stored = self._repository.update(planned, expected_state_version=workflow.state_version)
        self._audit.record(
            action="workflow.plan",
            outcome="evaluated",
            subject=principal.subject,
            resource_id=workflow_id,
            correlation_id=correlation_id,
        )
        return stored

    def decide_approval(
        self,
        *,
        principal: Principal,
        workflow_id: str,
        decision: Literal["approved", "rejected"],
        reason: str,
        idempotency_key: str,
        correlation_id: str,
    ) -> Workflow:
        """Bind a one-time human decision to the immutable tool proposal."""

        if not principal.roles.intersection({Role.REVIEWER, Role.ADMINISTRATOR}):
            self._audit.record(
                action="workflow.approval",
                outcome="denied",
                subject=principal.subject,
                resource_id=None,
                correlation_id=correlation_id,
            )
            raise PermissionDenied("The current role cannot decide approval requests.")

        workflow = self._repository.get(workflow_id)
        if workflow is None:
            raise WorkflowNotFound("The workflow does not exist or is not accessible.")
        if workflow.owner_id == principal.subject:
            self._audit.record(
                action="workflow.approval",
                outcome="self_approval_denied",
                subject=principal.subject,
                resource_id=workflow_id,
                correlation_id=correlation_id,
            )
            raise PermissionDenied("A requester cannot approve their own workflow.")

        if workflow.approval_decision is not None:
            existing = workflow.approval_decision
            if existing.idempotency_key != idempotency_key:
                raise InvalidWorkflowState("The approval request has already been decided.")
            if existing.decision != decision:
                raise IdempotencyConflict(
                    "The idempotency key was already used for another approval decision."
                )
            if decision == "approved" and workflow.action_proposal is not None:
                self._task_queue.enqueue(
                    create_execution_task(
                        workflow.workflow_id, workflow.action_proposal.proposal_digest
                    )
                )
            return workflow

        if workflow.status != "awaiting_approval" or workflow.action_proposal is None:
            raise InvalidWorkflowState("Only a pending proposal can be decided.")

        now = self._now_factory()
        if now > workflow.action_proposal.expires_at:
            expired = workflow.expire(now)
            self._repository.update(expired, expected_state_version=workflow.state_version)
            self._audit.record(
                action="workflow.approval",
                outcome="expired",
                subject=principal.subject,
                resource_id=workflow_id,
                correlation_id=correlation_id,
            )
            raise ApprovalExpired("The proposal expired before it could be decided.")

        approval = create_approval_decision(
            proposal=workflow.action_proposal,
            reviewer_id=principal.subject,
            decision=decision,
            reason=reason,
            idempotency_key=idempotency_key,
            now=now,
        )
        decided = workflow.record_approval(approval, now)
        stored = self._repository.update(decided, expected_state_version=workflow.state_version)
        if decision == "approved":
            self._task_queue.enqueue(
                create_execution_task(
                    workflow.workflow_id, workflow.action_proposal.proposal_digest
                )
            )
        self._audit.record(
            action="workflow.approval",
            outcome=decision,
            subject=principal.subject,
            resource_id=workflow_id,
            correlation_id=correlation_id,
        )
        return stored

    def process_next_task(self, *, principal: Principal, correlation_id: str) -> Workflow:
        """Process one queued delivery through the simulated local worker boundary."""

        if not principal.roles.intersection({Role.OPERATOR, Role.ADMINISTRATOR}):
            self._audit.record(
                action="task.process",
                outcome="denied",
                subject=principal.subject,
                resource_id=None,
                correlation_id=correlation_id,
            )
            raise PermissionDenied("The current role cannot process execution tasks.")
        task = self._task_queue.claim_next()
        if task is None:
            raise NoPendingTask("No approved execution task is waiting.")
        return self.execute_task(task=task, actor=principal.subject, correlation_id=correlation_id)

    def execute_task(self, *, task: ExecutionTask, actor: str, correlation_id: str) -> Workflow:
        """Consume an at-least-once task without duplicating its side effect."""

        workflow = self._repository.get(task.workflow_id)
        if workflow is None:
            raise WorkflowNotFound("The task workflow does not exist.")
        if workflow.status == "completed" and workflow.execution_result is not None:
            if workflow.execution_result.proposal_digest != task.proposal_digest:
                raise IdempotencyConflict("The task does not match the completed proposal.")
            self._task_queue.complete(task.task_id)
            return workflow
        if workflow.action_proposal is None or workflow.approval_decision is None:
            raise InvalidWorkflowState("The task lacks a bound approval proposal.")
        proposal = workflow.action_proposal
        if (
            proposal.proposal_digest != task.proposal_digest
            or workflow.approval_decision.proposal_digest != task.proposal_digest
        ):
            raise InvalidWorkflowState("The task does not match the approved proposal digest.")

        now = self._now_factory()
        if workflow.status == "approved":
            if now > workflow.approval_decision.expires_at:
                expired = workflow.expire(now)
                self._repository.update(expired, expected_state_version=workflow.state_version)
                self._task_queue.complete(task.task_id)
                self._audit.record(
                    action="task.process",
                    outcome="approval_expired",
                    subject=actor,
                    resource_id=workflow.workflow_id,
                    correlation_id=correlation_id,
                )
                raise ApprovalExpired("The approval expired before task execution.")
            execution_context = workflow.processing_context.model_copy(
                update={
                    "operation": ProcessingOperation.TOOL_EXECUTION,
                    "provider": "deterministic-local",
                }
            )
            governance = self._policy.evaluate(execution_context)
            self._audit.record(
                action="data_processing.tool_execution",
                outcome=governance.outcome.value,
                subject=actor,
                resource_id=workflow.workflow_id,
                correlation_id=correlation_id,
            )
            if not governance.execution_allowed:
                raise DataProcessingDenied(governance.reasons[0])
            workflow = self._repository.update(
                workflow.begin_execution(governance, execution_context, now),
                expected_state_version=workflow.state_version,
            )
        elif workflow.status != "executing":
            raise InvalidWorkflowState("Only approved work can be executed.")

        result = self._tool_executor.execute(task, proposal, now)
        completed = workflow.complete_execution(result, now)
        stored = self._repository.update(completed, expected_state_version=workflow.state_version)
        self._task_queue.complete(task.task_id)
        self._audit.record(
            action="task.process",
            outcome="completed",
            subject=actor,
            resource_id=workflow.workflow_id,
            correlation_id=correlation_id,
        )
        return stored
