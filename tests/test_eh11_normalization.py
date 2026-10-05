from __future__ import annotations

from research.normalize_eh11_results import normalize_rows


def test_known_one_bar_combined_scope_error_becomes_explicit_exclusion() -> None:
    source = {
        "workload": "single",
        "profile": "combined_borrowed_modulation",
        "bars": 1,
        "outcome": "internal_error",
        "solver_status": "ERROR",
        "error_type": "ValueError",
        "error": (
            "minimum_borrowed_chords exceeds beats available outside the "
            "preserved cadential/context boundary"
        ),
        "excluded_count": 0,
    }
    row = normalize_rows([source])[0]
    assert row["outcome"] == "excluded"
    assert row["excluded_count"] == 1
    assert row["solver_status"] == "NOT_RUN"
    assert row["original_outcome"] == "internal_error"
    assert row["original_solver_status"] == "ERROR"
    assert row["normalization"] == "scope_exclusion"


def test_unrelated_internal_error_is_never_reclassified() -> None:
    source = {
        "workload": "single",
        "profile": "secondary_harmony",
        "bars": 1,
        "outcome": "internal_error",
        "solver_status": "ERROR",
        "error_type": "ValueError",
        "error": "Pitch class 10 is outside C major",
        "excluded_count": 0,
    }
    assert normalize_rows([source])[0] == source


def test_different_combined_error_is_never_reclassified() -> None:
    source = {
        "workload": "single",
        "profile": "combined_borrowed_modulation",
        "bars": 1,
        "outcome": "internal_error",
        "solver_status": "ERROR",
        "error_type": "ValueError",
        "error": "different defect",
        "excluded_count": 0,
    }
    assert normalize_rows([source])[0] == source
