"""FastAPI composition root and HTTP boundary."""

from time import perf_counter
from typing import Annotated, Literal
from uuid import uuid4

from agentic_governance import BaselinePolicyEngine, DeterministicDataClassifier
from agentic_runtime import DeterministicAgentRuntime
from fastapi import Depends, FastAPI, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from agentic_api.adapters import (
    InMemoryAuditSink,
    InMemoryTaskQueue,
    InMemoryWorkflowRepository,
    LocalIdentityProvider,
    SimulatedTicketExecutor,
)
from agentic_api.config import ApiSettings, get_settings
from agentic_api.domain import Principal, Role
from agentic_api.dto import (
    ApprovalRequest,
    AuditEventResponse,
    AuditEventsResponse,
    CreateServiceRequest,
    OperationalMetricsResponse,
    ProblemResponse,
    ReadinessResponse,
    SessionResponse,
    WorkflowResponse,
)
from agentic_api.errors import ApplicationError, PermissionDenied
from agentic_api.operational import InMemoryOperationalTelemetry, InMemoryRateLimiter
from agentic_api.security import (
    METADATA_PATTERN,
    authenticated_principal,
    correlation_id,
    enforce_mutation_rate_limit,
    idempotency_key,
)
from agentic_api.service import WorkflowService


class HealthResponse(BaseModel):
    """Public liveness response with no dependency or secret detail."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"] = "ok"
    service: Literal["api"] = "api"
    environment: str


def _problem(
    *, status_code: int, title: str, detail: str, type_suffix: str, correlation: str
) -> JSONResponse:
    payload = ProblemResponse(
        type=f"https://agentic-delivery.local/problems/{type_suffix}",
        title=title,
        status=status_code,
        detail=detail,
        correlationId=correlation,
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(by_alias=True, mode="json"),
        media_type="application/problem+json",
    )


def create_app(settings: ApiSettings) -> FastAPI:
    """Build the API and wire local adapters behind application-owned ports."""

    settings.assert_safe_profile()
    application = FastAPI(
        title="Agentic Delivery Reference API",
        version="0.6.0",
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url=None,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Correlation-ID"],
    )
    application.state.identity_provider = LocalIdentityProvider()
    application.state.workflow_repository = InMemoryWorkflowRepository()
    application.state.audit_sink = InMemoryAuditSink()
    application.state.telemetry = InMemoryOperationalTelemetry()
    application.state.rate_limiter = InMemoryRateLimiter(
        settings.rate_limit_requests, settings.rate_limit_window_seconds
    )
    application.state.task_queue = InMemoryTaskQueue()
    application.state.tool_executor = SimulatedTicketExecutor()
    application.state.workflow_service = WorkflowService(
        application.state.workflow_repository,
        application.state.audit_sink,
        DeterministicAgentRuntime(),
        DeterministicDataClassifier(),
        BaselinePolicyEngine(settings.governance_mode),
        application.state.task_queue,
        application.state.tool_executor,
    )

    @application.middleware("http")
    async def secure_observable_boundary(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        incoming = request.headers.get("X-Correlation-ID")
        if incoming is None:
            request.state.correlation_id = str(uuid4())
            invalid_correlation = False
        elif METADATA_PATTERN.fullmatch(incoming):
            request.state.correlation_id = incoming
            invalid_correlation = False
        else:
            request.state.correlation_id = "unavailable"
            invalid_correlation = True
        started = perf_counter()
        response: Response
        if invalid_correlation:
            response = _problem(
                status_code=400,
                title="Invalid request metadata",
                detail="X-Correlation-ID has an invalid format.",
                type_suffix="invalid-request-metadata",
                correlation="unavailable",
            )
            route_template = "<rejected>"
        else:
            response = await call_next(request)
            route = request.scope.get("route")
            route_template = getattr(route, "path", "<unmatched>")
        application.state.telemetry.record(
            method=request.method,
            route=route_template,
            status_code=response.status_code,
            duration_ms=(perf_counter() - started) * 1000,
            correlation_id=request.state.correlation_id,
        )
        response.headers["X-Correlation-ID"] = request.state.correlation_id
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https://fastapi.tiangolo.com; "
            "frame-ancestors 'none'; object-src 'none'"
        )
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    @application.exception_handler(ApplicationError)
    async def handle_application_error(request: Request, error: ApplicationError) -> JSONResponse:
        correlation = getattr(request.state, "correlation_id", "unavailable")
        return _problem(
            status_code=error.status_code,
            title=error.title,
            detail=error.detail,
            type_suffix=error.type_suffix,
            correlation=correlation,
        )

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, _error: RequestValidationError
    ) -> JSONResponse:
        correlation = getattr(request.state, "correlation_id", "unavailable")
        return _problem(
            status_code=422,
            title="Request validation failed",
            detail="The request body or parameters do not match the API contract.",
            type_suffix="validation-error",
            correlation=correlation,
        )

    @application.get(
        "/health",
        response_model=HealthResponse,
        tags=["operations"],
        summary="Report process liveness",
    )
    def health() -> HealthResponse:
        return HealthResponse(environment=settings.environment)

    @application.get(
        "/ready",
        response_model=ReadinessResponse,
        tags=["operations"],
        summary="Report local component readiness",
    )
    def ready() -> ReadinessResponse:
        return ReadinessResponse(
            checks={
                "audit": "ready",
                "identity": "ready",
                "rateLimit": "ready",
                "repository": "ready",
                "taskQueue": "ready",
                "telemetry": "ready",
            }
        )

    @application.get(
        "/v1/operations/metrics",
        response_model=OperationalMetricsResponse,
        tags=["operations"],
    )
    def operational_metrics(
        principal: Annotated[Principal, Depends(authenticated_principal)],
        correlation: Annotated[str, Depends(correlation_id)],
    ) -> OperationalMetricsResponse:
        if not principal.roles.intersection({Role.OPERATOR, Role.ADMINISTRATOR}):
            application.state.audit_sink.record(
                action="operations.metrics.read",
                outcome="denied",
                subject=principal.subject,
                resource_id=None,
                correlation_id=correlation,
            )
            raise PermissionDenied("The current role cannot inspect operational metrics.")
        application.state.audit_sink.record(
            action="operations.metrics.read",
            outcome="allowed",
            subject=principal.subject,
            resource_id=None,
            correlation_id=correlation,
        )
        return OperationalMetricsResponse.from_domain(application.state.telemetry.snapshot())

    @application.get(
        "/v1/operations/audit-events",
        response_model=AuditEventsResponse,
        tags=["operations"],
    )
    def audit_events(
        principal: Annotated[Principal, Depends(authenticated_principal)],
        correlation: Annotated[str, Depends(correlation_id)],
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
    ) -> AuditEventsResponse:
        if Role.ADMINISTRATOR not in principal.roles:
            application.state.audit_sink.record(
                action="operations.audit.read",
                outcome="denied",
                subject=principal.subject,
                resource_id=None,
                correlation_id=correlation,
            )
            raise PermissionDenied("The current role cannot inspect audit evidence.")
        application.state.audit_sink.record(
            action="operations.audit.read",
            outcome="allowed",
            subject=principal.subject,
            resource_id=None,
            correlation_id=correlation,
        )
        events = application.state.audit_sink.events[-limit:]
        return AuditEventsResponse(
            events=tuple(
                AuditEventResponse(
                    eventId=event.event_id,
                    occurredAt=event.occurred_at,
                    actor=event.subject,
                    action=event.action,
                    resourceId=event.resource_id,
                    decision=event.decision,
                    outcome=event.outcome,
                    correlationId=event.correlation_id,
                )
                for event in events
            )
        )

    @application.get("/v1/session", response_model=SessionResponse, tags=["identity"])
    def session(
        principal: Annotated[Principal, Depends(authenticated_principal)],
    ) -> SessionResponse:
        return SessionResponse.from_principal(principal)

    @application.post(
        "/v1/service-requests",
        response_model=WorkflowResponse,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["workflows"],
    )
    def create_service_request(
        payload: CreateServiceRequest,
        principal: Annotated[Principal, Depends(authenticated_principal)],
        correlation: Annotated[str, Depends(correlation_id)],
        idempotency: Annotated[str, Depends(idempotency_key)],
        _rate_limit: Annotated[None, Depends(enforce_mutation_rate_limit)],
    ) -> WorkflowResponse:
        workflow = application.state.workflow_service.create(
            principal=principal,
            request=payload.request,
            requested_locale=payload.requested_locale,
            idempotency_key=idempotency,
            correlation_id=correlation,
            declared_categories=payload.data_context.declared_categories,
            purpose=payload.data_context.purpose,
            jurisdiction=payload.data_context.jurisdiction,
            overlay_ids=payload.data_context.overlay_ids,
        )
        return WorkflowResponse.from_domain(workflow)

    @application.post(
        "/v1/workflows/{workflow_id}/plan",
        response_model=WorkflowResponse,
        tags=["workflows"],
    )
    def plan_workflow(
        workflow_id: str,
        principal: Annotated[Principal, Depends(authenticated_principal)],
        correlation: Annotated[str, Depends(correlation_id)],
        _idempotency: Annotated[str, Depends(idempotency_key)],
        _rate_limit: Annotated[None, Depends(enforce_mutation_rate_limit)],
    ) -> WorkflowResponse:
        workflow = application.state.workflow_service.plan(
            principal=principal,
            workflow_id=workflow_id,
            correlation_id=correlation,
        )
        return WorkflowResponse.from_domain(workflow)

    @application.post(
        "/v1/workflows/{workflow_id}/approval",
        response_model=WorkflowResponse,
        tags=["approvals"],
    )
    def decide_workflow_approval(
        workflow_id: str,
        payload: ApprovalRequest,
        principal: Annotated[Principal, Depends(authenticated_principal)],
        correlation: Annotated[str, Depends(correlation_id)],
        idempotency: Annotated[str, Depends(idempotency_key)],
        _rate_limit: Annotated[None, Depends(enforce_mutation_rate_limit)],
    ) -> WorkflowResponse:
        workflow = application.state.workflow_service.decide_approval(
            principal=principal,
            workflow_id=workflow_id,
            decision=payload.decision,
            reason=payload.reason,
            idempotency_key=idempotency,
            correlation_id=correlation,
        )
        return WorkflowResponse.from_domain(workflow)

    @application.post(
        "/v1/local/tasks/process-next",
        response_model=WorkflowResponse,
        tags=["local-worker"],
    )
    def process_next_local_task(
        principal: Annotated[Principal, Depends(authenticated_principal)],
        correlation: Annotated[str, Depends(correlation_id)],
        _idempotency: Annotated[str, Depends(idempotency_key)],
        _rate_limit: Annotated[None, Depends(enforce_mutation_rate_limit)],
    ) -> WorkflowResponse:
        workflow = application.state.workflow_service.process_next_task(
            principal=principal,
            correlation_id=correlation,
        )
        return WorkflowResponse.from_domain(workflow)

    @application.get(
        "/v1/workflows/{workflow_id}", response_model=WorkflowResponse, tags=["workflows"]
    )
    def get_workflow(
        workflow_id: str,
        principal: Annotated[Principal, Depends(authenticated_principal)],
        correlation: Annotated[str, Depends(correlation_id)],
    ) -> WorkflowResponse:
        workflow = application.state.workflow_service.get(
            principal=principal,
            workflow_id=workflow_id,
            correlation_id=correlation,
        )
        return WorkflowResponse.from_domain(workflow)

    return application


app = create_app(get_settings())
