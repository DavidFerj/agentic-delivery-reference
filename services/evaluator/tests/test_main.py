"""Golden-set evaluator behavior and command tests."""

import json
from pathlib import Path

import pytest
from agentic_runtime import DeterministicAgentRuntime
from agentic_runtime.errors import EvaluationGateBlocked
from agentic_runtime.models import EvaluationGateResult, PlanningInput, PlanningResult

from agentic_evaluator.golden import GoldenCase, GoldenSet, load_golden_set, run_golden_set
from agentic_evaluator.main import main

ROOT = Path(__file__).resolve().parents[3]


def test_versioned_golden_set_passes_every_case() -> None:
    report = run_golden_set(load_golden_set(ROOT / "evaluations/golden-set/deterministic-v1.json"))

    assert report.passed is True
    assert report.pass_rate == report.threshold == 1
    assert len(report.results) == 5
    assert all(item.passed for item in report.results)


def test_main_prints_machine_readable_gate_report(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(ROOT)

    assert main() == 0
    report = json.loads(capsys.readouterr().out)
    assert report["goldenSetVersion"] == "deterministic-v1"
    assert report["passed"] is True


def test_main_honors_explicit_golden_set_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "golden.json"
    path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "version": "empty-v1",
                "cases": [],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("ADR_GOLDEN_SET_PATH", str(path))

    assert main() == 1
    assert json.loads(capsys.readouterr().out)["passRate"] == 0


class AlwaysFailedRuntime(DeterministicAgentRuntime):
    def plan(self, planning_input: PlanningInput) -> PlanningResult:
        raise EvaluationGateBlocked(
            EvaluationGateResult(
                gateVersion="test",
                passed=False,
                score=0,
                threshold=1,
                checks=(),
            )
        )


def test_runner_records_mismatch_and_evaluation_block() -> None:
    golden_set = GoldenSet(
        schemaVersion=1,
        version="negative-v1",
        cases=(
            GoldenCase(
                id="mismatch",
                request="Prepare a general plan",
                expectedOutcome="planned",
                expectedCategory="data",
                expectedComplexity="high",
                minimumCitations=3,
            ),
        ),
    )
    mismatch = run_golden_set(golden_set)
    blocked = run_golden_set(golden_set, AlwaysFailedRuntime)

    assert mismatch.passed is False
    assert mismatch.results[0].actual_outcome == "planned"
    assert blocked.results[0].actual_outcome == "evaluation_blocked"
    assert blocked.results[0].passed is False
