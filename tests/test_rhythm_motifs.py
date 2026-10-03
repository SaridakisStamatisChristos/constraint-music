from __future__ import annotations

from dataclasses import replace

from mido import MidiFile

from constraint_music.midi import write_midi
from constraint_music.models import GenerationResult, GenerationSpec, RhythmState
from constraint_music.solver import ConstraintMusicSolver
from constraint_music.verifier import verify_result


def rhythm_spec(**overrides: object) -> GenerationSpec:
    payload: dict[str, object] = {
        "bars": 2,
        "beats_per_bar": 4,
        "subdivisions_per_beat": 2,
        "require_authentic_cadence": False,
        "rhythm_enabled": True,
        "min_onsets_per_bar": 5,
        "max_onsets_per_bar": 6,
        "min_rests_per_bar": 1,
        "max_rests_per_bar": 2,
        "min_ties_per_bar": 1,
        "max_ties_per_bar": 1,
        "max_consecutive_rests": 1,
        "max_tie_steps": 1,
        "max_time_seconds": 10,
        "workers": 1,
        "seed": 221,
        "tension_curve": (0.05, 0.7, 0.05),
    }
    payload.update(overrides)
    return GenerationSpec(**payload)


def test_rhythm_csp_generates_verified_onsets_ties_and_rests() -> None:
    result = ConstraintMusicSolver().generate(rhythm_spec())
    assert result.validation.valid, result.validation.issues
    for bar in range(result.spec.bars):
        start = bar * result.spec.steps_per_bar
        states = result.rhythm[start : start + result.spec.steps_per_bar]
        assert states.count(RhythmState.REST) >= 1
        assert states.count(RhythmState.TIE) == 1
        assert states[0] == RhythmState.ONSET


def test_transposed_motif_is_exactly_enforced() -> None:
    spec = GenerationSpec(
        bars=2,
        beats_per_bar=4,
        subdivisions_per_beat=1,
        require_authentic_cadence=False,
        motif_relation="transpose",
        motif_source_bar=0,
        motif_target_bar=1,
        motif_length_steps=2,
        motif_transpose_semitones=12,
        melody_low=60,
        melody_high=84,
        max_time_seconds=10,
        workers=1,
        seed=445,
    )
    result = ConstraintMusicSolver().generate(spec)
    assert result.validation.valid, result.validation.issues
    for offset in range(spec.motif_length_steps):
        assert result.melody[spec.motif_target_start + offset] == (
            result.melody[spec.motif_source_start + offset] + 12
        )


def test_verifier_detects_broken_rhythm_density() -> None:
    result = ConstraintMusicSolver().generate(rhythm_spec())
    rhythm = list(result.rhythm)
    rhythm[: result.spec.steps_per_bar] = [RhythmState.ONSET] * result.spec.steps_per_bar
    report = verify_result(replace(result, rhythm=tuple(rhythm)))
    assert "CM019" in report.failed_rules


def test_verifier_detects_broken_motif_relation() -> None:
    spec = GenerationSpec(
        bars=2,
        beats_per_bar=4,
        subdivisions_per_beat=1,
        require_authentic_cadence=False,
        motif_relation="repeat",
        motif_source_bar=0,
        motif_target_bar=1,
        motif_length_steps=2,
        max_time_seconds=10,
        workers=1,
        seed=446,
    )
    result = ConstraintMusicSolver().generate(spec)
    melody = list(result.melody)
    melody[spec.motif_target_start] += 1
    report = verify_result(replace(result, melody=tuple(melody)))
    assert "CM020" in report.failed_rules


def test_midi_renderer_turns_ties_into_sustained_notes(tmp_path) -> None:
    spec = GenerationSpec(
        bars=1,
        beats_per_bar=2,
        subdivisions_per_beat=2,
        require_authentic_cadence=False,
    )
    result = GenerationResult(
        spec=spec,
        melody=(60, 60, 62, 64),
        rhythm=(RhythmState.ONSET, RhythmState.TIE, RhythmState.REST, RhythmState.ONSET),
        bass=(48, 50),
        chord_degrees=(0, 1),
        target_tension=(0, 0),
        actual_tension=(0, 0),
        objective_value=0.0,
        solver_status="TEST",
        wall_time_seconds=0.0,
    )
    path = write_midi(result, tmp_path / "rhythm.mid")
    midi = MidiFile(path)
    melody_track = next(track for track in midi.tracks if track.name == "Melody")
    note_ons = [msg for msg in melody_track if msg.type == "note_on" and msg.velocity > 0]
    note_offs = [msg for msg in melody_track if msg.type == "note_off"]
    assert len(note_ons) == 2
    assert len(note_offs) == 2
