"""Deterministic grounding and safety gate executed before tool proposal creation."""

from agentic_runtime.knowledge import RetrievedPassage
from agentic_runtime.models import (
    Citation,
    EvaluationCheck,
    EvaluationGateResult,
    ImplementationProposal,
)


class DeterministicEvaluationGate:
    gate_version = "local-evaluation-gate-v1"
    threshold = 1.0

    def evaluate(
        self,
        proposal: ImplementationProposal,
        citations: tuple[Citation, ...],
        passages: tuple[RetrievedPassage, ...],
        output_patterns: tuple[str, ...],
    ) -> EvaluationGateResult:
        passage_by_id = {item.document.document_id: item for item in passages}
        checks = (
            EvaluationCheck(
                name="structured_output",
                passed=bool(proposal.summary and proposal.delivery_steps),
            ),
            EvaluationCheck(name="citation_present", passed=bool(citations)),
            EvaluationCheck(
                name="citation_integrity",
                passed=bool(citations)
                and all(
                    citation.document_id in passage_by_id
                    and citation.excerpt_hash == passage_by_id[citation.document_id].content_hash
                    for citation in citations
                ),
            ),
            EvaluationCheck(
                name="grounded_guidance",
                passed=any(
                    passage.document.content in proposal.delivery_steps for passage in passages
                ),
            ),
            EvaluationCheck(name="output_safety", passed=not output_patterns),
        )
        score = sum(check.passed for check in checks) / len(checks)
        return EvaluationGateResult(
            gateVersion=self.gate_version,
            passed=score >= self.threshold,
            score=score,
            threshold=self.threshold,
            checks=checks,
        )
