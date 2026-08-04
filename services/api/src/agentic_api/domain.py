"""Framework-independent identity and workflow domain models."""

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum

from agentic_governance.models import PolicyDecision, ProcessingContext, ProcessingOperation
from agentic_runtime.models import PlanningResult

from agentic_api.execution import ApprovalDecision, ToolActionProposal, ToolExecutionResult


class Role(StrEnum):
    """Roles supported by the product authorization model."""

    REQUESTER = "requester"
    REVIEWER = "reviewer"
    OPERATOR = "operator"
    ADMINISTRATOR = "administrator"


@dataclass(frozen=True, slots=True)
class Principal:
    """Verified local representation of an interactive identity."""

    subject: str
    display_name: str
    roles: frozenset[Role]


@dataclass(frozen=True, slots=True)
class StateTransition:
    """One immutable workflow state change."""

    previous: str | None
    current: str
    at: datetime
    actor_type: str


@dataclass(frozen=True, slots=True)
class Workflow:
    """Workflow aggregate and persisted deterministic planning result."""

    workflow_id: str
    owner_id: str
    request: str
    requested_locale: str
    status: str
    state_version: int
    created_at: datetime
    correlation_id: str
    transitions: tuple[StateTransition, ...]
    processing_context: ProcessingContext
    governance_decisions: tuple[PolicyDecision, ...]
    planning_result: PlanningResult | None = None
    action_proposal: ToolActionProposal | None = None
    approval_decision: ApprovalDecision | None = None
    execution_result: ToolExecutionResult | None = None

    @classmethod
    def receive(
        cls,
        *,
        workflow_id: str,
        owner_id: str,
        request: str,
        requested_locale: str,
        correlation_id: str,
        processing_context: ProcessingContext,
        governance_decision: PolicyDecision,
        now: datetime | None = None,
    ) -> "Workflow":
        """Create the first valid workflow state."""

        created_at = now or datetime.now(UTC)
        transition = StateTransition(
            previous=None,
            current="received",
            at=created_at,
            actor_type="user",
        )
        return cls(
            workflow_id=workflow_id,
            owner_id=owner_id,
            request=request,
            requested_locale=requested_locale,
            status="received",
            state_version=1,
            created_at=created_at,
            correlation_id=correlation_id,
            transitions=(transition,),
            processing_context=processing_context,
            governance_decisions=(governance_decision,),
        )

    def apply_planning_result(
        self,
        result: PlanningResult,
        governance_decision: PolicyDecision,
        action_proposal: ToolActionProposal,
        now: datetime | None = None,
    ) -> "Workflow":
        """Append every graph checkpoint to the authoritative state history."""

        transitioned_at = now or datetime.now(UTC)
        previous = self.status
        transitions = list(self.transitions)
        for current in result.completed_states:
            transitions.append(
                StateTransition(
                    previous=previous,
                    current=current,
                    at=transitioned_at,
                    actor_type="system",
                )
            )
            previous = current
        transitions.append(
            StateTransition(
                previous=previous,
                current="awaiting_approval",
                at=transitioned_at,
                actor_type="system",
            )
        )
        return replace(
            self,
            status="awaiting_approval",
            state_version=self.state_version + len(result.completed_states) + 1,
            transitions=tuple(transitions),
            planning_result=result,
            processing_context=self.processing_context.model_copy(
                update={
                    "operation": ProcessingOperation.AGENT_PLANNING,
                    "provider": "deterministic-local",
                }
            ),
            governance_decisions=(*self.governance_decisions, governance_decision),
            action_proposal=action_proposal,
        )

    def record_approval(
        self, approval: ApprovalDecision, now: datetime | None = None
    ) -> "Workflow":
        decided_at = now or datetime.now(UTC)
        return replace(
            self,
            status=approval.decision,
            state_version=self.state_version + 1,
            transitions=(
                *self.transitions,
                StateTransition(self.status, approval.decision, decided_at, "human"),
            ),
            approval_decision=approval,
        )

    def expire(self, now: datetime | None = None) -> "Workflow":
        expired_at = now or datetime.now(UTC)
        return replace(
            self,
            status="expired",
            state_version=self.state_version + 1,
            transitions=(
                *self.transitions,
                StateTransition(self.status, "expired", expired_at, "system"),
            ),
        )

    def begin_execution(
        self,
        governance_decision: PolicyDecision,
        processing_context: ProcessingContext,
        now: datetime | None = None,
    ) -> "Workflow":
        started_at = now or datetime.now(UTC)
        return replace(
            self,
            status="executing",
            state_version=self.state_version + 1,
            transitions=(
                *self.transitions,
                StateTransition(self.status, "executing", started_at, "worker"),
            ),
            processing_context=processing_context,
            governance_decisions=(*self.governance_decisions, governance_decision),
        )

    def complete_execution(
        self, result: ToolExecutionResult, now: datetime | None = None
    ) -> "Workflow":
        completed_at = now or datetime.now(UTC)
        if self.approval_decision is None:
            raise ValueError("An approval decision is required before completion.")
        consumed = self.approval_decision.model_copy(update={"consumed_at": completed_at})
        return replace(
            self,
            status="completed",
            state_version=self.state_version + 2,
            transitions=(
                *self.transitions,
                StateTransition(self.status, "evaluating", completed_at, "system"),
                StateTransition("evaluating", "completed", completed_at, "system"),
            ),
            approval_decision=consumed,
            execution_result=result,
        )
