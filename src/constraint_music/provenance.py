from __future__ import annotations

import json
from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path
from typing import Any

from .contract import CONTRACT_VERSION, contract_digest
from .models import GenerationResult

ARTIFACT_SCHEMA_VERSION = "2.2"


def _sha256_json(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def composition_digest(result: GenerationResult) -> str:
    payload = result.to_dict()
    semantic = {
        "spec": payload["spec"],
        "music": {
            "melody_midi": payload["music"]["melody_midi"],
            "rhythm": payload["music"]["rhythm"],
            "bass_midi": payload["music"]["bass_midi"],
            "chord_degrees": payload["music"]["chord_degrees"],
            "target_tension": payload["music"]["target_tension"],
            "actual_tension": payload["music"]["actual_tension"],
        },
    }
    return _sha256_json(semantic)


def artifact_content_digest(payload: Mapping[str, Any]) -> str:
    content = {
        key: payload[key]
        for key in ("spec", "solver", "validation", "music")
        if key in payload
    }
    return _sha256_json(content)


def artifact_payload(result: GenerationResult) -> dict[str, Any]:
    payload = result.to_dict()
    payload["schema_version"] = ARTIFACT_SCHEMA_VERSION
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
    return GenerationResult.from_dict(payload), payload


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
    if provenance.get("constraint_contract_version") != CONTRACT_VERSION:
        issues.append("constraint contract version does not match this verifier")
    if provenance.get("constraint_contract_sha256") != contract_digest():
        issues.append("constraint contract digest does not match this verifier")
    if provenance.get("composition_sha256") != composition_digest(result):
        issues.append("composition digest mismatch")
    if provenance.get("artifact_content_sha256") != artifact_content_digest(payload):
        issues.append("artifact content digest mismatch")
    return tuple(issues)
