from __future__ import annotations

from dataclasses import replace

from constraint_music.models import GenerationResult, GenerationSpec
from constraint_music.verifier import verify_result


def test_verifier_catches_melodic_tritone(solved_piece: GenerationResult) -> None:
    melody = list(solved_piece.melody)
    left = melody[0]
    melody[1] = left + 6 if left + 6 <= solved_piece.spec.melody_high else left - 6
    report = verify_result(replace(solved_piece, melody=tuple(melody)))
    assert "CM009" in report.failed_rules


def test_verifier_catches_large_leap_without_recovery(solved_piece: GenerationResult) -> None:
    melody = list(solved_piece.melody)
    melody[:3] = [60, 69, 74]
    report = verify_result(replace(solved_piece, melody=tuple(melody)))
    assert "CM012" in report.failed_rules


def test_verifier_catches_bass_tritone(solved_piece: GenerationResult) -> None:
    bass = list(solved_piece.bass)
    left = bass[0]
    bass[1] = left + 6 if left + 6 <= solved_piece.spec.bass_high else left - 6
    report = verify_result(replace(solved_piece, bass=tuple(bass)))
    assert "CM014" in report.failed_rules


def test_verifier_catches_parallel_fifth_on_weak_to_strong_boundary() -> None:
    spec = GenerationSpec(
        bars=1,
        beats_per_bar=2,
        subdivisions_per_beat=2,
        require_authentic_cadence=False,
        max_time_seconds=2,
    )
    result = GenerationResult(
        spec=spec,
        melody=(60, 67, 69, 72),
        bass=(48, 50),
        chord_degrees=(0, 1),
        target_tension=(0, 0),
        actual_tension=(0, 0),
        objective_value=0.0,
        solver_status="TEST",
        wall_time_seconds=0.0,
    )
    report = verify_result(result)
    assert "CM015" in report.failed_rules


def test_verifier_rejects_invalid_chord_degree_without_crashing(
    solved_piece: GenerationResult,
) -> None:
    chords = list(solved_piece.chord_degrees)
    chords[0] = 9
    report = verify_result(replace(solved_piece, chord_degrees=tuple(chords)))
    assert "CM004" in report.failed_rules
