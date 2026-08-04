"""Hexagonal ports for replaceable data governance capabilities."""

from typing import Protocol

from agentic_governance.models import DataCategory, DataProfile, PolicyDecision, ProcessingContext


class DataClassifier(Protocol):
    def classify(
        self, text: str, declared_categories: set[DataCategory] | None = None
    ) -> DataProfile: ...


class PolicyDecisionPoint(Protocol):
    def evaluate(self, context: ProcessingContext) -> PolicyDecision: ...
