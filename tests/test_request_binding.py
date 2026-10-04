from __future__ import annotations

from constraint_music.certification import verify_artifact
from constraint_music.models import GenerationResult
from constraint_music.modulation_runtime import result_from_dict
from constraint_music.provenance import (
    artifact_content_digest,
    artifact_payload,
    composition_digest,
    request_digest,
)


def test_valid_artifact_is_bound_to_independent_request(
    solved_piece: GenerationResult,
) -> None:
    report = verify_artifact(
        artifact_payload(solved_piece), expected_spec=solved_piece.spec
    )
    assert report.accepted, (report.semantic.issues, report.integrity_issues)


def test_empty_verified_rule_claim_rejects_even_after_rehash(
    solved_piece: GenerationResult,
) -> None:
    payload = artifact_payload(solved_piece)
    payload["provenance"]["verified_constraint_ids"] = []
    payload["provenance"]["artifact_content_sha256"] = artifact_content_digest(payload)
    report = verify_artifact(payload, expected_spec=solved_piece.spec)
    assert not report.accepted
    assert "verified_constraint_ids do not match freshly evaluated rules" in report.integrity_issues


def test_rewritten_embedded_request_rejects_against_original_request(
    solved_piece: GenerationResult,
) -> None:
    payload = artifact_payload(solved_piece)
    payload["spec"]["tempo_bpm"] += 1
    rewritten = result_from_dict(payload)
    payload["provenance"]["request_sha256"] = request_digest(rewritten.spec)
    payload["provenance"]["composition_sha256"] = composition_digest(rewritten)
    payload["provenance"]["artifact_content_sha256"] = artifact_content_digest(payload)
    report = verify_artifact(payload, expected_spec=solved_piece.spec)
    assert not report.accepted
    assert any("independently supplied request" in issue for issue in report.integrity_issues)

