"""Typed contracts owned by the deterministic runtime boundary."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Complexity = Literal["low", "medium", "high"]
Category = Literal["general", "integration", "security", "data"]
CompletedState = Literal[
    "validated",
    "guarded",
    "classified",
    "context_built",
    "knowledge_retrieved",
    "planned",
    "evaluated",
]


class PlanningInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    workflow_id: str
    owner_id: str
    request: str
    requested_locale: str
    correlation_id: str


class Classification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    category: Category
    complexity: Complexity
    reason: str


class ModelPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: Literal["deterministic-local"] = "deterministic-local"
    model: Literal["rules-v1"] = "rules-v1"
    reason: str


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: str = Field(alias="documentId")
    title: str
    section: str
    version: str
    excerpt_hash: str = Field(alias="excerptHash")
    relevance_score: float = Field(alias="relevanceScore", ge=0, le=1)


class RetrievalEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    corpus_version: str = Field(alias="corpusVersion")
    selected_document_ids: tuple[str, ...] = Field(alias="selectedDocumentIds")
    quarantined_document_ids: tuple[str, ...] = Field(alias="quarantinedDocumentIds")


class GuardrailReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_version: str = Field(alias="policyVersion")
    input_outcome: Literal["passed"] = Field(default="passed", alias="inputOutcome")
    retrieval_outcome: Literal["passed", "filtered"] = Field(alias="retrievalOutcome")
    output_outcome: Literal["passed"] = Field(default="passed", alias="outputOutcome")


class EvaluationCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    passed: bool


class EvaluationGateResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    gate_version: str = Field(alias="gateVersion")
    passed: bool
    score: float = Field(ge=0, le=1)
    threshold: float = Field(ge=0, le=1)
    checks: tuple[EvaluationCheck, ...]


class ImplementationProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    summary: str
    complexity: Complexity
    delivery_steps: tuple[str, ...] = Field(alias="deliverySteps")
    risks: tuple[str, ...]


class ExecutionMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    latency_ms: Literal[0] = Field(default=0, alias="latencyMs")
    estimated_input_tokens: int = Field(alias="estimatedInputTokens", ge=0)
    estimated_output_tokens: int = Field(alias="estimatedOutputTokens", ge=0)
    estimated_cost_usd: float = Field(default=0.0, alias="estimatedCostUsd", ge=0, le=0)


class PlanningResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    classification: Classification
    model_policy: ModelPolicy = Field(alias="modelPolicy")
    proposal: ImplementationProposal
    citations: tuple[Citation, ...]
    retrieval: RetrievalEvidence
    guardrails: GuardrailReport
    evaluation: EvaluationGateResult
    metrics: ExecutionMetrics
    completed_states: tuple[CompletedState, ...] = Field(alias="completedStates")
