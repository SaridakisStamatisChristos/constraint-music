from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, replace
from hashlib import sha256
from pathlib import Path
from typing import Any

from .artifact_validation import CURRENT_SCHEMA_VERSION, validate_artifact_payload
from .contract import CONTRACT_VERSION, RuleStatus, contract_digest
from .models import GenerationResult, GenerationSpec
from .modulation_runtime import result_from_dict
from .objective import evaluate_objective_vector
from .search import objective_mapping
from .verifier import verify_result

ARTIFACT_SCHEMA_VERSION = CURRENT_SCHEMA_VERSION
CANONICALIZATION_VERSION = "1"


def _sha256_json(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def composition_digest(result: GenerationResult) -> str:
    payload = result.to_dict()
    music = payload["music"]
    semantic_music = {
        "melody_midi": music["melody_midi"],
        "rhythm": music["rhythm"],
        "bass_midi": music["bass_midi"],
        "chord_degrees": music["chord_degrees"],
        "target_tension": music["target_tension"],
        "actual_tension": music["actual_tension"],
    }
    for key in (
        "soprano_midi",
        "alto_midi",
        "tenor_midi",
        "chord_kinds",
        "chord_inversions",
        "tonicization_targets",
        "modal_sources",
        "key_contexts",
    ):
        if key in music:
            semantic_music[key] = music[key]
    semantic = {"spec": payload["spec"], "music": semantic_music}
    return _sha256_json(semantic)


def artifact_content_digest(payload: Mapping[str, Any]) -> str:
    content = dict(payload)
    provenance = content.get("provenance")
    if isinstance(provenance, Mapping):
        content["provenance"] = {
            key: value
            for key, value in provenance.items()
            if key != "artifact_content_sha256"
        }
    return _sha256_json(content)


def canonical_spec_payload(spec: GenerationSpec) -> dict[str, Any]:
    payload = asdict(spec)
    payload["mode"] = spec.mode.value
    payload["progression_graph"] = {
        str(degree): list(targets) for degree, targets in enumerate(spec.progression_graph)
    }
    return payload


def request_digest(spec: GenerationSpec) -> str:
    return _sha256_json(
        {
            "canonicalization_version": CANONICALIZATION_VERSION,
            "request": canonical_spec_payload(spec),
        }
    )


def artifact_payload(result: GenerationResult) -> dict[str, Any]:
    fresh_report = verify_result(result)
    checked_result = replace(result, validation=fresh_report)
    payload = checked_result.to_dict()
    payload["schema_version"] = ARTIFACT_SCHEMA_VERSION
    payload["search"] = {
        "objective_vector": objective_mapping(evaluate_objective_vector(result)),
        "semantics": "all objective components are minimized",
    }
    payload["provenance"] = {
        "canonicalization_version": CANONICALIZATION_VERSION,
        "constraint_contract_version": CONTRACT_VERSION,
        "constraint_contract_sha256": contract_digest(),
        "request_sha256": request_digest(result.spec),
        "composition_sha256": composition_digest(checked_result),
        "verified_constraint_ids": [
            outcome.rule_id
            for outcome in fresh_report.rule_outcomes
            if outcome.status in {RuleStatus.PASS, RuleStatus.FAIL}
        ],
    }
    payload["provenance"]["artifact_content_sha256"] = artifact_content_digest(payload)
    return payload


def write_result_json(result: GenerationResult, path: str | Path) -> Path:
    report = verify_result(result)
    if not report.valid:
        raise ValueError(
            "refusing to write a certifying artifact for an invalid result: "
            + "; ".join(report.issues)
        )
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(artifact_payload(result), indent=2) + "\n", encoding="utf-8")
    return destination


def load_result_json(
    path: str | Path, *, require_current: bool = True
) -> tuple[GenerationResult, Mapping[str, Any]]:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("Result JSON root must be an object")
    validate_artifact_payload(payload, require_current=require_current)
    return result_from_dict(payload), payload


def verify_artifact_integrity(
    result: GenerationResult,
    payload: Mapping[str, Any],
    *,
    expected_spec: GenerationSpec | None = None,
) -> tuple[str, ...]:
    issues: list[str] = []
    if payload.get("schema_version") != ARTIFACT_SCHEMA_VERSION:
        issues.append(
            f"schema_version mismatch: expected {ARTIFACT_SCHEMA_VERSION!r}, "
            f"got {payload.get('schema_version')!r}"
        )
    provenance = payload.get("provenance")
    if not isinstance(provenance, Mapping):
        return (*issues, "missing provenance object")
    search = payload.get("search")
    if not isinstance(search, Mapping):
        issues.append("missing search metadata")
    else:
        try:
            expected_vector = objective_mapping(evaluate_objective_vector(result))
        except (IndexError, ValueError):
            issues.append("objective vector cannot be recomputed from invalid musical values")
        else:
            if search.get("objective_vector") != expected_vector:
                issues.append("objective vector metadata mismatch")
    if provenance.get("constraint_contract_version") != CONTRACT_VERSION:
        issues.append("constraint contract version does not match this verifier")
    if provenance.get("constraint_contract_sha256") != contract_digest():
        issues.append("constraint contract digest does not match this verifier")
    if provenance.get("canonicalization_version") != CANONICALIZATION_VERSION:
        issues.append("request canonicalization version does not match this verifier")
    if provenance.get("request_sha256") != request_digest(result.spec):
        issues.append("embedded request digest mismatch")
    if expected_spec is not None:
        if canonical_spec_payload(result.spec) != canonical_spec_payload(expected_spec):
            issues.append("embedded request does not match the independently supplied request")
        if provenance.get("request_sha256") != request_digest(expected_spec):
            issues.append("request digest does not bind the independently supplied request")
    if provenance.get("composition_sha256") != composition_digest(result):
        issues.append("composition digest mismatch")
    if provenance.get("artifact_content_sha256") != artifact_content_digest(payload):
        issues.append("artifact content digest mismatch")
    fresh = verify_result(result)
    expected_validation = replace(result, validation=fresh).to_dict()["validation"]
    if payload.get("validation") != expected_validation:
        issues.append("serialized validation report does not match fresh verification")
    expected_ids = list(fresh.evaluated_rule_ids)
    claimed_ids = provenance.get("verified_constraint_ids")
    if not isinstance(claimed_ids, list) or not all(
        isinstance(item, str) for item in claimed_ids
    ):
        issues.append("verified_constraint_ids must be a string array")
    elif claimed_ids != expected_ids:
        issues.append("verified_constraint_ids do not match freshly evaluated rules")
    issues.extend(_display_claim_issues(result, payload))
    return tuple(issues)


def _display_claim_issues(
    result: GenerationResult, payload: Mapping[str, Any]
) -> tuple[str, ...]:
    music = payload.get("music")
    if not isinstance(music, Mapping):
        return ("music display claims cannot be checked",)
    expected = result.to_dict()["music"]
    issues: list[str] = []
    for key in (
        "melody_names",
        "bass_names",
        "soprano_names",
        "alto_names",
        "tenor_names",
        "chord_names",
        "chord_form_names",
    ):
        if key in music and music.get(key) != expected.get(key):
            issues.append(f"display claim {key} does not match realized musical data")
    return tuple(issues)
