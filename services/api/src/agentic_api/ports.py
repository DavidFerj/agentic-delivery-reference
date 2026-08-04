"""Ports owned by the application core."""

from datetime import datetime
from typing import Protocol

from agentic_runtime.models import PlanningInput, PlanningResult

from agentic_api.domain import Principal, Workflow
from agentic_api.execution import ExecutionTask, ToolActionProposal, ToolExecutionResult


class IdentityProvider(Protocol):
    """Verify an opaque bearer credential at the trust boundary."""

    def verify(self, credential: str) -> Principal | None: ...


class WorkflowRepository(Protocol):
    """Store workflows and enforce scoped idempotency."""

    def create(self, workflow: Workflow, idempotency_key: str) -> Workflow: ...

    def get(self, workflow_id: str) -> Workflow | None: ...

    def update(self, workflow: Workflow, expected_state_version: int) -> Workflow: ...


class AgentRuntime(Protocol):
    """Execute deterministic planning behind an application-owned port."""

    def plan(self, planning_input: PlanningInput) -> PlanningResult: ...


class AuditSink(Protocol):
    """Record security-relevant decisions without sensitive payloads."""

    def record(
        self,
        *,
        action: str,
        outcome: str,
        subject: str | None,
        resource_id: str | None,
        correlation_id: str,
    ) -> None: ...


class TaskQueue(Protocol):
    """Dispatch approved work with at-least-once local delivery semantics."""

    def enqueue(self, task: ExecutionTask) -> ExecutionTask: ...

    def claim_next(self) -> ExecutionTask | None: ...

    def complete(self, task_id: str) -> None: ...


class ToolExecutor(Protocol):
    """Execute one approved tool proposal idempotently."""

    def execute(
        self, task: ExecutionTask, proposal: ToolActionProposal, now: datetime
    ) -> ToolExecutionResult: ...
