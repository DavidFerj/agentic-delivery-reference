"""Typed approval, task, and simulated side-effect contracts."""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Literal

from agentic_runtime.models import PlanningResult
from pydantic import BaseModel, ConfigDict, Field


class TicketArguments(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    workflow_id: str = Field(alias="workflowId")
    title: str
    complexity: str
    delivery_steps: tuple[str, ...] = Field(alias="deliverySteps")


class ToolActionProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    proposal_id: str = Field(alias="proposalId")
    action: Literal["create_delivery_ticket"] = "create_delivery_ticket"
    arguments: TicketArguments
    schema_hash: str = Field(alias="schemaHash")
    proposal_digest: str = Field(alias="proposalDigest")
    expires_at: datetime = Field(alias="expiresAt")


class ApprovalDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    decision_id: str = Field(alias="decisionId")
    decision: Literal["approved", "rejected"]
    reviewer_id: str = Field(alias="reviewerId")
    reason: str
    decided_at: datetime = Field(alias="decidedAt")
    expires_at: datetime = Field(alias="expiresAt")
    proposal_digest: str = Field(alias="proposalDigest")
    idempotency_key: str = Field(alias="idempotencyKey", exclude=True)
    consumed_at: datetime | None = Field(default=None, alias="consumedAt")


class ExecutionTask(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: str = Field(alias="taskId")
    workflow_id: str = Field(alias="workflowId")
    proposal_digest: str = Field(alias="proposalDigest")
    idempotency_key: str = Field(alias="idempotencyKey")
    delivery_attempt: int = Field(default=0, alias="deliveryAttempt", ge=0)


class ToolExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    execution_id: str = Field(alias="executionId")
    ticket_id: str = Field(alias="ticketId")
    status: Literal["created"] = "created"
    simulated: Literal[True] = True
    executed_at: datetime = Field(alias="executedAt")
    idempotency_key: str = Field(alias="idempotencyKey", exclude=True)
    proposal_digest: str = Field(alias="proposalDigest")


def canonical_digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def create_tool_proposal(
    workflow_id: str,
    planning_result: PlanningResult,
    now: datetime | None = None,
) -> ToolActionProposal:
    created_at = now or datetime.now(UTC)
    arguments = TicketArguments(
        workflowId=workflow_id,
        title=planning_result.proposal.summary,
        complexity=planning_result.proposal.complexity,
        deliverySteps=planning_result.proposal.delivery_steps,
    )
    action_contract = {
        "action": "create_delivery_ticket",
        "arguments": arguments.model_dump(mode="json", by_alias=True),
    }
    digest = canonical_digest(action_contract)
    schema_hash = canonical_digest(TicketArguments.model_json_schema(by_alias=True))
    return ToolActionProposal(
        proposalId=f"proposal-{digest[:16]}",
        arguments=arguments,
        schemaHash=schema_hash,
        proposalDigest=digest,
        expiresAt=created_at + timedelta(minutes=30),
    )


def create_approval_decision(
    *,
    proposal: ToolActionProposal,
    reviewer_id: str,
    decision: Literal["approved", "rejected"],
    reason: str,
    idempotency_key: str,
    now: datetime,
) -> ApprovalDecision:
    decision_id = canonical_digest(
        {
            "decision": decision,
            "idempotencyKey": idempotency_key,
            "proposalDigest": proposal.proposal_digest,
            "reviewerId": reviewer_id,
        }
    )
    return ApprovalDecision(
        decisionId=decision_id,
        decision=decision,
        reviewerId=reviewer_id,
        reason=reason,
        decidedAt=now,
        expiresAt=min(proposal.expires_at, now + timedelta(minutes=15)),
        proposalDigest=proposal.proposal_digest,
        idempotencyKey=idempotency_key,
    )


def create_execution_task(workflow_id: str, proposal_digest: str) -> ExecutionTask:
    return ExecutionTask(
        taskId=f"task-{canonical_digest({'workflowId': workflow_id})[:16]}",
        workflowId=workflow_id,
        proposalDigest=proposal_digest,
        idempotencyKey=f"ticket:{workflow_id}:{proposal_digest}",
    )
