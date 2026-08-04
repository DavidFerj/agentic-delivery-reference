"""Narrow, versioned guardrails for the deterministic local profile."""

import re

from agentic_runtime.errors import PromptInjectionBlocked
from agentic_runtime.knowledge import RetrievedPassage
from agentic_runtime.models import ImplementationProposal

PATTERNS = {
    "instruction_override": re.compile(
        r"\b(ignore|disregard|override)\b.{0,40}\b(previous|prior|system|developer)\b",
        re.IGNORECASE,
    ),
    "secret_exfiltration": re.compile(
        r"\b(reveal|print|return|expose)\b.{0,40}\b(secret|credential|system prompt|token)\b",
        re.IGNORECASE,
    ),
}


class DeterministicGuardrails:
    policy_version = "local-guardrails-v1"

    @staticmethod
    def detected_patterns(text: str) -> tuple[str, ...]:
        return tuple(name for name, pattern in PATTERNS.items() if pattern.search(text))

    def check_input(self, text: str) -> None:
        if self.detected_patterns(text):
            raise PromptInjectionBlocked(
                "The request contains an instruction-override pattern and was blocked."
            )

    def filter_retrieval(
        self, passages: tuple[RetrievedPassage, ...]
    ) -> tuple[tuple[RetrievedPassage, ...], tuple[str, ...]]:
        safe: list[RetrievedPassage] = []
        quarantined: list[str] = []
        for passage in passages:
            if self.detected_patterns(passage.document.content):
                quarantined.append(passage.document.document_id)
            else:
                safe.append(passage)
        return tuple(safe), tuple(quarantined)

    def check_output(self, proposal: ImplementationProposal) -> tuple[str, ...]:
        text = " ".join((proposal.summary, *proposal.delivery_steps, *proposal.risks))
        return self.detected_patterns(text)
