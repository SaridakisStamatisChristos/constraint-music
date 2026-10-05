from __future__ import annotations

import json
from pathlib import Path

from research.compiler_deletions import compiler_constraint_deletion_report
from research.cross_feature_differential import cross_feature_differential_report
from research.differential_check import (
    bounded_conformance_report,
    enumerate_absolute_register_domain,
    enumerate_context_anchor_domain,
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


def test_context_anchor_partition_matches_every_bounded_local_decision() -> None:
    result = enumerate_context_anchor_domain()

    assert result["visited"] == 680
    assert result["visited"] == result["accepted"] + result["rejected"]
    assert result["accepted"] == 83
    assert result["categories"] == {
        "authentic_cadence:accept": 15,
        "authentic_cadence:reject": 125,
        "modulation:accept": 40,
        "modulation:reject": 360,
        "open_form:accept": 28,
        "open_form:reject": 112,
    }
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
    assert report["schema_version"] == 2
    assert set(report["partitions"]) == {
        "absolute_register",
        "context_anchor",
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


def test_named_compiler_constraint_deletion_is_caught_at_every_boundary() -> None:
    result = compiler_constraint_deletion_report()
    deletion = result["deletion"]

    assert result["deleted_constraints"] == 1
    assert result["escaped_faults"] == 0
    assert isinstance(deletion, dict)
    assert deletion["constraint_name"] == "CM057.root.beat-0.voice-2"
    assert deletion["oracle_valid"] is False
    assert deletion["verifier_valid"] is False
    assert deletion["boundary_outcome"] == "REJECT"
    assert deletion["failed_rules"] == ("CM057",)
    registration = deletion["registered_phase"]
    assert isinstance(registration, dict)
    assert registration["constraint_start"] <= deletion["constraint_index"]
    assert deletion["constraint_index"] < registration["constraint_end"]


def test_cross_feature_controls_accept_and_targeted_faults_do_not_escape() -> None:
    result = cross_feature_differential_report()

    assert result["visited"] == 10
    assert result["controls_accepted"] == 5
    assert result["faults_rejected"] == 5
    assert result["disagreements"] == 0
    assert result["escaped_faults"] == 0
    cases = result["cases"]
    assert isinstance(cases, list)
    assert {case["feature"] for case in cases} == {
        "authentic_cadence",
        "modal_mixture",
        "modulation",
        "rhythm",
        "tonicization",
    }
    for case in cases:
        fault = case["fault"]
        assert isinstance(fault, dict)
        assert fault["expected_rule"] in fault["failed_rules"]
