"""Protocol and evidence accounting checks independent of favorable detection outcomes."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import replace

import pytest
from research import multifixture_assurance as study
from research.multifixture_mutations import apply_mutation

from constraint_music.midi import write_midi
from constraint_music.provenance import artifact_payload


def test_manifest_has_fixed_disjoint_requests_and_fault_clusters():
    manifest = study.load_manifest()
    assert manifest["planned_attempts"] == 16
    assert manifest["planned_controls"] == 32
    assert manifest["planned_mutation_slots"] == 488
    assert study._frozen_protocol(manifest)["protocol_commit"].startswith("9823544")
    for field in ("id", "seed"):
        values = [f["id"] if field == "id" else f["spec"]["seed"] for f in manifest["fixtures"]]
        assert len(set(values)) == 16


@pytest.mark.parametrize("corruption", ["duplicate", "seed", "cluster", "count", "workers"])
def test_manifest_rejects_accounting_and_split_drift(corruption):
    manifest = deepcopy(study.load_manifest())
    if corruption == "duplicate":
        manifest["fixtures"][1]["id"] = manifest["fixtures"][0]["id"]
    elif corruption == "seed":
        manifest["fixtures"][1]["spec"]["seed"] = manifest["fixtures"][0]["spec"]["seed"]
    elif corruption == "cluster":
        manifest["mutations"][-1]["cluster"] = manifest["mutations"][0]["cluster"]
    elif corruption == "count":
        manifest["planned_mutation_slots"] -= 1
    else:
        manifest["fixtures"][0]["spec"]["workers"] = 2
    with pytest.raises(ValueError):
        study.validate_manifest(manifest)


def _failed_archive(tmp_path, monkeypatch):
    manifest = study.load_manifest()
    attestation = {
        **study._frozen_protocol(manifest),
        "implementation_hashes": study.implementation_hashes(),
        "implementation_sha256": study.digest(study.implementation_hashes()),
    }
    candidates = []
    for i, f in enumerate(manifest["fixtures"]):
        spec = study.GenerationSpec.from_mapping(f["spec"])
        candidates.append(
            {
                "fixture_id": f["id"],
                "request_sha256": study.request_digest(spec),
                "outcome": "UNKNOWN" if i % 2 else "INFEASIBLE",
                "solver_status": "UNKNOWN" if i % 2 else "INFEASIBLE",
                "payload": None,
                "midi": {},
                "issues": ["fixed test failure"],
            }
        )
    (tmp_path / "candidates.json").write_text(
        json.dumps({"attestation": attestation, "candidates": candidates})
    )
    # Evaluating unavailable slots must never run mutation code or a checker.
    monkeypatch.setattr(study, "apply_mutation", lambda *_: pytest.fail("unavailable mutation"))
    return manifest


def test_failed_generation_retains_every_planned_slot_and_status(tmp_path, monkeypatch):
    manifest = _failed_archive(tmp_path, monkeypatch)
    rows = study.evaluate(tmp_path)
    summary = study.summarize(rows)
    assert summary["counts"] == {"attempts": 16, "controls": 32, "attacks": 488, "rows": 536}
    assert sum(r["UNKNOWN"] for r in summary["candidate_yield"]) == 8
    assert sum(r["INFEASIBLE"] for r in summary["candidate_yield"]) == 8
    assert sum(r["GENERATION_FAILED"] for r in summary["fault_results"]) == 488
    assert summary["shortfalls"] == {"development": 4, "evaluation": 12}
    assert all(r["clusters"] == 0 and r["wilson_95"] is None for r in summary["uncertainty"])
    with pytest.raises(ValueError, match="missing, duplicate"):
        study.validate_rows(manifest, rows[:-1])
    with pytest.raises(ValueError, match="missing, duplicate"):
        study.validate_rows(manifest, [*rows, rows[0]])


def test_fixture_interval_does_not_treat_perfect_sample_as_population_certainty():
    interval = study.wilson(12, 12)
    assert interval is not None and 0.75 < interval[0] < 0.76 and interval[1] == 1
    assert study.wilson(0, 0) is None


def test_development_mutations_preserve_controls_and_do_not_query_checker(tmp_path, solved_piece):
    payload = artifact_payload(replace(solved_piece, wall_time_seconds=0))
    before = deepcopy(payload)
    path = write_midi(solved_piece, tmp_path / "dev.mid", profile="certified-satb")
    data = path.read_bytes()
    definitions = [m for m in study.load_manifest()["mutations"] if m["split"] == "development"]
    for definition in definitions:
        applied = apply_mutation(definition, payload, data, "certified-satb")
        assert applied.applicability == "APPLIED"
        assert applied.witness["obligation"] == definition["obligation"]
        assert applied.payload != payload or applied.midi != data
        if definition["family"] == "delivery":
            assert applied.payload == payload
    assert payload == before and path.read_bytes() == data


def test_crash_is_never_successful_rejection(tmp_path, solved_piece, monkeypatch):
    payload = artifact_payload(solved_piece)
    path = write_midi(solved_piece, tmp_path / "crash.mid", profile="certified-satb")

    def crash(*_args, **_kwargs):
        raise RuntimeError("injected checker crash")

    monkeypatch.setattr(study, "certify_delivery", crash)
    row = study.observe(payload, path.read_bytes(), solved_piece.spec, "certified-satb", path)
    assert row["outcome"] == "CRASH" and row["detected_by"] == []
    assert row["first_rejecting_boundary"] is None


def test_oracle_harness_exception_preserves_production_outcome(tmp_path, solved_piece, monkeypatch):
    payload = artifact_payload(solved_piece)
    path = write_midi(solved_piece, tmp_path / "oracle.mid", profile="certified-satb")

    def crash(*_args, **_kwargs):
        raise RuntimeError("injected research oracle exception")

    monkeypatch.setattr(study, "_oracle", crash)
    row = study.observe(payload, path.read_bytes(), solved_piece.spec, "certified-satb", path)
    assert row["outcome"] == "HARNESS_ERROR" and row["production_outcome"] == "ACCEPT"
    assert not row["crashed"]


def test_archived_summary_is_exactly_derived_from_all_raw_rows():
    directory = study.RESULTS
    rows = [json.loads(line) for line in (directory / "raw.jsonl").read_text().splitlines()]
    manifest = study.load_manifest()
    study.validate_rows(manifest, rows)
    assert study.summarize(rows) == json.loads((directory / "summary.json").read_text())
    archive = json.loads((directory / "candidates.json").read_text())
    for split, count in (("development", 4), ("evaluation", 12)):
        candidates = [c for c in archive["candidates"] if c["split"] == split]
        # Musical content itself must be distinct; seed-bearing request hashes are insufficient.
        assert len({study.digest(c["payload"]["music"]) for c in candidates}) == count


def test_accepted_attack_and_checker_crash_remain_findings():
    rows = [json.loads(line) for line in (study.RESULTS / "raw.jsonl").read_text().splitlines()]
    attack = next(
        r
        for r in rows
        if r["kind"] == "attack" and r["split"] == "evaluation" and r["applicability"] == "APPLIED"
    )
    attack["outcome"] = "ACCEPT"
    summary = study.summarize(rows)
    assert attack["case_id"] in summary["findings"]
    assert (
        next(u for u in summary["uncertainty"] if u["split"] == "evaluation")[
            "all_detected_clusters"
        ]
        == 11
    )
    attack["outcome"] = "CRASH"
    assert attack["case_id"] in study.summarize(rows)["findings"]
