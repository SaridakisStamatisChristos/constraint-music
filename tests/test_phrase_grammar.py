from __future__ import annotations

import pytest

from constraint_music.models import GenerationSpec
from constraint_music.phrase import PhraseSpec
from constraint_music.solver import ConstraintMusicSolver


def period_spec(**overrides: object) -> GenerationSpec:
    payload: dict[str, object] = {
        "bars": 2,
        "beats_per_bar": 2,
        "subdivisions_per_beat": 1,
        "require_authentic_cadence": False,
        "avoid_parallel_perfects": False,
        "resolve_leading_tone": False,
        "workers": 1,
        "seed": 2202,
        "max_time_seconds": 10,
        "tension_curve": (0.05, 0.75, 0.05),
        "phrases": (
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
    }
    payload.update(overrides)
    return GenerationSpec(**payload)


def test_antecedent_consequent_period_is_compiled_and_verified() -> None:
    result = ConstraintMusicSolver().generate(period_spec())
    assert result.validation.valid, result.validation.issues
    assert result.chord_degrees[0] == 0
    assert result.chord_degrees[1] == 4
    assert result.chord_degrees[2] == 4
    assert result.chord_degrees[3] == 0
    assert result.melody[2] == result.melody[0] + 7


def test_full_phrase_transposition_is_exact() -> None:
    spec = GenerationSpec(
        bars=2,
        beats_per_bar=2,
        subdivisions_per_beat=1,
        require_authentic_cadence=False,
        avoid_parallel_perfects=False,
        resolve_leading_tone=False,
        melody_low=60,
        melody_high=84,
        workers=1,
        seed=2203,
        max_time_seconds=10,
        phrases=(
            PhraseSpec(id="source", start_bar=0, bars=1),
            PhraseSpec(
                id="target",
                start_bar=1,
                bars=1,
                relation="transpose",
                source="source",
                transpose_semitones=12,
            ),
        ),
    )
    result = ConstraintMusicSolver().generate(spec)
    assert result.validation.valid, result.validation.issues
    assert result.melody[2:] == tuple(note + 12 for note in result.melody[:2])
    assert result.rhythm[2:] == result.rhythm[:2]


def test_sequence_reconstructs_source_fragment_with_stepwise_transposition() -> None:
    spec = GenerationSpec(
        bars=2,
        beats_per_bar=2,
        subdivisions_per_beat=1,
        require_authentic_cadence=False,
        avoid_parallel_perfects=False,
        resolve_leading_tone=False,
        melody_low=60,
        melody_high=84,
        workers=1,
        seed=2204,
        max_time_seconds=10,
        phrases=(
            PhraseSpec(id="seed", start_bar=0, bars=1),
            PhraseSpec(
                id="seq",
                start_bar=1,
                bars=1,
                relation="sequence",
                source="seed",
                relation_steps=1,
                sequence_step_semitones=12,
            ),
        ),
    )
    result = ConstraintMusicSolver().generate(spec)
    assert result.validation.valid, result.validation.issues
    assert result.melody[2] == result.melody[0]
    assert result.melody[3] == result.melody[0] + 12


def test_overlapping_phrases_are_rejected() -> None:
    with pytest.raises(ValueError, match="overlap"):
        GenerationSpec(
            bars=4,
            phrases=(
                PhraseSpec(id="A", start_bar=0, bars=3),
                PhraseSpec(id="B", start_bar=2, bars=2),
            ),
        )


def test_phrase_beyond_composition_is_rejected() -> None:
    with pytest.raises(ValueError, match="extends beyond composition"):
        GenerationSpec(
            bars=4,
            phrases=(PhraseSpec(id="A", start_bar=3, bars=2),),
        )
