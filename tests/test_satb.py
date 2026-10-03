from __future__ import annotations

from dataclasses import replace

from constraint_music.contract import HARD_CONSTRAINT_IDS
from constraint_music.models import GenerationSpec
from constraint_music.satb import (
    ALTO_HIGH,
    ALTO_LOW,
    TENOR_HIGH,
    TENOR_LOW,
    SatbGenerationResult,
)
from constraint_music.solver import ConstraintMusicSolver
from constraint_music.verifier import verify_result


def satb_spec(**overrides: object) -> GenerationSpec:
    payload: dict[str, object] = {
        "bars": 2,
        "beats_per_bar": 4,
        "subdivisions_per_beat": 1,
        "max_time_seconds": 15,
        "workers": 1,
        "seed": 321,
        "tension_curve": (0.05, 0.75, 0.02),
    }
    payload.update(overrides)
    return GenerationSpec(**payload)


def test_solver_emits_independently_verified_satb() -> None:
    result = ConstraintMusicSolver().generate(satb_spec())
    assert isinstance(result, SatbGenerationResult)
    assert result.validation.valid, result.validation.issues
    assert result.validation.checked_rules == HARD_CONSTRAINT_IDS
    assert len(result.soprano) == result.spec.total_beats
    assert len(result.alto) == result.spec.total_beats
    assert len(result.tenor) == result.spec.total_beats

    key = result.spec.tonal_key
    voices = zip(
        result.soprano,
        result.alto,
        result.tenor,
        result.bass,
        result.chord_degrees,
        strict=True,
    )
    for beat, (soprano, alto, tenor, bass, chord) in enumerate(voices):
        assert soprano == result.melody[beat * result.spec.subdivisions_per_beat]
        assert ALTO_LOW <= alto <= ALTO_HIGH
        assert TENOR_LOW <= tenor <= TENOR_HIGH
        assert bass < tenor < alto < soprano
        assert soprano - alto <= 12
        assert alto - tenor <= 12
        triad = key.triad_pitch_classes(chord)
        pcs = (soprano % 12, alto % 12, tenor % 12, bass % 12)
        assert set(pcs) == set(triad)
        assert pcs.count(triad[0]) == 2


def test_verifier_rejects_satb_voice_crossing() -> None:
    result = ConstraintMusicSolver().generate(satb_spec())
    assert isinstance(result, SatbGenerationResult)
    tampered_alto = list(result.alto)
    tampered_alto[0] = result.soprano[0]
    report = verify_result(replace(result, alto=tuple(tampered_alto)))
    assert not report.valid
    assert "CM028" in report.failed_rules


def test_verifier_rejects_incomplete_satb_chord() -> None:
    result = ConstraintMusicSolver().generate(satb_spec())
    assert isinstance(result, SatbGenerationResult)
    tampered_tenor = list(result.tenor)
    tampered_tenor[0] += 1
    report = verify_result(replace(result, tenor=tuple(tampered_tenor)))
    assert not report.valid
    assert "CM030" in report.failed_rules


def test_voicing_distinctness_includes_inner_voices() -> None:
    first, second = ConstraintMusicSolver().generate_many(
        satb_spec(require_authentic_cadence=False), 2, distinct_on=("voicing",)
    )
    assert isinstance(first, SatbGenerationResult)
    assert isinstance(second, SatbGenerationResult)
    assert (first.alto, first.tenor) != (second.alto, second.tenor)
