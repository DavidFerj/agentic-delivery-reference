"""Explicit LangGraph composition for deterministic governed planning."""

from typing import Literal, NotRequired, TypedDict, cast

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from agentic_runtime.errors import EvaluationGateBlocked
from agentic_runtime.evaluation import DeterministicEvaluationGate
from agentic_runtime.guardrails import DeterministicGuardrails
from agentic_runtime.knowledge import (
    KnowledgeRetriever,
    LocalKnowledgeRetriever,
    RetrievedPassage,
)
from agentic_runtime.models import (
    Category,
    Citation,
    Classification,
    CompletedState,
    Complexity,
    EvaluationGateResult,
    ExecutionMetrics,
    GuardrailReport,
    ImplementationProposal,
    ModelPolicy,
    PlanningInput,
    PlanningResult,
    RetrievalEvidence,
)
from agentic_runtime.provider import DeterministicProposalProvider, ProposalProvider


class RuntimeState(TypedDict):
    planning_input: PlanningInput
    completed_states: list[CompletedState]
    classification: NotRequired[Classification]
    model_policy: NotRequired[ModelPolicy]
    citations: NotRequired[tuple[Citation, ...]]
    passages: NotRequired[tuple[RetrievedPassage, ...]]
    retrieval: NotRequired[RetrievalEvidence]
    proposal: NotRequired[ImplementationProposal]
    guardrails: NotRequired[GuardrailReport]
    evaluation: NotRequired[EvaluationGateResult]
    metrics: NotRequired[ExecutionMetrics]


class DeterministicAgentRuntime:
    """Run an inspectable, checkpointed graph without network access."""

    def __init__(
        self,
        provider: ProposalProvider | None = None,
        retriever: KnowledgeRetriever | None = None,
        guardrails: DeterministicGuardrails | None = None,
        evaluation_gate: DeterministicEvaluationGate | None = None,
    ) -> None:
        self._provider = provider or DeterministicProposalProvider()
        self._retriever = retriever or LocalKnowledgeRetriever()
        self._guardrails = guardrails or DeterministicGuardrails()
        self._evaluation_gate = evaluation_gate or DeterministicEvaluationGate()
        builder = StateGraph(RuntimeState)
        builder.add_node("validate", self._validate)
        builder.add_node("guard_input", self._guard_input)
        builder.add_node("classify", self._classify)
        builder.add_node("build_context", self._build_context)
        builder.add_node("retrieve_local_policy", self._retrieve_local_policy)
        builder.add_node("plan", self._plan)
        builder.add_node("evaluate", self._evaluate)
        builder.add_edge(START, "validate")
        builder.add_edge("validate", "guard_input")
        builder.add_edge("guard_input", "classify")
        builder.add_edge("classify", "build_context")
        builder.add_edge("build_context", "retrieve_local_policy")
        builder.add_edge("retrieve_local_policy", "plan")
        builder.add_edge("plan", "evaluate")
        builder.add_edge("evaluate", END)
        self._graph = builder.compile(checkpointer=InMemorySaver())

    @staticmethod
    def _validate(state: RuntimeState) -> dict[str, object]:
        return {"completed_states": [*state["completed_states"], "validated"]}

    def _guard_input(self, state: RuntimeState) -> dict[str, object]:
        self._guardrails.check_input(state["planning_input"].request)
        return {"completed_states": [*state["completed_states"], "guarded"]}

    @staticmethod
    def _classify(state: RuntimeState) -> dict[str, object]:
        request = state["planning_input"].request.lower()
        if any(word in request for word in ("security", "auth", "permission", "secret")):
            category: Category = "security"
        elif any(word in request for word in ("integrat", "api", "webhook", "provider")):
            category = "integration"
        elif any(word in request for word in ("data", "database", "migration", "schema")):
            category = "data"
        else:
            category = "general"

        high_risk = category in {"security", "data"} or len(request) > 300
        medium_risk = category == "integration" or len(request) > 120
        complexity: Complexity = "high" if high_risk else "medium" if medium_risk else "low"
        classification = Classification(
            category=category,
            complexity=complexity,
            reason="rules-v1 category, risk, and request-size policy",
        )
        return {
            "classification": classification,
            "completed_states": [*state["completed_states"], "classified"],
        }

    @staticmethod
    def _build_context(state: RuntimeState) -> dict[str, object]:
        policy = ModelPolicy(reason="Local mode requires reproducible zero-cost structured output.")
        return {
            "model_policy": policy,
            "completed_states": [*state["completed_states"], "context_built"],
        }

    def _retrieve_local_policy(self, state: RuntimeState) -> dict[str, object]:
        batch = self._retriever.retrieve(
            state["planning_input"].request, state["classification"].category
        )
        passages, quarantined = self._guardrails.filter_retrieval(batch.passages)
        citations = tuple(
            Citation(
                documentId=passage.document.document_id,
                title=passage.document.title,
                section=passage.document.section,
                version=passage.document.version,
                excerptHash=passage.content_hash,
                relevanceScore=passage.relevance_score,
            )
            for passage in passages
        )
        return {
            "citations": citations,
            "passages": passages,
            "retrieval": RetrievalEvidence(
                corpusVersion=batch.corpus_version,
                selectedDocumentIds=tuple(item.document.document_id for item in passages),
                quarantinedDocumentIds=quarantined,
            ),
            "completed_states": [*state["completed_states"], "knowledge_retrieved"],
        }

    def _plan(self, state: RuntimeState) -> dict[str, object]:
        classification = state["classification"]
        proposal = self._provider.generate(
            state["planning_input"], classification, state["passages"]
        )
        input_tokens = max(1, len(state["planning_input"].request) // 4)
        input_tokens += sum(len(item.document.content) // 4 for item in state["passages"])
        output_tokens = max(1, len(proposal.summary) // 4 + len(proposal.delivery_steps) * 12)
        return {
            "proposal": proposal,
            "metrics": ExecutionMetrics(
                estimatedInputTokens=input_tokens,
                estimatedOutputTokens=output_tokens,
            ),
            "completed_states": [*state["completed_states"], "planned"],
        }

    def _evaluate(self, state: RuntimeState) -> dict[str, object]:
        output_patterns = self._guardrails.check_output(state["proposal"])
        evaluation = self._evaluation_gate.evaluate(
            state["proposal"], state["citations"], state["passages"], output_patterns
        )
        if not evaluation.passed:
            raise EvaluationGateBlocked(evaluation)
        retrieval_outcome: Literal["passed", "filtered"] = (
            "filtered" if state["retrieval"].quarantined_document_ids else "passed"
        )
        return {
            "evaluation": evaluation,
            "guardrails": GuardrailReport(
                policyVersion=self._guardrails.policy_version,
                retrievalOutcome=retrieval_outcome,
            ),
            "completed_states": [*state["completed_states"], "evaluated"],
        }

    def plan(self, planning_input: PlanningInput) -> PlanningResult:
        """Execute one workflow thread and validate its structured output."""

        output = cast(
            RuntimeState,
            self._graph.invoke(
                {"planning_input": planning_input, "completed_states": []},
                config={"configurable": {"thread_id": planning_input.workflow_id}},
            ),
        )
        return PlanningResult(
            classification=output["classification"],
            modelPolicy=output["model_policy"],
            proposal=output["proposal"],
            citations=output["citations"],
            retrieval=output["retrieval"],
            guardrails=output["guardrails"],
            evaluation=output["evaluation"],
            metrics=output["metrics"],
            completedStates=tuple(output["completed_states"]),
        )
