from __future__ import annotations

import copy

from research.check_paired_v3_portable import portable_summary
from research.paired_cross_system_v3.runner import SYSTEMS


def test_portable_v3_comparison_limits_only_ci_bound_rounding():
    expected = {
        "paired_comparisons": {
            system: {
                "conservative_paired_ci": [0.023394439417224966, 0.23008555785856383],
                "exact_mcnemar_two_sided_p": 0.01,
                "superiority_gate": False,
            }
            for system in SYSTEMS[1:]
        },
        "adapted_reproducible_pass": {"constraint-music": 128},
    }
    candidate = copy.deepcopy(expected)
    candidate["paired_comparisons"]["music21"]["conservative_paired_ci"][0] += 2e-15
    assert portable_summary(candidate, expected)

    large_drift = copy.deepcopy(candidate)
    large_drift["paired_comparisons"]["music21"]["conservative_paired_ci"][0] += 2e-12
    assert not portable_summary(large_drift, expected)

    changed_p_value = copy.deepcopy(candidate)
    changed_p_value["paired_comparisons"]["music21"]["exact_mcnemar_two_sided_p"] = 0.02
    assert not portable_summary(changed_p_value, expected)

    changed_count = copy.deepcopy(candidate)
    changed_count["adapted_reproducible_pass"]["constraint-music"] = 127
    assert not portable_summary(changed_count, expected)

    changed_gate = copy.deepcopy(candidate)
    changed_gate["paired_comparisons"]["music21"]["superiority_gate"] = True
    assert not portable_summary(changed_gate, expected)
