"""Deterministic structured-output provider with no network or model dependency."""

from typing import Protocol

from agentic_runtime.knowledge import RetrievedPassage
from agentic_runtime.models import Classification, ImplementationProposal, PlanningInput


class ProposalProvider(Protocol):
    """Generate a validated proposal from trusted structured context."""

    def generate(
        self,
        planning_input: PlanningInput,
        classification: Classification,
        passages: tuple[RetrievedPassage, ...],
    ) -> ImplementationProposal: ...


class DeterministicProposalProvider:
    """Produce stable local output through versioned rules."""

    def generate(
        self,
        planning_input: PlanningInput,
        classification: Classification,
        passages: tuple[RetrievedPassage, ...],
    ) -> ImplementationProposal:
        category_step = {
            "general": "Define the bounded delivery outcome and acceptance criteria.",
            "integration": "Define the external contract behind a replaceable adapter.",
            "security": "Threat-model the affected trust boundaries and controls.",
            "data": "Define the data contract, consistency rules, and migration path.",
        }[classification.category]
        return ImplementationProposal(
            summary=(
                f"Prepare a {classification.complexity}-complexity "
                f"{classification.category} delivery for: {planning_input.request}"
            ),
            complexity=classification.complexity,
            deliverySteps=(
                category_step,
                (
                    passages[0].document.content
                    if passages
                    else "Stop when no grounded guidance exists."
                ),
                "Implement the smallest complete vertical slice.",
                "Validate contracts, failure modes, security, and observability.",
                "Package reproducible local deployment evidence.",
            ),
            risks=(
                "Requirements may change after stakeholder review.",
                "External adapters remain disabled and require later contract verification.",
            ),
        )
