"""Versioned CI portability replay for v3; the frozen eight-ULP check remains intact.

Python 3.11's binomial inversion differs by at most 1.2e-15 in two
subtracted confidence-interval bounds. Permit 1e-12 absolute drift only in
those six bounds. Counts, outcomes, p-values, gate decisions, archive bytes
and report text must match exactly.
"""

from __future__ import annotations

import copy
import json
import math
from typing import Any

from research.check_paired_v3 import check_development_replay, same_summary
from research.paired_cross_system_v2.diagnostic import check as check_diagnostic
from research.paired_cross_system_v3.report import report
from research.paired_cross_system_v3.runner import ROOT, SYSTEMS, analyze, check_phase

CI_ABSOLUTE_TOLERANCE = 1e-12


def portable_summary(actual: dict[str, Any], expected: dict[str, Any]) -> bool:
    candidate = copy.deepcopy(actual)
    for system in SYSTEMS[1:]:
        try:
            bounds = candidate["paired_comparisons"][system]["conservative_paired_ci"]
            frozen = expected["paired_comparisons"][system]["conservative_paired_ci"]
            if len(bounds) != 2 or len(frozen) != 2:
                return False
            for index in (0, 1):
                value, reference = bounds[index], frozen[index]
                if (
                    type(value) is not float
                    or type(reference) is not float
                    or not math.isfinite(value)
                    or not math.isfinite(reference)
                    or abs(value - reference) > CI_ABSOLUTE_TOLERANCE
                ):
                    return False
                bounds[index] = reference
        except (KeyError, IndexError, TypeError):
            return False
    return same_summary(candidate, expected)


def check() -> None:
    check_diagnostic()
    check_development_replay()
    check_phase("development")
    # analyze checks source/receipt history, all planned slots and archived bytes.
    actual = analyze()
    expected = json.loads((ROOT / "summary.json").read_text())
    if not portable_summary(actual, expected):
        raise ValueError("v3 summary differs beyond CI-bound portability tolerance")
    if report(actual) != (ROOT / "REPORT.md").read_text():
        raise ValueError("v3 report differs from recomputed evidence")
    print("v3 versioned portable replay: PASS")


if __name__ == "__main__":
    check()
