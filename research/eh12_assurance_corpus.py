"""Generate the versioned EH-12 consolidated assurance corpus."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from copy import deepcopy
from dataclasses import replace
from functools import cache
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from constraint_music.artifact_validation import (
    CURRENT_SCHEMA_VERSION,
    SUPPORTED_SCHEMA_VERSIONS,
    ArtifactShapeError,
)
from constraint_music.certification import certify_delivery, verify_artifact
from constraint_music.delivery import RenderProfile, output_digest
from constraint_music.midi import write_midi
from constraint_music.modal_mixture import canonical_modal_source
from constraint_music.models import GenerationSpec
from constraint_music.modulation_runtime import ModulatedSatbGenerationResult
from constraint_music.provenance import artifact_payload, request_digest
from constraint_music.satb import SatbGenerationResult
from constraint_music.secondary_leading_tone_seventh_runtime import (
    reconstruct_secondary_leading_tone_seventh,
)
from constraint_music.solver import ConstraintMusicSolver
from constraint_music.theory import Key
from constraint_music.verifier import verify_result

from .compiler_deletions import expanded_compiler_constraint_deletion_report
from .oracle.contextual_harmony import TonalMode
from .oracle.modulation import OracleKey, adjudicate_modulation_plan
from .oracle.secondary_seventh import adjudicate_secondary_seventh_context

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "research/configs/eh12_assurance_manifest.json"
DEFAULT_RESULTS = ROOT / "research/results"
RAW_RESULT_NAME = "eh12_assurance_raw.jsonl"
SUMMARY_NAME = "eh12_assurance_summary.json"

_EXPECTED_INTERACTIONS = {
    "modulation+modal_mixture",
    "modulation+secondary_harmony",
    "modal_mixture+secondary_harmony",
}


class AssuranceCorpusError(ValueError):
    """Raised when the corpus manifest or generated evidence is inconsistent."""


def _mapping(value: object, location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AssuranceCorpusError(f"{location} must be an object")
    return value


def _array(value: object, location: str) -> list[Any]:
    if not isinstance(value, list):
        raise AssuranceCorpusError(f"{location} must be an array")
    return value


def _text(value: object, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AssuranceCorpusError(f"{location} must be a non-empty string")
    return value


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise AssuranceCorpusError("manifest root must be an object")
    validate_manifest(manifest)
    return manifest


def validate_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("schema_version") != 1:
        raise AssuranceCorpusError("manifest schema_version must be 1")
    if manifest.get("corpus_id") != "eh12-consolidated-assurance-v1":
        raise AssuranceCorpusError("unexpected corpus_id")
    _text(manifest.get("claim_boundary"), "claim_boundary")
    common = _mapping(manifest.get("common_spec"), "common_spec")
    if common.get("workers") != 1:
        raise AssuranceCorpusError("common_spec.workers must be 1")

    fixtures = _array(manifest.get("fixtures"), "fixtures")
    fixture_ids: set[str] = set()
    seeds: set[int] = set()
    interactions: set[str] = set()
    profiles: set[str] = set()
    for index, raw in enumerate(fixtures):
        item = _mapping(raw, f"fixtures[{index}]")
        fixture_ids.add(_text(item.get("id"), f"fixtures[{index}].id"))
        seed = item.get("seed")
        if type(seed) is not int:
            raise AssuranceCorpusError(f"fixtures[{index}].seed must be an integer")
        seeds.add(seed)
        interactions.add(
            _text(item.get("interaction"), f"fixtures[{index}].interaction")
        )
        _mapping(item.get("spec_overrides"), f"fixtures[{index}].spec_overrides")
        _text(item.get("fault"), f"fixtures[{index}].fault")
        _text(item.get("expected_rule"), f"fixtures[{index}].expected_rule")
        _text(item.get("adjudication_note"), f"fixtures[{index}].adjudication_note")
        profiles.update(
            _text(profile, f"fixtures[{index}].delivery_profiles")
            for profile in _array(
                item.get("delivery_profiles"),
                f"fixtures[{index}].delivery_profiles",
            )
        )
    if len(fixtures) != 3 or len(fixture_ids) != 3 or len(seeds) != 3:
        raise AssuranceCorpusError("exactly three fixtures with unique IDs and seeds are required")
    if interactions != _EXPECTED_INTERACTIONS:
        raise AssuranceCorpusError("fixtures must cover all three pairwise interactions")
    if profiles != {"certified-satb", "melody-plus-satb"}:
        raise AssuranceCorpusError("both certified delivery profiles must be covered")

    required_families = {
        _text(value, "required_schema_families")
        for value in _array(
            manifest.get("required_schema_families"), "required_schema_families"
        )
    }
    cases = _array(manifest.get("schema_cases"), "schema_cases")
    case_ids: set[str] = set()
    covered_families: set[str] = set()
    legacy_mutations: set[str] = set()
    for index, raw in enumerate(cases):
        item = _mapping(raw, f"schema_cases[{index}]")
        case_ids.add(_text(item.get("id"), f"schema_cases[{index}].id"))
        fixture_id = _text(item.get("fixture_id"), f"schema_cases[{index}].fixture_id")
        if fixture_id not in fixture_ids:
            raise AssuranceCorpusError(f"schema case references unknown fixture {fixture_id!r}")
        family = _text(item.get("family"), f"schema_cases[{index}].family")
        covered_families.add(family)
        mutation = _text(item.get("mutation"), f"schema_cases[{index}].mutation")
        if family == "legacy_schema":
            legacy_mutations.add(mutation.removeprefix("legacy_").replace("_", "."))
        if item.get("expected_outcome") != "BLOCKED":
            raise AssuranceCorpusError("schema cases must fail closed as BLOCKED")
        _text(item.get("cluster_id"), f"schema_cases[{index}].cluster_id")
    if len(case_ids) != len(cases):
        raise AssuranceCorpusError("schema case IDs must be unique")
    if covered_families != required_families:
        raise AssuranceCorpusError("schema cases must cover every required family")
    legacy_versions = set(SUPPORTED_SCHEMA_VERSIONS) - {CURRENT_SCHEMA_VERSION}
    if legacy_mutations != legacy_versions:
        raise AssuranceCorpusError("every supported legacy schema must have a strict case")


def _spec(manifest: dict[str, Any], fixture: dict[str, Any]) -> GenerationSpec:
    values = dict(_mapping(manifest["common_spec"], "common_spec"))
    values.update(_mapping(fixture["spec_overrides"], "spec_overrides"))
    values["seed"] = fixture["seed"]
    return GenerationSpec(**values)


def _secondary_beats(result: SatbGenerationResult) -> tuple[int, ...]:
    return tuple(
        beat
        for beat in range(result.spec.total_beats - 1)
        if reconstruct_secondary_leading_tone_seventh(result, beat) is not None
    )


def _modal_beats(result: SatbGenerationResult) -> tuple[int, ...]:
    return tuple(
        beat for beat, source in enumerate(result.modal_sources) if source is not None
    )


def _oracle_key(key: Key) -> OracleKey:
    return OracleKey(key.tonic_pc, TonalMode(key.mode.value))


def _interaction_fault(
    fixture: dict[str, Any],
    control: SatbGenerationResult,
) -> tuple[SatbGenerationResult, bool, tuple[str, ...] | str, dict[str, object]]:
    fault_name = str(fixture["fault"])
    secondary_beats = _secondary_beats(control)
    modal_beats = _modal_beats(control)
    boundary = control.spec.modulation_boundary_beat

    if fault_name == "stale_key_contexts":
        if not isinstance(control, ModulatedSatbGenerationResult):
            raise AssuranceCorpusError("stale-key fixture is not a modulated result")
        if boundary is None or boundary in modal_beats:
            raise AssuranceCorpusError("modulation and modal-mixture witness beats must differ")
        fault = replace(
            control,
            key_contexts=(control.spec.tonal_key,) * control.spec.total_beats,
        )
        destination = control.spec.modulation_destination
        if destination is None:
            raise AssuranceCorpusError("modulation destination is missing")
        decision = adjudicate_modulation_plan(
            source=_oracle_key(control.spec.tonal_key),
            destination=_oracle_key(destination),
            boundary=boundary,
            total_beats=control.spec.total_beats,
            serialized_contexts=tuple(_oracle_key(key) for key in fault.key_contexts),
        )
        return fault, decision.valid, decision.reason, {
            "modulation_boundary": boundary,
            "modal_beats": modal_beats,
        }

    if not secondary_beats:
        raise AssuranceCorpusError(f"fixture {fixture['id']!r} lacks secondary harmony")
    beat = secondary_beats[0]
    if fault_name == "remove_secondary_target":
        if boundary is None or beat == boundary:
            raise AssuranceCorpusError("modulation and secondary-harmony beats must differ")
        targets = list(control.tonicization_targets)
        targets[beat] = None
        fault = replace(control, tonicization_targets=tuple(targets))
        decision = adjudicate_secondary_seventh_context(
            beat=beat,
            total_beats=control.spec.total_beats,
            target_supported=False,
            modal_overlap=False,
            require_authentic_cadence=control.spec.require_authentic_cadence,
            modulation_boundary_beat=boundary,
        )
        return fault, decision.valid, decision.reasons, {
            "modulation_boundary": boundary,
            "secondary_beats": secondary_beats,
        }
    if fault_name == "overlap_modal_secondary":
        if set(modal_beats) & set(secondary_beats):
            raise AssuranceCorpusError("control has overlapping modal and secondary beats")
        sources = list(control.modal_sources)
        sources[beat] = canonical_modal_source(control.spec.active_key_at_beat(beat))
        fault = replace(control, modal_sources=tuple(sources))
        decision = adjudicate_secondary_seventh_context(
            beat=beat,
            total_beats=control.spec.total_beats,
            target_supported=True,
            modal_overlap=True,
            require_authentic_cadence=control.spec.require_authentic_cadence,
            modulation_boundary_beat=boundary,
        )
        return fault, decision.valid, decision.reasons, {
            "modal_beats": modal_beats,
            "secondary_beats": secondary_beats,
        }
    raise AssuranceCorpusError(f"unknown interaction fault {fault_name!r}")


def _mutated_payload(payload: dict[str, Any], mutation: str) -> dict[str, Any]:
    changed = deepcopy(payload)
    spec = changed["spec"]
    solver = changed["solver"]
    validation = changed["validation"]
    music = changed["music"]
    if mutation == "schema_version_type":
        changed["schema_version"] = 213
    elif mutation == "root_spec_shape":
        changed["spec"] = None
    elif mutation == "spec_missing_bars":
        spec.pop("bars")
    elif mutation == "spec_bars_string":
        spec["bars"] = "2"
    elif mutation == "spec_boolean_null":
        spec["require_authentic_cadence"] = None
    elif mutation == "spec_time_string":
        spec["max_time_seconds"] = "30"
    elif mutation == "spec_tension_null":
        spec["tension_curve"] = [None, *spec["tension_curve"][1:]]
    elif mutation == "solver_objective_null":
        solver["objective"] = None
    elif mutation == "solver_status_null":
        solver["status"] = None
    elif mutation == "validation_valid_null":
        validation["valid"] = None
    elif mutation == "validation_issues_shape":
        validation["issues"] = None
    elif mutation == "music_bass_shape":
        music["bass_midi"] = None
    elif mutation == "music_bass_item_null":
        music["bass_midi"][0] = None
    elif mutation == "music_bass_short":
        music["bass_midi"].pop()
    elif mutation == "music_rhythm_shape":
        music["rhythm"] = None
    elif mutation == "music_rhythm_item_null":
        music["rhythm"][0] = None
    elif mutation == "music_rhythm_short":
        music["rhythm"].pop()
    elif mutation == "music_target_string":
        music["tonicization_targets"][0] = "none"
    elif mutation == "music_target_short":
        music["tonicization_targets"].pop()
    elif mutation == "music_modal_integer":
        music["modal_sources"][0] = 1
    elif mutation == "music_modal_short":
        music["modal_sources"].pop()
    elif mutation == "music_context_item_null":
        music["key_contexts"][0] = None
    elif mutation == "music_context_short":
        music["key_contexts"].pop()
    elif mutation == "search_shape":
        changed["search"] = None
    elif mutation == "provenance_shape":
        changed["provenance"] = None
    elif mutation == "legacy_2_12":
        changed["schema_version"] = "2.12"
    else:
        raise AssuranceCorpusError(f"unknown schema mutation {mutation!r}")
    return changed


def _schema_observation(
    payload: dict[str, Any], spec: GenerationSpec
) -> tuple[str, list[str]]:
    try:
        report = verify_artifact(payload, expected_spec=spec)
    except ArtifactShapeError as exc:
        return "BLOCKED", list(exc.issues)
    except Exception as exc:  # pragma: no cover - raw evidence preserves crashes
        return "CRASH", [f"{type(exc).__name__}: {exc}"]
    issues = [*report.semantic.issues, *report.integrity_issues]
    return ("ACCEPT" if report.accepted else "REJECT"), issues


def _row(
    *,
    case_id: str,
    family: str,
    cluster_id: str,
    expected_outcome: str,
    outcome: str,
    fixture_id: str | None,
    issues: list[str] | tuple[str, ...] = (),
    details: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "case_id": case_id,
        "family": family,
        "cluster_id": cluster_id,
        "fixture_id": fixture_id,
        "expected_outcome": expected_outcome,
        "outcome": outcome,
        "adjudicated": outcome == expected_outcome,
        "excluded": False,
        "crashed": outcome == "CRASH",
        "issues": list(issues),
        "details": details or {},
    }


def _canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest()


def _source_hash(path: str) -> str:
    return sha256((ROOT / path).read_bytes()).hexdigest()


@cache
def generate() -> tuple[dict[str, Any], list[dict[str, object]], dict[str, object]]:
    manifest = load_manifest()
    fixtures = [
        _mapping(item, "fixture") for item in _array(manifest["fixtures"], "fixtures")
    ]
    generated: dict[str, tuple[GenerationSpec, SatbGenerationResult, dict[str, Any]]] = {}
    rows: list[dict[str, object]] = []

    for fixture in fixtures:
        fixture_id = str(fixture["id"])
        spec = _spec(manifest, fixture)
        result = ConstraintMusicSolver().generate(spec)
        if not isinstance(result, SatbGenerationResult):
            raise AssuranceCorpusError(f"fixture {fixture_id!r} is not SATB")
        report = verify_result(result)
        if not report.valid:
            raise AssuranceCorpusError(f"fixture {fixture_id!r} is invalid: {report.issues}")
        payload = artifact_payload(result)
        generated[fixture_id] = (spec, result, payload)
        rows.append(
            _row(
                case_id=f"control.{fixture_id}",
                family="fixture-control",
                cluster_id=f"fixture-{fixture_id}",
                fixture_id=fixture_id,
                expected_outcome="ACCEPT",
                outcome="ACCEPT",
                details={
                    "seed": spec.seed,
                    "request_sha256": request_digest(spec),
                    "composition_sha256": payload["provenance"]["composition_sha256"],
                    "interaction": fixture["interaction"],
                    "modulation_boundary": spec.modulation_boundary_beat,
                    "modal_beats": _modal_beats(result),
                    "secondary_beats": _secondary_beats(result),
                    "adjudication_note": fixture["adjudication_note"],
                },
            )
        )

        fault, oracle_valid, oracle_reasons, witness = _interaction_fault(fixture, result)
        fault_report = verify_result(fault)
        expected_rule = str(fixture["expected_rule"])
        outcome = (
            "REJECT"
            if not oracle_valid
            and not fault_report.valid
            and expected_rule in fault_report.failed_rules
            else "ESCAPE"
        )
        rows.append(
            _row(
                case_id=f"interaction.{fixture_id}.fault",
                family="interaction-fault",
                cluster_id=f"fixture-{fixture_id}",
                fixture_id=fixture_id,
                expected_outcome="REJECT",
                outcome=outcome,
                issues=fault_report.issues,
                details={
                    "fault": fixture["fault"],
                    "expected_rule": expected_rule,
                    "failed_rules": fault_report.failed_rules,
                    "oracle_valid": oracle_valid,
                    "oracle_reasons": oracle_reasons,
                    "witness": witness,
                    "oracle_source": "realized semantics, not serialized labels",
                },
            )
        )

    for raw_case in _array(manifest["schema_cases"], "schema_cases"):
        case = _mapping(raw_case, "schema_case")
        fixture_id = str(case["fixture_id"])
        spec, _result, payload = generated[fixture_id]
        outcome, issues = _schema_observation(
            _mutated_payload(payload, str(case["mutation"])), spec
        )
        rows.append(
            _row(
                case_id=str(case["id"]),
                family="schema-adversarial",
                cluster_id=str(case["cluster_id"]),
                fixture_id=fixture_id,
                expected_outcome=str(case["expected_outcome"]),
                outcome=outcome,
                issues=issues,
                details={
                    "schema_family": case["family"],
                    "mutation": case["mutation"],
                },
            )
        )

    with TemporaryDirectory() as directory:
        for fixture in fixtures:
            fixture_id = str(fixture["id"])
            spec, result, payload = generated[fixture_id]
            for profile_name in _array(
                fixture["delivery_profiles"], "delivery_profiles"
            ):
                profile = RenderProfile(str(profile_name))
                destination = Path(directory) / f"{fixture_id}-{profile.value}.mid"
                write_midi(result, destination, profile=profile)
                report = certify_delivery(
                    payload,
                    destination,
                    expected_spec=spec,
                    render_profile=profile,
                )
                outcome = "ACCEPT" if report.accepted else "REJECT"
                issues = [*report.semantic.issues, *report.integrity_issues]
                if report.delivery is not None:
                    issues.extend(report.delivery.issues)
                rows.append(
                    _row(
                        case_id=f"delivery.{fixture_id}.{profile.value}",
                        family="delivery-control",
                        cluster_id=f"fixture-{fixture_id}",
                        fixture_id=fixture_id,
                        expected_outcome="ACCEPT",
                        outcome=outcome,
                        issues=issues,
                        details={
                            "profile": profile.value,
                            "output_sha256": output_digest(destination),
                            "parseback_event_count": (
                                len(report.delivery.observed_events)
                                if report.delivery is not None
                                else 0
                            ),
                            "rhythm_articulated": spec.rhythm_enabled,
                        },
                    )
                )

    deletion_report = expanded_compiler_constraint_deletion_report()
    for deletion in _array(deletion_report["deletions"], "deletions"):
        item = _mapping(deletion, "deletion")
        registration = _mapping(item["registered_phase"], "registered_phase")
        escaped = bool(item["escaped"])
        rows.append(
            _row(
                case_id=f"compiler-deletion.{item['constraint_name']}",
                family="compiler-deletion",
                cluster_id=f"compiler-phase-{registration['phase']}",
                fixture_id=None,
                expected_outcome="REJECT",
                outcome="ESCAPE" if escaped else "REJECT",
                issues=(
                    [str(item["boundary_diagnostic"])]
                    if item.get("boundary_diagnostic")
                    else []
                ),
                details={
                    "constraint_name": item["constraint_name"],
                    "constraint_index": item["constraint_index"],
                    "registered_phase": registration,
                    "forced_witness": item["forced_witness"],
                    "adjudicator": item["adjudicator"],
                    "oracle_valid": item.get("oracle_valid"),
                    "verifier_valid": item["verifier_valid"],
                    "failed_rules": item["failed_rules"],
                    "boundary_outcome": item["boundary_outcome"],
                },
            )
        )

    outcomes = Counter(str(row["outcome"]) for row in rows)
    families = Counter(str(row["family"]) for row in rows)
    schema_families = sorted(
        {
            str(_mapping(row["details"], "details")["schema_family"])
            for row in rows
            if row["family"] == "schema-adversarial"
        }
    )
    delivery_rows = [row for row in rows if row["family"] == "delivery-control"]
    interaction_rows = [row for row in rows if row["family"] == "interaction-fault"]
    summary = {
        "schema_version": 1,
        "corpus_id": manifest["corpus_id"],
        "claim_boundary": manifest["claim_boundary"],
        "manifest_sha256": _canonical_hash(manifest),
        "raw_results_sha256": _canonical_hash(rows),
        "overall": {
            "cases": len(rows),
            "adjudicated": sum(bool(row["adjudicated"]) for row in rows),
            "crashes": sum(bool(row["crashed"]) for row in rows),
            "exclusions": sum(bool(row["excluded"]) for row in rows),
            "outcomes": dict(sorted(outcomes.items())),
            "families": dict(sorted(families.items())),
            "clusters": len({str(row["cluster_id"]) for row in rows}),
        },
        "fixtures": [
            {
                "id": fixture["id"],
                "seed": fixture["seed"],
                "interaction": fixture["interaction"],
                "request_sha256": request_digest(generated[str(fixture["id"])][0]),
                "composition_sha256": generated[str(fixture["id"])][2]["provenance"][
                    "composition_sha256"
                ],
            }
            for fixture in fixtures
        ],
        "schema_adversarial": {
            "cases": families["schema-adversarial"],
            "families": schema_families,
            "legacy_versions": sorted(
                set(SUPPORTED_SCHEMA_VERSIONS) - {CURRENT_SCHEMA_VERSION}
            ),
        },
        "interactions": {
            "controls": families["fixture-control"],
            "faults": len(interaction_rows),
            "rejected_faults": sum(row["outcome"] == "REJECT" for row in interaction_rows),
            "families": sorted(str(fixture["interaction"]) for fixture in fixtures),
        },
        "delivery": {
            "controls": len(delivery_rows),
            "accepted": sum(row["outcome"] == "ACCEPT" for row in delivery_rows),
            "profiles": sorted(
                {
                    str(_mapping(row["details"], "details")["profile"])
                    for row in delivery_rows
                }
            ),
        },
        "compiler_deletions": {
            "cases": deletion_report["deleted_constraints"],
            "distinct_registered_phases": deletion_report[
                "distinct_registered_phases"
            ],
            "escaped_faults": deletion_report["escaped_faults"],
        },
        "implementation_hashes": {
            path: _source_hash(path)
            for path in (
                "research/configs/eh12_assurance_manifest.json",
                "research/compiler_deletions.py",
                "research/eh12_assurance_corpus.py",
                "research/oracle/modulation.py",
                "research/oracle/rhythm_phrase.py",
                "research/oracle/secondary_seventh.py",
                "src/constraint_music/artifact_validation.py",
                "src/constraint_music/certification.py",
                "src/constraint_music/compiler_structure.py",
                "src/constraint_music/compiler_tonal.py",
                "src/constraint_music/delivery.py",
                "src/constraint_music/semantic_dispatch.py",
                "src/constraint_music/verifier.py"
            )
        },
    }
    if summary["overall"]["adjudicated"] != summary["overall"]["cases"]:
        raise AssuranceCorpusError("one or more assurance cases escaped adjudication")
    return manifest, rows, summary


def write_evidence(directory: Path = DEFAULT_RESULTS) -> tuple[Path, Path]:
    _manifest, rows, summary = generate()
    directory.mkdir(parents=True, exist_ok=True)
    raw_path = directory / RAW_RESULT_NAME
    summary_path = directory / SUMMARY_NAME
    raw_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return raw_path, summary_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=DEFAULT_RESULTS)
    args = parser.parse_args()
    raw_path, summary_path = write_evidence(args.directory)
    print(json.dumps({"raw": str(raw_path), "summary": str(summary_path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
