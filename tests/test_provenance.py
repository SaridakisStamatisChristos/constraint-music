from __future__ import annotations

import json

from constraint_music.models import GenerationResult
from constraint_music.provenance import (
    load_result_json,
    verify_artifact_integrity,
    write_result_json,
)
from constraint_music.verifier import verify_result


def test_v2_artifact_round_trip(tmp_path, solved_piece: GenerationResult) -> None:
    path = write_result_json(solved_piece, tmp_path / "piece.json")
    loaded, payload = load_result_json(path)
    assert verify_result(loaded).valid
    assert verify_artifact_integrity(loaded, payload) == ()


def test_tampered_artifact_breaks_digest(tmp_path, solved_piece: GenerationResult) -> None:
    path = write_result_json(solved_piece, tmp_path / "piece.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["music"]["melody_midi"][0] += 1
    path.write_text(json.dumps(payload), encoding="utf-8")

    tampered, loaded_payload = load_result_json(path)
    issues = verify_artifact_integrity(tampered, loaded_payload)
    assert "composition digest mismatch" in issues
