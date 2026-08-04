"""Safe runtime failures raised before an action can be proposed."""

from agentic_runtime.models import EvaluationGateResult


class PromptInjectionBlocked(Exception):
    """A recognized instruction-override pattern was rejected."""


class EvaluationGateBlocked(Exception):
    """The deterministic quality gate rejected a planning result."""

    def __init__(self, result: EvaluationGateResult) -> None:
        super().__init__("The deterministic evaluation gate did not pass.")
        self.result = result
