from __future__ import annotations

import json
from pathlib import Path

from research.differential_check import (
    bounded_conformance_report,
    enumerate_absolute_register_domain,
    enumerate_voice_resolution_domain,
    evaluate_complete_verifier_matrix,
)
from research.enumerate_fragments import enumerate_all_domains

_EVIDENCE = Path(__file__).parents[1] / "research/results/bounded_conformance.json"


def test_absolute_register_partition_is_complete_for_its_declared_bounds() -> None:
    result = enumerate_absolute_register_domain()

    assert result["generated"] == (
        result["visited"] + result["pruned_non_exact_role_assignment"]
    )
    assert result["visited"] == result["accepted"] + result["rejected"]
    assert result["visited"] > 0
    assert result["accepted"] > 0
    assert result["rejected"] > 0
    assert result["disagreements"] == 0
    assert result["first_disagreement"] is None


def test_voice_resolution_partition_matches_every_bounded_local_decision() -> None:
    result = enumerate_voice_resolution_domain()

    assert result["visited"] == result["accepted"] + result["rejected"]
    assert result["visited"] > 0
    assert result["accepted"] > 0
    assert result["rejected"] > 0
    assert result["disagreements"] == 0
    assert result["first_disagreement"] is None


def test_complete_verifier_matrix_accepts_controls_and_rejects_named_faults() -> None:
    result = evaluate_complete_verifier_matrix()

    assert result["visited"] == 24
    assert result["categories"] == {
        "none:oracle_accept": 8,
        "none:verifier_accept": 8,
        "register:oracle_reject": 8,
        "register:verifier_reject": 8,
        "resolution:oracle_reject": 8,
        "resolution:verifier_reject": 8,
    }
    assert result["disagreements"] == 0
    assert result["first_disagreement"] is None


def test_bounded_report_is_deterministic_json_with_pinned_sources() -> None:
    report = bounded_conformance_report()
    rendered = json.dumps(report, sort_keys=True)

    assert json.dumps(json.loads(rendered), sort_keys=True) == rendered
    assert set(report["partitions"]) == {
        "absolute_register",
        "voice_resolution",
        "complete_verifier",
    }
    assert all(
        len(digest) == 64 for digest in report["implementation_hashes"].values()
    )


def test_checked_in_bounded_evidence_matches_current_implementation() -> None:
    expected = json.loads(json.dumps(enumerate_all_domains()))
    persisted = json.loads(_EVIDENCE.read_text(encoding="utf-8"))

    assert persisted == expected
