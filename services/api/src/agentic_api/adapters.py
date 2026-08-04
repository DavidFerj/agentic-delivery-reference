"""Deterministic adapters used only by the local profile."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import RLock

from agentic_api.domain import Principal, Role, Workflow
from agentic_api.errors import IdempotencyConflict, InvalidWorkflowState
from agentic_api.execution import (
    ExecutionTask,
    ToolActionProposal,
    ToolExecutionResult,
    canonical_digest,
)

LOCAL_IDENTITIES: dict[str, Principal] = {
    "local-requester-token": Principal(
        subject="local-requester",
        display_name="Local Requester",
        roles=frozenset({Role.REQUESTER}),
    ),
    "local-reviewer-token": Principal(
        subject="local-reviewer",
        display_name="Local Reviewer",
        roles=frozenset({Role.REVIEWER}),
    ),
    "local-operator-token": Principal(
        subject="local-operator",
        display_name="Local Operator",
        roles=frozenset({Role.OPERATOR}),
    ),
    "local-administrator-token": Principal(
        subject="local-administrator",
        display_name="Local Administrator",
        roles=frozenset({Role.ADMINISTRATOR}),
    ),
}


class LocalIdentityProvider:
    """Resolve documented non-secret development credentials."""

    def verify(self, credential: str) -> Principal | None:
        return LOCAL_IDENTITIES.get(credential)


class InMemoryWorkflowRepository:
    """Thread-safe process-local repository for the local vertical slice."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._workflows: dict[str, Workflow] = {}
        self._idempotency: dict[tuple[str, str], str] = {}

    def create(self, workflow: Workflow, idempotency_key: str) -> Workflow:
        scoped_key = (workflow.owner_id, idempotency_key)
        with self._lock:
            existing_id = self._idempotency.get(scoped_key)
            if existing_id is not None:
                existing = self._workflows[existing_id]
                if (
                    existing.request != workflow.request
                    or existing.requested_locale != workflow.requested_locale
                ):
                    raise IdempotencyConflict(
                        "The idempotency key was already used with a different request."
                    )
                return existing
            self._workflows[workflow.workflow_id] = workflow
            self._idempotency[scoped_key] = workflow.workflow_id
            return workflow

    def get(self, workflow_id: str) -> Workflow | None:
        with self._lock:
            return self._workflows.get(workflow_id)

    def update(self, workflow: Workflow, expected_state_version: int) -> Workflow:
        with self._lock:
            current = self._workflows.get(workflow.workflow_id)
            if current is None or current.state_version != expected_state_version:
                raise InvalidWorkflowState(
                    "The workflow changed before the planning result could be stored."
                )
            self._workflows[workflow.workflow_id] = workflow
            return workflow


@dataclass(frozen=True, slots=True)
class AuditEvent:
    event_id: str
    occurred_at: datetime
    action: str
    outcome: str
    decision: str
    subject: str | None
    resource_id: str | None
    correlation_id: str


class InMemoryAuditSink:
    """Collect sanitized audit events for local inspection and tests."""

    def __init__(self, now_factory: Callable[[], datetime] | None = None) -> None:
        self._now_factory = now_factory or (lambda: datetime.now(UTC))
        self._lock = RLock()
        self._events: list[AuditEvent] = []

    @property
    def events(self) -> tuple[AuditEvent, ...]:
        with self._lock:
            return tuple(self._events)

    def record(
        self,
        *,
        action: str,
        outcome: str,
        subject: str | None,
        resource_id: str | None,
        correlation_id: str,
    ) -> None:
        with self._lock:
            self._events.append(
                AuditEvent(
                    event_id=f"audit-{len(self._events) + 1:08d}",
                    occurred_at=self._now_factory(),
                    action=action,
                    outcome=outcome,
                    decision=outcome,
                    subject=subject,
                    resource_id=resource_id,
                    correlation_id=correlation_id,
                )
            )


class InMemoryTaskQueue:
    """Retain approved work for explicit at-least-once local processing."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._tasks: dict[str, ExecutionTask] = {}
        self._order: list[str] = []
        self._completed: set[str] = set()

    def enqueue(self, task: ExecutionTask) -> ExecutionTask:
        with self._lock:
            existing = self._tasks.get(task.task_id)
            if existing is not None:
                if existing.proposal_digest != task.proposal_digest:
                    raise IdempotencyConflict(
                        "The task identifier is already bound to another proposal."
                    )
                return existing
            self._tasks[task.task_id] = task
            self._order.append(task.task_id)
            return task

    def claim_next(self) -> ExecutionTask | None:
        with self._lock:
            for task_id in self._order:
                if task_id in self._completed:
                    continue
                task = self._tasks[task_id]
                delivered = task.model_copy(update={"delivery_attempt": task.delivery_attempt + 1})
                self._tasks[task_id] = delivered
                return delivered
            return None

    def complete(self, task_id: str) -> None:
        with self._lock:
            self._completed.add(task_id)


class SimulatedTicketExecutor:
    """Create deterministic local ticket evidence without an external side effect."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._executions: dict[str, ToolExecutionResult] = {}

    @property
    def executions(self) -> tuple[ToolExecutionResult, ...]:
        return tuple(self._executions.values())

    def execute(
        self, task: ExecutionTask, proposal: ToolActionProposal, now: datetime
    ) -> ToolExecutionResult:
        with self._lock:
            existing = self._executions.get(task.idempotency_key)
            if existing is not None:
                if existing.proposal_digest != proposal.proposal_digest:
                    raise IdempotencyConflict(
                        "The execution key is already bound to another proposal."
                    )
                return existing
            execution_hash = canonical_digest(
                {
                    "idempotencyKey": task.idempotency_key,
                    "proposalDigest": proposal.proposal_digest,
                }
            )
            result = ToolExecutionResult(
                executionId=f"execution-{execution_hash[:16]}",
                ticketId=f"LOCAL-{execution_hash[:12].upper()}",
                executedAt=now,
                idempotencyKey=task.idempotency_key,
                proposalDigest=proposal.proposal_digest,
            )
            self._executions[task.idempotency_key] = result
            return result
