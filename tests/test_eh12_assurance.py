from __future__ import annotations

import json
from copy import deepcopy

import pytest
from research.eh12_assurance_corpus import (
    DEFAULT_RESULTS,
    RAW_RESULT_NAME,
    SUMMARY_NAME,
    AssuranceCorpusError,
    generate,
    load_manifest,
    validate_manifest,
)


def test_manifest_freezes_three_distinct_pairwise_fixtures() -> None:
    manifest = load_manifest()
    fixtures = manifest["fixtures"]

    assert len(fixtures) == 3
    assert len({fixture["id"] for fixture in fixtures}) == 3
    assert len({fixture["seed"] for fixture in fixtures}) == 3
    assert {fixture["interaction"] for fixture in fixtures} == {
        "modulation+modal_mixture",
        "modulation+secondary_harmony",
        "modal_mixture+secondary_harmony",
    }


def test_schema_matrix_covers_every_declared_family_and_legacy_schema() -> None:
    manifest, rows, summary = generate()
    schema_rows = [row for row in rows if row["family"] == "schema-adversarial"]

    assert len(schema_rows) == 26
    assert all(row["outcome"] == "BLOCKED" for row in schema_rows)
    assert all(not row["crashed"] for row in schema_rows)
    assert set(summary["schema_adversarial"]["families"]) == set(
        manifest["required_schema_families"]
    )
    assert summary["schema_adversarial"]["legacy_versions"] == ["2.12"]


def test_all_raw_cases_are_adjudicated_without_crashes_or_exclusions() -> None:
    _manifest, rows, summary = generate()

    assert len(rows) == 39
    assert summary["overall"]["adjudicated"] == 39
    assert summary["overall"]["crashes"] == 0
    assert summary["overall"]["exclusions"] == 0
    assert all(row["adjudicated"] for row in rows)


def test_full_piece_controls_and_faults_have_stable_identities() -> None:
    _manifest, rows, summary = generate()
    controls = [row for row in rows if row["family"] == "fixture-control"]
    faults = [row for row in rows if row["family"] == "interaction-fault"]

    assert len(controls) == len(faults) == 3
    assert {row["fixture_id"] for row in controls} == {
        row["fixture_id"] for row in faults
    }
    assert all(row["outcome"] == "ACCEPT" for row in controls)
    assert all(row["outcome"] == "REJECT" for row in faults)
    assert len({fixture["composition_sha256"] for fixture in summary["fixtures"]}) == 3
    assert len({fixture["request_sha256"] for fixture in summary["fixtures"]}) == 3


def test_pairwise_interaction_controls_use_disjoint_witness_beats() -> None:
    _manifest, rows, _summary = generate()
    controls = {
        row["fixture_id"]: row for row in rows if row["family"] == "fixture-control"
    }

    mod_modal = controls["modulation-modal"]["details"]
    assert mod_modal["modulation_boundary"] not in mod_modal["modal_beats"]

    mod_secondary = controls["modulation-secondary"]["details"]
    assert (
        mod_secondary["modulation_boundary"]
        not in mod_secondary["secondary_beats"]
    )

    modal_secondary = controls["modal-secondary-rhythm"]["details"]
    assert set(modal_secondary["modal_beats"]).isdisjoint(
        modal_secondary["secondary_beats"]
    )


def test_delivery_controls_preserve_exact_parseback_and_digests() -> None:
    _manifest, rows, summary = generate()
    delivery = [row for row in rows if row["family"] == "delivery-control"]

    assert len(delivery) == 4
    assert summary["delivery"] == {
        "controls": 4,
        "accepted": 4,
        "profiles": ["certified-satb", "melody-plus-satb"],
    }
    assert all(row["details"]["parseback_event_count"] > 0 for row in delivery)
    assert all(len(row["details"]["output_sha256"]) == 64 for row in delivery)
    articulated = [
        row
        for row in delivery
        if row["details"]["profile"] == "melody-plus-satb"
    ]
    assert len(articulated) == 1
    assert articulated[0]["details"]["rhythm_articulated"] is True


def test_three_named_compiler_deletions_span_distinct_phases() -> None:
    _manifest, rows, summary = generate()
    deletions = [row for row in rows if row["family"] == "compiler-deletion"]

    assert summary["compiler_deletions"] == {
        "cases": 3,
        "distinct_registered_phases": 3,
        "escaped_faults": 0,
    }
    assert {row["details"]["registered_phase"]["phase"] for row in deletions} == {
        "harmony",
        "rhythm",
        "secondary_seventh_satb",
    }
    assert all(row["details"]["verifier_valid"] is False for row in deletions)
    assert all(row["details"]["boundary_outcome"] == "REJECT" for row in deletions)


def test_checked_in_evidence_matches_current_implementation() -> None:
    _manifest, rows, summary = generate()
    persisted_rows = [
        json.loads(line)
        for line in (DEFAULT_RESULTS / RAW_RESULT_NAME)
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    persisted_summary = json.loads(
        (DEFAULT_RESULTS / SUMMARY_NAME).read_text(encoding="utf-8")
    )

    assert persisted_rows == json.loads(json.dumps(rows))
    assert persisted_summary == json.loads(json.dumps(summary))


def test_manifest_rejects_duplicate_fixture_seed() -> None:
    manifest = deepcopy(load_manifest())
    manifest["fixtures"][1]["seed"] = manifest["fixtures"][0]["seed"]

    with pytest.raises(AssuranceCorpusError, match="unique IDs and seeds"):
        validate_manifest(manifest)
