from __future__ import annotations

from dataclasses import replace

from constraint_music.models import GenerationSpec
from constraint_music.phrase import PhraseSpec
from constraint_music.solver import ConstraintMusicSolver
from constraint_music.verifier import verify_result


def _period_result():
    spec = GenerationSpec(
        bars=2,
        beats_per_bar=2,
        subdivisions_per_beat=1,
        require_authentic_cadence=False,
        avoid_parallel_perfects=False,
        resolve_leading_tone=False,
        workers=1,
        seed=2210,
        max_time_seconds=10,
        phrases=(
            PhraseSpec(
                id="A",
                start_bar=0,
                bars=1,
                role="antecedent",
                cadence="dominant_open",
            ),
            PhraseSpec(
                id="B",
                start_bar=1,
                bars=1,
                role="consequent",
                cadence="dominant_to_tonic",
                relation="answer",
                source="A",
                transpose_semitones=7,
                relation_steps=1,
            ),
        ),
    )
    return ConstraintMusicSolver().generate(spec)


def test_verifier_detects_broken_answer_relation() -> None:
    result = _period_result()
    melody = list(result.melody)
    melody[2] += 1
    report = verify_result(replace(result, melody=tuple(melody)))
    assert "CM024" in report.failed_rules


def test_verifier_detects_broken_phrase_cadence() -> None:
    result = _period_result()
    chords = list(result.chord_degrees)
    chords[-1] = 1
    report = verify_result(replace(result, chord_degrees=tuple(chords)))
    assert "CM025" in report.failed_rules


def test_verifier_detects_broken_antecedent_consequent_strength() -> None:
    result = _period_result()
    chords = list(result.chord_degrees)
    chords[-2] = 0
    report = verify_result(replace(result, chord_degrees=tuple(chords)))
    assert "CM026" in report.failed_rules
