from __future__ import annotations

import json
from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path
from typing import Any

from .contract import CONTRACT_VERSION, contract_digest
from .models import GenerationResult
from .modulation_runtime import result_from_dict
from .objective import evaluate_objective_vector
from .search import objective_mapping

ARTIFACT_SCHEMA_VERSION = "2.10"


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
    content = {
        key: payload[key]
        for key in ("spec", "solver", "validation", "music", "search")
        if key in payload
    }
    return _sha256_json(content)


def artifact_payload(result: GenerationResult) -> dict[str, Any]:
    payload = result.to_dict()
    payload["schema_version"] = ARTIFACT_SCHEMA_VERSION
    payload["search"] = {
        "objective_vector": objective_mapping(evaluate_objective_vector(result)),
        "semantics": "all objective components are minimized",
    }
    payload["provenance"] = {
        "constraint_contract_version": CONTRACT_VERSION,
        "constraint_contract_sha256": contract_digest(),
        "composition_sha256": composition_digest(result),
        "artifact_content_sha256": artifact_content_digest(payload),
        "verified_constraint_ids": list(result.validation.checked_rules),
    }
    return payload


def write_result_json(result: GenerationResult, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(artifact_payload(result), indent=2) + "\n", encoding="utf-8")
    return destination


def load_result_json(path: str | Path) -> tuple[GenerationResult, Mapping[str, Any]]:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("Result JSON root must be an object")
    return result_from_dict(payload), payload


def verify_artifact_integrity(
    result: GenerationResult, payload: Mapping[str, Any]
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
    if provenance.get("composition_sha256") != composition_digest(result):
        issues.append("composition digest mismatch")
    if provenance.get("artifact_content_sha256") != artifact_content_digest(payload):
        issues.append("artifact content digest mismatch")
    return tuple(issues)
