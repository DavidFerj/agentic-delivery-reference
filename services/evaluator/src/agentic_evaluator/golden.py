"""Versioned deterministic golden-set runner."""

import json
from collections.abc import Callable
from pathlib import Path

from agentic_runtime import (
    DeterministicAgentRuntime,
    EvaluationGateBlocked,
    PromptInjectionBlocked,
)
from agentic_runtime.models import Category, Complexity, PlanningInput
from pydantic import BaseModel, ConfigDict, Field


class GoldenCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(alias="id")
    request: str
    expected_outcome: str = Field(alias="expectedOutcome")
    expected_category: Category | None = Field(default=None, alias="expectedCategory")
    expected_complexity: Complexity | None = Field(default=None, alias="expectedComplexity")
    minimum_citations: int = Field(alias="minimumCitations", ge=0)


class GoldenSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(alias="schemaVersion")
    version: str
    cases: tuple[GoldenCase, ...]


class GoldenCaseResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(alias="caseId")
    passed: bool
    actual_outcome: str = Field(alias="actualOutcome")


class GoldenSetReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(default=1, alias="schemaVersion")
    golden_set_version: str = Field(alias="goldenSetVersion")
    passed: bool
    pass_rate: float = Field(alias="passRate", ge=0, le=1)
    threshold: float = Field(default=1.0, ge=0, le=1)
    results: tuple[GoldenCaseResult, ...]


def load_golden_set(path: Path) -> GoldenSet:
    return GoldenSet.model_validate_json(path.read_text(encoding="utf-8"))


def run_golden_set(
    golden_set: GoldenSet,
    runtime_factory: Callable[[], DeterministicAgentRuntime] = DeterministicAgentRuntime,
) -> GoldenSetReport:
    results: list[GoldenCaseResult] = []
    for case in golden_set.cases:
        runtime = runtime_factory()
        try:
            result = runtime.plan(
                PlanningInput(
                    workflow_id=f"golden-{case.case_id}",
                    owner_id="golden-set",
                    request=case.request,
                    requested_locale="en",
                    correlation_id=f"golden-{case.case_id}",
                )
            )
            actual_outcome = "planned"
            passed = (
                case.expected_outcome == actual_outcome
                and result.classification.category == case.expected_category
                and result.classification.complexity == case.expected_complexity
                and len(result.citations) >= case.minimum_citations
                and result.evaluation.passed
            )
        except PromptInjectionBlocked:
            actual_outcome = "blocked"
            passed = case.expected_outcome == actual_outcome
        except EvaluationGateBlocked:
            actual_outcome = "evaluation_blocked"
            passed = case.expected_outcome == actual_outcome
        results.append(
            GoldenCaseResult(caseId=case.case_id, passed=passed, actualOutcome=actual_outcome)
        )
    pass_rate = sum(item.passed for item in results) / len(results) if results else 0.0
    return GoldenSetReport(
        goldenSetVersion=golden_set.version,
        passed=pass_rate >= 1.0,
        passRate=pass_rate,
        results=tuple(results),
    )


def report_json(report: GoldenSetReport) -> str:
    return json.dumps(report.model_dump(by_alias=True, mode="json"), sort_keys=True)
