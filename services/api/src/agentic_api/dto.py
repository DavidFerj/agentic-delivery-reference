"""Validated HTTP data-transfer objects."""

from datetime import datetime
from typing import Literal, cast

from agentic_governance.models import (
    DataCategory,
    PolicyDecision,
    ProcessingContext,
    ProcessingPurpose,
)
from agentic_runtime.models import (
    Citation,
    Classification,
    EvaluationGateResult,
    ExecutionMetrics,
    GuardrailReport,
    ImplementationProposal,
    ModelPolicy,
    RetrievalEvidence,
)
from pydantic import BaseModel, ConfigDict, Field

from agentic_api.domain import Principal, Workflow
from agentic_api.execution import ApprovalDecision, ToolActionProposal, ToolExecutionResult
from agentic_api.operational import RequestObservation, TelemetrySnapshot


class DataContextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    declared_categories: set[DataCategory] = Field(default_factory=set, alias="declaredCategories")
    purpose: ProcessingPurpose = ProcessingPurpose.DELIVERY_PLANNING
    jurisdiction: str = Field(default="US", min_length=2, max_length=35, pattern=r"^[A-Z-]+$")
    overlay_ids: tuple[str, ...] = Field(
        default=("common-us-baseline",), alias="overlayIds", min_length=1
    )


class CreateServiceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request: str = Field(min_length=10, max_length=10_000)
    requested_locale: str = Field(default="en", alias="requestedLocale", max_length=35)
    data_context: DataContextRequest = Field(
        default_factory=DataContextRequest, alias="dataContext"
    )


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["approved", "rejected"]
    reason: str = Field(min_length=3, max_length=500)


class SessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str
    display_name: str = Field(alias="displayName")
    roles: list[str]

    @classmethod
    def from_principal(cls, principal: Principal) -> "SessionResponse":
        return cls(
            subject=principal.subject,
            displayName=principal.display_name,
            roles=sorted(role.value for role in principal.roles),
        )


class StateTransitionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    previous: str | None = Field(alias="from")
    current: str = Field(alias="to")
    at: datetime
    actor_type: str = Field(alias="actorType")


class WorkflowResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_id: str = Field(alias="workflowId")
    status: Literal[
        "received",
        "awaiting_approval",
        "approved",
        "rejected",
        "expired",
        "executing",
        "completed",
    ]
    state_version: int = Field(alias="stateVersion")
    created_at: datetime = Field(alias="createdAt")
    correlation_id: str = Field(alias="correlationId")
    request: str
    requested_locale: str = Field(alias="requestedLocale")
    transitions: list[StateTransitionResponse]
    classification: Classification | None = None
    model_policy: ModelPolicy | None = Field(default=None, alias="modelPolicy")
    proposal: ImplementationProposal | None = None
    citations: tuple[Citation, ...] = ()
    retrieval: RetrievalEvidence | None = None
    guardrails: GuardrailReport | None = None
    evaluation: EvaluationGateResult | None = None
    metrics: ExecutionMetrics | None = None
    processing_context: ProcessingContext = Field(alias="processingContext")
    governance_decisions: tuple[PolicyDecision, ...] = Field(alias="governanceDecisions")
    action_proposal: ToolActionProposal | None = Field(default=None, alias="actionProposal")
    approval_decision: ApprovalDecision | None = Field(default=None, alias="approvalDecision")
    execution_result: ToolExecutionResult | None = Field(default=None, alias="executionResult")

    @classmethod
    def from_domain(cls, workflow: Workflow) -> "WorkflowResponse":
        return cls(
            workflowId=workflow.workflow_id,
            status=cast(
                Literal[
                    "received",
                    "awaiting_approval",
                    "approved",
                    "rejected",
                    "expired",
                    "executing",
                    "completed",
                ],
                workflow.status,
            ),
            stateVersion=workflow.state_version,
            createdAt=workflow.created_at,
            correlationId=workflow.correlation_id,
            request=workflow.request,
            requestedLocale=workflow.requested_locale,
            transitions=[
                StateTransitionResponse.model_validate(
                    {
                        "from": transition.previous,
                        "to": transition.current,
                        "at": transition.at,
                        "actorType": transition.actor_type,
                    }
                )
                for transition in workflow.transitions
            ],
            classification=(
                workflow.planning_result.classification if workflow.planning_result else None
            ),
            modelPolicy=(
                workflow.planning_result.model_policy if workflow.planning_result else None
            ),
            proposal=workflow.planning_result.proposal if workflow.planning_result else None,
            citations=workflow.planning_result.citations if workflow.planning_result else (),
            retrieval=workflow.planning_result.retrieval if workflow.planning_result else None,
            guardrails=workflow.planning_result.guardrails if workflow.planning_result else None,
            evaluation=workflow.planning_result.evaluation if workflow.planning_result else None,
            metrics=workflow.planning_result.metrics if workflow.planning_result else None,
            processingContext=workflow.processing_context,
            governanceDecisions=workflow.governance_decisions,
            actionProposal=workflow.action_proposal,
            approvalDecision=workflow.approval_decision,
            executionResult=workflow.execution_result,
        )


class ProblemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    title: str
    status: int
    detail: str
    correlation_id: str = Field(alias="correlationId")


class ReadinessResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ready"] = "ready"
    service: Literal["api"] = "api"
    checks: dict[str, Literal["ready"]]


class RequestObservationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    occurred_at: datetime = Field(alias="occurredAt")
    method: str
    route: str
    status_code: int = Field(alias="statusCode")
    duration_ms: float = Field(alias="durationMs")
    correlation_id: str = Field(alias="correlationId")

    @classmethod
    def from_domain(cls, observation: RequestObservation) -> "RequestObservationResponse":
        return cls(
            occurredAt=observation.occurred_at,
            method=observation.method,
            route=observation.route,
            statusCode=observation.status_code,
            durationMs=observation.duration_ms,
            correlationId=observation.correlation_id,
        )


class OperationalMetricsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_requests: int = Field(alias="totalRequests")
    error_requests: int = Field(alias="errorRequests")
    average_duration_ms: float = Field(alias="averageDurationMs")
    status_counts: dict[str, int] = Field(alias="statusCounts")
    route_counts: dict[str, int] = Field(alias="routeCounts")
    recent_requests: tuple[RequestObservationResponse, ...] = Field(alias="recentRequests")

    @classmethod
    def from_domain(cls, snapshot: TelemetrySnapshot) -> "OperationalMetricsResponse":
        return cls(
            totalRequests=snapshot.total_requests,
            errorRequests=snapshot.error_requests,
            averageDurationMs=snapshot.average_duration_ms,
            statusCounts=snapshot.status_counts,
            routeCounts=snapshot.route_counts,
            recentRequests=tuple(
                RequestObservationResponse.from_domain(item) for item in snapshot.recent_requests
            ),
        )


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(alias="eventId")
    occurred_at: datetime = Field(alias="occurredAt")
    actor: str | None
    action: str
    resource_id: str | None = Field(alias="resourceId")
    decision: str
    outcome: str
    correlation_id: str = Field(alias="correlationId")


class AuditEventsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: tuple[AuditEventResponse, ...]
