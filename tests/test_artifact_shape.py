from __future__ import annotations

from dataclasses import replace

import pytest

from constraint_music.artifact_validation import ArtifactShapeError, validate_artifact_payload
from constraint_music.models import GenerationResult
from constraint_music.provenance import artifact_payload
from constraint_music.verifier import verify_result


@pytest.mark.parametrize(
    "field",
    (
        "soprano_midi",
        "alto_midi",
        "tenor_midi",
        "chord_kinds",
        "chord_inversions",
        "tonicization_targets",
        "modal_sources",
    ),
)
def test_current_artifact_rejects_missing_satb_field(
    solved_piece: GenerationResult, field: str
) -> None:
    payload = artifact_payload(solved_piece)
    payload["music"].pop(field)
    with pytest.raises(ArtifactShapeError, match=field):
        validate_artifact_payload(payload)


def test_current_artifact_rejects_boolean_pitch(solved_piece: GenerationResult) -> None:
    payload = artifact_payload(solved_piece)
    payload["music"]["alto_midi"][0] = True
    with pytest.raises(ArtifactShapeError, match="booleans/strings are forbidden"):
        validate_artifact_payload(payload)


def test_current_artifact_rejects_truncated_voice(solved_piece: GenerationResult) -> None:
    payload = artifact_payload(solved_piece)
    payload["music"]["tenor_midi"].pop()
    with pytest.raises(ArtifactShapeError, match="exactly"):
        validate_artifact_payload(payload)


def test_direct_base_result_cannot_downgrade_satb_contract(
    solved_piece: GenerationResult,
) -> None:
    base = GenerationResult(
        spec=solved_piece.spec,
        melody=solved_piece.melody,
        bass=solved_piece.bass,
        chord_degrees=solved_piece.chord_degrees,
        target_tension=solved_piece.target_tension,
        actual_tension=solved_piece.actual_tension,
        objective_value=solved_piece.objective_value,
        solver_status=solved_piece.solver_status,
        wall_time_seconds=solved_piece.wall_time_seconds,
        rhythm=solved_piece.rhythm,
        validation=replace(solved_piece.validation),
    )
    report = verify_result(base)
    assert not report.valid
    assert "CM027" in report.failed_rules

