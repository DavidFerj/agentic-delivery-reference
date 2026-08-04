"""Application errors mapped to safe HTTP problem responses at the boundary."""


class ApplicationError(Exception):
    """Base error carrying only information safe for API consumers."""

    status_code = 500
    title = "Internal server error"
    type_suffix = "internal-error"

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class AuthenticationRequired(ApplicationError):
    status_code = 401
    title = "Authentication required"
    type_suffix = "authentication-required"


class PermissionDenied(ApplicationError):
    status_code = 403
    title = "Permission denied"
    type_suffix = "permission-denied"


class WorkflowNotFound(ApplicationError):
    status_code = 404
    title = "Workflow not found"
    type_suffix = "workflow-not-found"


class IdempotencyConflict(ApplicationError):
    status_code = 409
    title = "Idempotency conflict"
    type_suffix = "idempotency-conflict"


class InvalidRequestMetadata(ApplicationError):
    status_code = 400
    title = "Invalid request metadata"
    type_suffix = "invalid-request-metadata"


class InvalidWorkflowState(ApplicationError):
    status_code = 409
    title = "Invalid workflow state"
    type_suffix = "invalid-workflow-state"


class DataProcessingDenied(ApplicationError):
    status_code = 403
    title = "Data processing denied"
    type_suffix = "data-processing-denied"


class ComplianceOverlayUnavailable(ApplicationError):
    status_code = 422
    title = "Compliance overlay unavailable"
    type_suffix = "compliance-overlay-unavailable"


class ApprovalExpired(ApplicationError):
    status_code = 409
    title = "Approval expired"
    type_suffix = "approval-expired"


class NoPendingTask(ApplicationError):
    status_code = 404
    title = "No pending task"
    type_suffix = "no-pending-task"


class PromptInjectionRejected(ApplicationError):
    status_code = 422
    title = "Prompt injection blocked"
    type_suffix = "prompt-injection-blocked"


class EvaluationGateRejected(ApplicationError):
    status_code = 422
    title = "Evaluation gate rejected the proposal"
    type_suffix = "evaluation-gate-rejected"


class RequestRateExceeded(ApplicationError):
    status_code = 429
    title = "Request rate exceeded"
    type_suffix = "request-rate-exceeded"
