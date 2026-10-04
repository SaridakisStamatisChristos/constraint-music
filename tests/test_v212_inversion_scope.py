from __future__ import annotations

from dataclasses import replace

from constraint_music.models import GenerationSpec
from constraint_music.satb import SatbGenerationResult
from constraint_music.secondary_leading_tone_seventh_runtime import (
    reconstruct_secondary_leading_tone_seventh,
)
from constraint_music.solver import ConstraintMusicSolver
from constraint_music.verifier import verify_result


def test_third_inversion_is_legal_only_for_reconstructed_secondary_seventh() -> None:
    spec = GenerationSpec(
        bars=1,
        beats_per_bar=2,
        subdivisions_per_beat=1,
        require_authentic_cadence=False,
        harmony_vocabulary="triads+sevenths",
        secondary_leading_tone_seventh_enabled=True,
        minimum_secondary_leading_tone_seventh_chords=1,
        avoid_parallel_perfects=False,
        workers=1,
        seed=4121,
        max_time_seconds=30,
        tension_curve=(0.8, 0.1),
    )
    result = ConstraintMusicSolver().generate(spec)
    assert isinstance(result, SatbGenerationResult)

    secondary_beats = {
        beat
        for beat in range(spec.total_beats)
        if reconstruct_secondary_leading_tone_seventh(result, beat) is not None
    }
    ordinary_beat = next(
        beat for beat in range(spec.total_beats) if beat not in secondary_beats
    )
    inversions = list(result.chord_inversions)
    inversions[ordinary_beat] = 3

    report = verify_result(replace(result, chord_inversions=tuple(inversions)))
    assert not report.valid
    assert "CM033" in report.failed_rules
