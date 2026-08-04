"""Approval, asynchronous delivery, expiry, and idempotency invariants."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from agentic_governance import BaselinePolicyEngine, DeterministicDataClassifier
from agentic_governance.models import (
    PolicyDecision,
    PolicyOutcome,
    ProcessingContext,
    ProcessingOperation,
)
from agentic_runtime import DeterministicAgentRuntime

from agentic_api.adapters import (
    InMemoryTaskQueue,
    InMemoryWorkflowRepository,
    SimulatedTicketExecutor,
)
from agentic_api.domain import Principal, Role
from agentic_api.errors import (
    ApprovalExpired,
    DataProcessingDenied,
    IdempotencyConflict,
    InvalidWorkflowState,
    WorkflowNotFound,
)
from agentic_api.execution import (
    ExecutionTask,
    ToolExecutionResult,
    create_execution_task,
)
from agentic_api.service import WorkflowService


class StubAudit:
    def record(
        self,
        *,
        action: str,
        outcome: str,
        subject: str | None,
        resource_id: str | None,
        correlation_id: str,
    ) -> None:
        pass


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 4, 5, 12, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, minutes: int) -> None:
        self.now += timedelta(minutes=minutes)


class DenyToolPolicy:
    def evaluate(self, context: ProcessingContext) -> PolicyDecision:
        decision = BaselinePolicyEngine().evaluate(context)
        if context.operation == ProcessingOperation.TOOL_EXECUTION:
            return decision.model_copy(
                update={
                    "outcome": PolicyOutcome.DENY,
                    "execution_allowed": False,
                    "reasons": ("Tool execution is denied by the test policy.",),
                }
            )
        return decision


def service_fixture() -> tuple[
    WorkflowService,
    InMemoryWorkflowRepository,
    InMemoryTaskQueue,
    SimulatedTicketExecutor,
    Clock,
]:
    repository = InMemoryWorkflowRepository()
    queue = InMemoryTaskQueue()
    executor = SimulatedTicketExecutor()
    clock = Clock()
    service = WorkflowService(
        repository,
        StubAudit(),
        DeterministicAgentRuntime(),
        DeterministicDataClassifier(),
        BaselinePolicyEngine(),
        queue,
        executor,
        id_factory=lambda: "workflow-approval",
        now_factory=clock,
    )
    return service, repository, queue, executor, clock


REQUESTER = Principal("requester", "Requester", frozenset({Role.REQUESTER}))
REVIEWER = Principal("reviewer", "Reviewer", frozenset({Role.REVIEWER}))
OPERATOR = Principal("operator", "Operator", frozenset({Role.OPERATOR}))


def planned_workflow(service: WorkflowService) -> str:
    created = service.create(
        principal=REQUESTER,
        request="Prepare a deterministic delivery ticket proposal",
        requested_locale="en",
        idempotency_key="approval-create",
        correlation_id="approval-correlation",
    )
    return service.plan(
        principal=REQUESTER,
        workflow_id=created.workflow_id,
        correlation_id="approval-correlation",
    ).workflow_id


def test_proposal_expiry_is_persisted_and_creates_no_task() -> None:
    service, repository, queue, executor, clock = service_fixture()
    workflow_id = planned_workflow(service)
    clock.advance(31)

    with pytest.raises(ApprovalExpired, match="proposal expired"):
        service.decide_approval(
            principal=REVIEWER,
            workflow_id=workflow_id,
            decision="approved",
            reason="Reviewed after expiry.",
            idempotency_key="expired-decision",
            correlation_id="approval-correlation",
        )

    assert repository.get(workflow_id).status == "expired"  # type: ignore[union-attr]
    assert queue.claim_next() is None
    assert executor.executions == ()


def test_approval_expiry_blocks_execution_and_completes_the_task_delivery() -> None:
    service, repository, queue, executor, clock = service_fixture()
    workflow_id = planned_workflow(service)
    service.decide_approval(
        principal=REVIEWER,
        workflow_id=workflow_id,
        decision="approved",
        reason="Approved for local execution.",
        idempotency_key="approved-decision",
        correlation_id="approval-correlation",
    )
    clock.advance(16)

    with pytest.raises(ApprovalExpired, match="approval expired"):
        service.process_next_task(principal=OPERATOR, correlation_id="approval-correlation")

    assert repository.get(workflow_id).status == "expired"  # type: ignore[union-attr]
    assert queue.claim_next() is None
    assert executor.executions == ()


def test_duplicate_task_delivery_returns_one_execution_result() -> None:
    service, _repository, queue, executor, _clock = service_fixture()
    workflow_id = planned_workflow(service)
    approved = service.decide_approval(
        principal=REVIEWER,
        workflow_id=workflow_id,
        decision="approved",
        reason="Approved for deterministic execution.",
        idempotency_key="duplicate-decision",
        correlation_id="approval-correlation",
    )
    assert approved.action_proposal is not None
    task = create_execution_task(workflow_id, approved.action_proposal.proposal_digest)

    first = service.execute_task(
        task=task, actor=OPERATOR.subject, correlation_id="approval-correlation"
    )
    replay = service.execute_task(
        task=task, actor=OPERATOR.subject, correlation_id="approval-correlation"
    )

    assert replay == first
    assert len(executor.executions) == 1
    assert queue.claim_next() is None


def test_queue_and_executor_reject_idempotency_key_rebinding() -> None:
    queue = InMemoryTaskQueue()
    task = ExecutionTask(
        taskId="task-1",
        workflowId="workflow-1",
        proposalDigest="digest-1",
        idempotencyKey="execution-1",
    )
    queue.enqueue(task)
    assert queue.enqueue(task) == task
    delivered = queue.claim_next()
    assert delivered is not None and delivered.delivery_attempt == 1

    with pytest.raises(IdempotencyConflict, match="another proposal"):
        queue.enqueue(task.model_copy(update={"proposal_digest": "digest-2"}))

    executor = SimulatedTicketExecutor()
    service, repository, _service_queue, _executor, _clock = service_fixture()
    workflow_id = planned_workflow(service)
    workflow = repository.get(workflow_id)
    assert workflow is not None and workflow.action_proposal is not None
    first = executor.execute(task, workflow.action_proposal, datetime(2026, 1, 1, tzinfo=UTC))
    assert (
        executor.execute(task, workflow.action_proposal, datetime(2026, 1, 2, tzinfo=UTC)) == first
    )

    altered = workflow.action_proposal.model_copy(update={"proposal_digest": "digest-2"})
    with pytest.raises(IdempotencyConflict, match="another proposal"):
        executor.execute(task, altered, datetime(2026, 1, 2, tzinfo=UTC))


def test_invalid_tasks_fail_without_creating_side_effects() -> None:
    service, repository, _queue, executor, _clock = service_fixture()
    missing = ExecutionTask(
        taskId="missing-task",
        workflowId="missing",
        proposalDigest="missing",
        idempotencyKey="missing",
    )
    with pytest.raises(WorkflowNotFound):
        service.execute_task(task=missing, actor="worker", correlation_id="missing")

    created = service.create(
        principal=REQUESTER,
        request="Prepare another deterministic ticket proposal",
        requested_locale="en",
        idempotency_key="invalid-task-create",
        correlation_id="invalid-task",
    )
    task = ExecutionTask(
        taskId="invalid-task",
        workflowId=created.workflow_id,
        proposalDigest="invalid",
        idempotencyKey="invalid",
    )
    with pytest.raises(InvalidWorkflowState, match="bound approval"):
        service.execute_task(task=task, actor="worker", correlation_id="invalid-task")

    assert repository.get(created.workflow_id).status == "received"  # type: ignore[union-attr]
    assert executor.executions == ()


def test_completion_requires_an_approval_decision() -> None:
    service, repository, _queue, _executor, _clock = service_fixture()
    created = service.create(
        principal=REQUESTER,
        request="Prepare a completion invariant test",
        requested_locale="en",
        idempotency_key="completion-create",
        correlation_id="completion",
    )
    result = ToolExecutionResult(
        executionId="execution",
        ticketId="LOCAL-TEST",
        executedAt=datetime(2026, 1, 1, tzinfo=UTC),
        idempotencyKey="completion",
        proposalDigest="digest",
    )

    with pytest.raises(ValueError, match="approval decision"):
        repository.get(created.workflow_id).complete_execution(result)  # type: ignore[union-attr]


def test_tampered_proposal_and_approval_digests_are_rejected() -> None:
    service, repository, _queue, _executor, _clock = service_fixture()
    workflow_id = planned_workflow(service)
    approved = service.decide_approval(
        principal=REVIEWER,
        workflow_id=workflow_id,
        decision="approved",
        reason="Approved before tampering test.",
        idempotency_key="tamper-decision",
        correlation_id="tamper",
    )
    assert approved.action_proposal is not None
    task = create_execution_task(workflow_id, approved.action_proposal.proposal_digest)

    with pytest.raises(InvalidWorkflowState, match="proposal digest"):
        service.execute_task(
            task=task.model_copy(update={"proposal_digest": "altered"}),
            actor="worker",
            correlation_id="tamper",
        )

    assert approved.approval_decision is not None
    corrupted = replace(
        approved,
        approval_decision=approved.approval_decision.model_copy(
            update={"proposal_digest": "altered"}
        ),
    )
    repository.update(corrupted, expected_state_version=approved.state_version)
    with pytest.raises(InvalidWorkflowState, match="proposal digest"):
        service.execute_task(task=task, actor="worker", correlation_id="tamper")


def test_terminal_approved_proposal_cannot_execute() -> None:
    service, repository, _queue, _executor, _clock = service_fixture()
    workflow_id = planned_workflow(service)
    approved = service.decide_approval(
        principal=REVIEWER,
        workflow_id=workflow_id,
        decision="approved",
        reason="Approved before terminal-state test.",
        idempotency_key="terminal-decision",
        correlation_id="terminal",
    )
    assert approved.action_proposal is not None
    task = create_execution_task(workflow_id, approved.action_proposal.proposal_digest)
    terminal = replace(approved, status="rejected")
    repository.update(terminal, expected_state_version=approved.state_version)

    with pytest.raises(InvalidWorkflowState, match="Only approved"):
        service.execute_task(task=task, actor="worker", correlation_id="terminal")


def test_completed_workflow_rejects_a_different_task_digest() -> None:
    service, _repository, _queue, _executor, _clock = service_fixture()
    workflow_id = planned_workflow(service)
    approved = service.decide_approval(
        principal=REVIEWER,
        workflow_id=workflow_id,
        decision="approved",
        reason="Approved for completion mismatch test.",
        idempotency_key="complete-mismatch-decision",
        correlation_id="complete-mismatch",
    )
    assert approved.action_proposal is not None
    task = create_execution_task(workflow_id, approved.action_proposal.proposal_digest)
    service.execute_task(task=task, actor="worker", correlation_id="complete-mismatch")

    with pytest.raises(IdempotencyConflict, match="completed proposal"):
        service.execute_task(
            task=task.model_copy(update={"proposal_digest": "altered"}),
            actor="worker",
            correlation_id="complete-mismatch",
        )


def test_execution_time_policy_can_deny_the_tool_before_side_effect() -> None:
    _service, repository, queue, executor, clock = service_fixture()
    guarded = WorkflowService(
        repository,
        StubAudit(),
        DeterministicAgentRuntime(),
        DeterministicDataClassifier(),
        DenyToolPolicy(),
        queue,
        executor,
        id_factory=lambda: "workflow-approval",
        now_factory=clock,
    )
    workflow_id = planned_workflow(guarded)
    guarded.decide_approval(
        principal=REVIEWER,
        workflow_id=workflow_id,
        decision="approved",
        reason="Approved but subject to execution policy.",
        idempotency_key="deny-tool-decision",
        correlation_id="deny-tool",
    )

    with pytest.raises(DataProcessingDenied, match="denied by the test policy"):
        guarded.process_next_task(principal=OPERATOR, correlation_id="deny-tool")

    assert executor.executions == ()


def test_worker_can_resume_an_already_executing_task() -> None:
    service, repository, _queue, executor, clock = service_fixture()
    workflow_id = planned_workflow(service)
    approved = service.decide_approval(
        principal=REVIEWER,
        workflow_id=workflow_id,
        decision="approved",
        reason="Approved for interrupted worker test.",
        idempotency_key="resume-decision",
        correlation_id="resume",
    )
    assert approved.action_proposal is not None
    task = create_execution_task(workflow_id, approved.action_proposal.proposal_digest)
    context = approved.processing_context.model_copy(
        update={
            "operation": ProcessingOperation.TOOL_EXECUTION,
            "provider": "deterministic-local",
        }
    )
    governance = BaselinePolicyEngine().evaluate(context)
    executing = approved.begin_execution(governance, context, clock())
    repository.update(executing, expected_state_version=approved.state_version)

    completed = service.execute_task(task=task, actor="worker", correlation_id="resume")

    assert completed.status == "completed"
    assert len(executor.executions) == 1
