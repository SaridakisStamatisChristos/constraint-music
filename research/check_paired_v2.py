"""Portable replay wrapper; the prospectively frozen v2 code remains unchanged."""

from __future__ import annotations

import json
import math
from typing import Any

from research.paired_cross_system_v2.contract import SYSTEMS
from research.paired_cross_system_v2.diagnostic import check as check_diagnostic
from research.paired_cross_system_v2.report import report
from research.paired_cross_system_v2.runner import ROOT, analyze, check_phase


def same_summary(actual: Any, expected: Any, path: tuple = ()) -> bool:
    """Exact types/structure/values, except at most eight ULPs on the two CI bounds."""
    if type(actual) is not type(expected):
        return False
    if isinstance(actual, dict):
        return actual.keys() == expected.keys() and all(
            same_summary(actual[key], expected[key], (*path, key)) for key in actual
        )
    if isinstance(actual, list):
        return len(actual) == len(expected) and all(
            same_summary(a, b, (*path, index))
            for index, (a, b) in enumerate(zip(actual, expected, strict=True))
        )
    if (
        type(actual) is float
        and len(path) == 4
        and path[0] == "paired_comparisons"
        and path[1] in SYSTEMS[1:]
        and path[2] == "conservative_paired_ci"
        and path[3] in (0, 1)
    ):
        return (
            math.isfinite(actual)
            and math.isfinite(expected)
            and abs(actual - expected) <= 8 * max(math.ulp(actual), math.ulp(expected))
        )
    return actual == expected


def check() -> None:
    check_diagnostic()
    check_phase("development")
    # analyze verifies all frozen source objects and the complete heldout archive.
    summary = analyze()
    if not same_summary(summary, json.loads((ROOT / "summary.json").read_text())):
        raise ValueError("summary differs beyond allowed CI-bound rounding")
    if report(summary) != (ROOT / "REPORT.md").read_text():
        raise ValueError("report differs from recomputed evidence")
    print("v2 portable raw replay and paired analysis: PASS")


if __name__ == "__main__":
    check()
