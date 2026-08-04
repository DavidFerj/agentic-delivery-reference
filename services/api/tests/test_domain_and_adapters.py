"""Focused tests for local adapter boundaries."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest
from agentic_governance import BaselinePolicyEngine, DeterministicDataClassifier
from agentic_governance.models import (
    EnforcementMode,
    PolicyDecision,
    PolicyOutcome,
    ProcessingContext,
    ProcessingOperation,
    ProcessingPurpose,
)
from agentic_runtime import DeterministicAgentRuntime
from agentic_runtime.models import PlanningInput

from agentic_api.adapters import (
    InMemoryTaskQueue,
    InMemoryWorkflowRepository,
    LocalIdentityProvider,
    SimulatedTicketExecutor,
)
from agentic_api.domain import Principal, Role, Workflow
from agentic_api.errors import DataProcessingDenied, InvalidWorkflowState
from agentic_api.execution import create_tool_proposal
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


class PlanningDenyPolicy:
    def evaluate(self, context: ProcessingContext) -> PolicyDecision:
        return PolicyDecision(
            decisionId="deny-planning",
            policyVersion="test-v1",
            outcome=PolicyOutcome.DENY,
            executionAllowed=False,
            enforcementMode=EnforcementMode.ENFORCE,
            classification=context.data_profile.classification,
            obligations=(),
            reasons=("Planning is denied by the test policy.",),
            retentionPolicy="test-only",
            overlayIds=context.overlay_ids,
        )


def governance(owner_id: str = "owner-1") -> tuple[ProcessingContext, PolicyDecision]:
    profile = DeterministicDataClassifier().classify("Prepare a deterministic plan")
    context = ProcessingContext(
        subjectId=owner_id,
        purpose=ProcessingPurpose.DELIVERY_PLANNING,
        operation=ProcessingOperation.WORKFLOW_INTAKE,
        provider="local-api",
        dataProfile=profile,
    )
    return context, BaselinePolicyEngine().evaluate(context)


def test_local_provider_recognizes_every_documented_role() -> None:
    provider = LocalIdentityProvider()

    roles = {
        next(iter(principal.roles))
        for token in (
            "local-requester-token",
            "local-reviewer-token",
            "local-operator-token",
            "local-administrator-token",
        )
        if (principal := provider.verify(token)) is not None
    }

    assert roles == set(Role)
    assert provider.verify("absent") is None


def test_workflow_factory_accepts_a_deterministic_timestamp() -> None:
    now = datetime(2026, 1, 2, tzinfo=UTC)
    context, decision = governance()
    workflow = Workflow.receive(
        workflow_id="workflow-1",
        owner_id="owner-1",
        request="A normalized request",
        requested_locale="en",
        correlation_id="correlation-1",
        processing_context=context,
        governance_decision=decision,
        now=now,
    )

    assert workflow.created_at == now
    assert workflow.transitions[0].at == now


def test_repository_returns_none_for_unknown_workflow() -> None:
    assert InMemoryWorkflowRepository().get("absent") is None


def test_planning_result_uses_a_fixed_transition_timestamp() -> None:
    now = datetime(2026, 2, 3, tzinfo=UTC)
    context, intake_decision = governance()
    workflow = Workflow.receive(
        workflow_id="workflow-2",
        owner_id="owner-1",
        request="Prepare a deterministic plan",
        requested_locale="en",
        correlation_id="correlation-2",
        processing_context=context,
        governance_decision=intake_decision,
        now=now,
    )
    result = DeterministicAgentRuntime().plan(
        PlanningInput(
            workflow_id=workflow.workflow_id,
            owner_id=workflow.owner_id,
            request=workflow.request,
            requested_locale=workflow.requested_locale,
            correlation_id=workflow.correlation_id,
        )
    )

    planning_context = context.model_copy(
        update={"operation": ProcessingOperation.AGENT_PLANNING, "provider": "deterministic-local"}
    )
    planned = workflow.apply_planning_result(
        result,
        BaselinePolicyEngine().evaluate(planning_context),
        create_tool_proposal(workflow.workflow_id, result, now),
        now,
    )

    assert planned.status == "awaiting_approval"
    assert planned.state_version == 9
    assert {transition.at for transition in planned.transitions} == {now}


def test_repository_rejects_stale_or_missing_updates() -> None:
    repository = InMemoryWorkflowRepository()
    context, decision = governance()
    workflow = Workflow.receive(
        workflow_id="workflow-3",
        owner_id="owner-1",
        request="Prepare a deterministic plan",
        requested_locale="en",
        correlation_id="correlation-3",
        processing_context=context,
        governance_decision=decision,
    )
    repository.create(workflow, "workflow-0003")

    with pytest.raises(InvalidWorkflowState):
        repository.update(workflow, expected_state_version=99)
    with pytest.raises(InvalidWorkflowState):
        repository.update(replace(workflow, workflow_id="absent"), expected_state_version=1)


def test_service_rejects_a_non_received_non_planned_state() -> None:
    repository = InMemoryWorkflowRepository()
    context, decision = governance()
    workflow = Workflow.receive(
        workflow_id="workflow-4",
        owner_id="owner-1",
        request="Prepare a deterministic plan",
        requested_locale="en",
        correlation_id="correlation-4",
        processing_context=context,
        governance_decision=decision,
    )
    repository.create(workflow, "workflow-0004")
    repository.update(replace(workflow, status="validated"), expected_state_version=1)
    service = WorkflowService(
        repository,
        audit=StubAudit(),
        runtime=DeterministicAgentRuntime(),
        classifier=DeterministicDataClassifier(),
        policy=BaselinePolicyEngine(),
        task_queue=InMemoryTaskQueue(),
        tool_executor=SimulatedTicketExecutor(),
        id_factory=lambda: "unused",
    )
    principal = Principal("owner-1", "Owner", frozenset({Role.REQUESTER}))

    with pytest.raises(InvalidWorkflowState):
        service.plan(
            principal=principal,
            workflow_id=workflow.workflow_id,
            correlation_id="correlation-4",
        )


def test_service_denies_planning_before_calling_the_runtime() -> None:
    repository = InMemoryWorkflowRepository()
    context, decision = governance()
    workflow = Workflow.receive(
        workflow_id="workflow-5",
        owner_id="owner-1",
        request="Prepare a deterministic plan",
        requested_locale="en",
        correlation_id="correlation-5",
        processing_context=context,
        governance_decision=decision,
    )
    repository.create(workflow, "workflow-0005")
    service = WorkflowService(
        repository,
        audit=StubAudit(),
        runtime=DeterministicAgentRuntime(),
        classifier=DeterministicDataClassifier(),
        policy=PlanningDenyPolicy(),
        task_queue=InMemoryTaskQueue(),
        tool_executor=SimulatedTicketExecutor(),
    )
    principal = Principal("owner-1", "Owner", frozenset({Role.REQUESTER}))

    with pytest.raises(DataProcessingDenied, match="Planning is denied"):
        service.plan(
            principal=principal,
            workflow_id=workflow.workflow_id,
            correlation_id="correlation-5",
        )

    assert repository.get(workflow.workflow_id) == workflow
