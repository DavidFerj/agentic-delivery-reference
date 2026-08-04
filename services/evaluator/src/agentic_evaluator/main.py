"""Evaluator command for the deterministic Phase 5 release gate."""

import os
from pathlib import Path

from agentic_evaluator.golden import load_golden_set, report_json, run_golden_set

DEFAULT_GOLDEN_SET = Path("evaluations/golden-set/deterministic-v1.json")


def main() -> int:
    path = Path(os.environ.get("ADR_GOLDEN_SET_PATH", str(DEFAULT_GOLDEN_SET)))
    report = run_golden_set(load_golden_set(path))
    print(report_json(report))
    return 0 if report.passed else 1
