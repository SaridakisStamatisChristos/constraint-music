from __future__ import annotations

from dataclasses import replace

import pytest

from constraint_music.models import GenerationResult, GenerationSpec, RhythmState
from constraint_music.solver import ConstraintMusicSolver
from constraint_music.verifier import verify_result


def test_v20_style_spec_remains_all_onset() -> None:
    spec = GenerationSpec(
        bars=1,
        beats_per_bar=2,
        subdivisions_per_beat=1,
        require_authentic_cadence=False,
        workers=1,
        seed=2100,
        max_time_seconds=10,
    )
    result = ConstraintMusicSolver().generate(spec)
    assert result.validation.valid, result.validation.issues
    assert result.rhythm == (RhythmState.ONSET,) * spec.total_steps


def test_result_deserialization_rejects_malformed_rhythm_value() -> None:
    spec = GenerationSpec(
        bars=1,
        beats_per_bar=2,
        subdivisions_per_beat=1,
        require_authentic_cadence=False,
    )
    result = ConstraintMusicSolver().generate(replace(spec, workers=1, max_time_seconds=10))
    payload = result.to_dict()
    payload["music"]["rhythm"][0] = "invalid-rhythm-state"
    with pytest.raises(ValueError, match="Unknown rhythm state"):
        GenerationResult.from_dict(payload)


def test_single_worker_generation_is_fully_deterministic_including_rhythm() -> None:
    spec = GenerationSpec(
        bars=2,
        beats_per_bar=2,
        subdivisions_per_beat=2,
        require_authentic_cadence=False,
        rhythm_enabled=True,
        min_onsets_per_bar=2,
        max_onsets_per_bar=3,
        min_rests_per_bar=1,
        max_rests_per_bar=1,
        min_ties_per_bar=0,
        max_ties_per_bar=1,
        max_consecutive_rests=1,
        max_tie_steps=1,
        workers=1,
        seed=2101,
        max_time_seconds=10,
    )
    solver = ConstraintMusicSolver()
    first = solver.generate(spec)
    second = solver.generate(spec)
    assert first.melody == second.melody
    assert first.bass == second.bass
    assert first.chord_degrees == second.chord_degrees
    assert first.rhythm == second.rhythm


def test_tampered_generated_assignment_fails_closed_verification() -> None:
    spec = GenerationSpec(
        bars=1,
        beats_per_bar=2,
        subdivisions_per_beat=1,
        require_authentic_cadence=False,
        workers=1,
        seed=2102,
        max_time_seconds=10,
    )
    result = ConstraintMusicSolver().generate(spec)
    melody = list(result.melody)
    melody[0] = 1
    report = verify_result(replace(result, melody=tuple(melody)))
    assert not report.valid
    assert "CM002" in report.failed_rules
