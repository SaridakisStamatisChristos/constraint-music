from __future__ import annotations

from dataclasses import replace
from itertools import product

import pytest
from research.oracle.rhythm_phrase import (
    OraclePhrase,
    RhythmPolicy,
    adjudicate_motif,
    adjudicate_phrases,
    adjudicate_rhythm,
)

from constraint_music.models import GenerationResult, GenerationSpec, RhythmState
from constraint_music.phrase import PhraseSpec
from constraint_music.verifier import verify_result

_FORM_RULES = {f"CM0{number}" for number in range(17, 27)}


def _result(
    spec: GenerationSpec,
    *,
    melody: tuple[int, ...],
    rhythm: tuple[RhythmState, ...],
    bass: tuple[int, ...],
    chords: tuple[int, ...],
) -> GenerationResult:
    return GenerationResult(
        spec=spec,
        melody=melody,
        rhythm=rhythm,
        bass=bass,
        chord_degrees=chords,
        target_tension=(0,) * spec.total_beats,
        actual_tension=(0,) * spec.total_beats,
        objective_value=0.0,
        solver_status="ORACLE_FIXTURE",
        wall_time_seconds=0.0,
    )


def _names(rhythm: tuple[RhythmState, ...]) -> tuple[str, ...]:
    return tuple(state.name.lower() for state in rhythm)


def _oracle_phrases(spec: GenerationSpec) -> tuple[OraclePhrase, ...]:
    return tuple(
        OraclePhrase(
            id=phrase.id,
            start_bar=phrase.start_bar,
            bars=phrase.bars,
            role=phrase.role,
            cadence=phrase.cadence,
            relation=phrase.relation,
            source=phrase.source,
            transpose_semitones=phrase.transpose_semitones,
            relation_steps=phrase.relation_steps,
            sequence_step_semitones=phrase.sequence_step_semitones,
        )
        for phrase in spec.phrases
    )


def _adjudicate_result_phrases(result: GenerationResult):
    spec = result.spec
    return adjudicate_phrases(
        phrases=_oracle_phrases(spec),
        composition_bars=spec.bars,
        beats_per_bar=spec.beats_per_bar,
        steps_per_bar=spec.steps_per_bar,
        tonic_pitch_class=spec.tonal_key.tonic_pc,
        melody=result.melody,
        rhythm=_names(result.effective_rhythm),
        bass=result.bass,
        chord_degrees=result.chord_degrees,
    )


def _period_result() -> GenerationResult:
    spec = GenerationSpec(
        bars=2,
        beats_per_bar=2,
        subdivisions_per_beat=1,
        require_authentic_cadence=False,
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
    return _result(
        spec,
        melody=(60, 62, 67, 60),
        rhythm=(RhythmState.ONSET,) * 4,
        bass=(48, 55, 43, 48),
        chords=(0, 4, 4, 0),
    )


def test_rhythm_oracle_matches_verifier_for_every_four_step_state_sequence() -> None:
    spec = GenerationSpec(
        bars=1,
        beats_per_bar=4,
        subdivisions_per_beat=1,
        require_authentic_cadence=False,
        rhythm_enabled=True,
        min_onsets_per_bar=1,
        max_onsets_per_bar=4,
        min_rests_per_bar=0,
        max_rests_per_bar=2,
        min_ties_per_bar=0,
        max_ties_per_bar=2,
        max_consecutive_rests=2,
        max_tie_steps=2,
        require_bar_downbeat_onset=True,
    )
    policy = RhythmPolicy(
        bars=1,
        steps_per_bar=4,
        min_onsets_per_bar=1,
        max_onsets_per_bar=4,
        min_rests_per_bar=0,
        max_rests_per_bar=2,
        min_ties_per_bar=0,
        max_ties_per_bar=2,
        max_consecutive_rests=2,
        max_tie_steps=2,
        require_bar_downbeat_onset=True,
    )
    states = (RhythmState.REST, RhythmState.ONSET, RhythmState.TIE)
    for rhythm in product(states, repeat=4):
        result = _result(
            spec,
            melody=(60,) * 4,
            rhythm=rhythm,
            bass=(48,) * 4,
            chords=(0,) * 4,
        )
        oracle = adjudicate_rhythm(result.melody, _names(rhythm), policy=policy)
        production = set(verify_result(result).failed_rules) & {"CM018", "CM019"}
        assert set(oracle.failed_rules) & {"CM018", "CM019"} == production


def test_rhythm_oracle_rejects_invalid_domain_tied_pitch_and_final_tie() -> None:
    invalid = adjudicate_rhythm(
        (60, 60),
        ("onset", "hold"),
        policy=RhythmPolicy(bars=1, steps_per_bar=2),
    )
    assert invalid.failed_rules == ("CM017",)

    changed_tie = adjudicate_rhythm(
        (60, 61),
        ("onset", "tie"),
        policy=RhythmPolicy(
            bars=1,
            steps_per_bar=2,
            require_bar_downbeat_onset=False,
            require_final_onset=True,
        ),
    )
    assert set(changed_tie.failed_rules) == {"CM018", "CM021"}


def test_cadential_articulation_oracle_matches_verifier() -> None:
    spec = GenerationSpec(
        bars=1,
        beats_per_bar=3,
        subdivisions_per_beat=1,
        require_authentic_cadence=True,
    )
    result = _result(
        spec,
        melody=(60, 60, 60),
        rhythm=(RhythmState.ONSET, RhythmState.ONSET, RhythmState.TIE),
        bass=(48, 43, 48),
        chords=(0, 4, 0),
    )
    oracle = adjudicate_rhythm(
        result.melody,
        _names(result.rhythm),
        policy=RhythmPolicy(
            bars=1,
            steps_per_bar=3,
            enabled=False,
            require_bar_downbeat_onset=False,
            require_final_onset=True,
        ),
    )
    assert oracle.failed_rules == ("CM021",)
    assert "CM021" in verify_result(result).failed_rules


@pytest.mark.parametrize(
    ("relation", "interval", "melody"),
    [
        ("repeat", 0, (60, 60, 60, 60)),
        ("transpose", 12, (60, 60, 72, 72)),
    ],
)
def test_motif_oracle_matches_verifier_for_every_protected_value(
    relation: str,
    interval: int,
    melody: tuple[int, ...],
) -> None:
    spec = GenerationSpec(
        bars=2,
        beats_per_bar=2,
        subdivisions_per_beat=1,
        require_authentic_cadence=False,
        motif_relation=relation,
        motif_source_bar=0,
        motif_target_bar=1,
        motif_length_steps=2,
        motif_transpose_semitones=interval,
    )
    rhythm = (
        RhythmState.ONSET,
        RhythmState.TIE,
        RhythmState.ONSET,
        RhythmState.TIE,
    )
    baseline = _result(
        spec,
        melody=melody,
        rhythm=rhythm,
        bass=(48,) * 4,
        chords=(0,) * 4,
    )
    assert adjudicate_motif(
        baseline.melody,
        _names(rhythm),
        relation=relation,
        source_start=0,
        target_start=2,
        length=2,
        transpose_semitones=interval,
    ).valid
    assert "CM020" not in verify_result(baseline).failed_rules

    for target in (2, 3):
        mutated_melody = list(melody)
        mutated_melody[target] += 1
        pitch_mutation = replace(baseline, melody=tuple(mutated_melody))
        oracle = adjudicate_motif(
            pitch_mutation.melody,
            _names(rhythm),
            relation=relation,
            source_start=0,
            target_start=2,
            length=2,
            transpose_semitones=interval,
        )
        assert "CM020" in oracle.failed_rules
        assert "CM020" in verify_result(pitch_mutation).failed_rules

        mutated_rhythm = list(rhythm)
        mutated_rhythm[target] = RhythmState.REST
        rhythm_mutation = replace(baseline, rhythm=tuple(mutated_rhythm))
        oracle = adjudicate_motif(
            rhythm_mutation.melody,
            _names(rhythm_mutation.rhythm),
            relation=relation,
            source_start=0,
            target_start=2,
            length=2,
            transpose_semitones=interval,
        )
        assert "CM020" in oracle.failed_rules
        assert "CM020" in verify_result(rhythm_mutation).failed_rules


def test_phrase_boundary_oracle_rejects_duplicate_out_of_bounds_and_overlap() -> None:
    common = {
        "composition_bars": 4,
        "beats_per_bar": 2,
        "steps_per_bar": 2,
        "tonic_pitch_class": 0,
        "melody": (60,) * 8,
        "rhythm": ("onset",) * 8,
        "bass": (48,) * 8,
        "chord_degrees": (0,) * 8,
    }
    fixtures = (
        (OraclePhrase("A", 0, 1), OraclePhrase("A", 2, 1)),
        (OraclePhrase("A", -1, 1),),
        (OraclePhrase("A", 3, 2),),
        (OraclePhrase("A", 0, 3), OraclePhrase("B", 2, 2)),
    )
    for phrases in fixtures:
        decision = adjudicate_phrases(phrases=phrases, **common)
        assert decision.failed_rules == ("CM022",)


@pytest.mark.parametrize(
    ("relation", "melody", "phrase"),
    [
        ("repeat", (60, 62, 60, 62), OraclePhrase("B", 1, 1, relation="repeat", source="A")),
        (
            "transpose",
            (60, 62, 72, 74),
            OraclePhrase(
                "B", 1, 1, relation="transpose", source="A", transpose_semitones=12
            ),
        ),
        (
            "answer",
            (60, 62, 67, 65),
            OraclePhrase(
                "B",
                1,
                1,
                relation="answer",
                source="A",
                transpose_semitones=7,
                relation_steps=1,
            ),
        ),
        (
            "sequence",
            (60, 62, 60, 72),
            OraclePhrase(
                "B",
                1,
                1,
                relation="sequence",
                source="A",
                relation_steps=1,
                sequence_step_semitones=12,
            ),
        ),
    ],
)
def test_phrase_relation_oracle_accepts_and_rejects_every_relation(
    relation: str,
    melody: tuple[int, ...],
    phrase: OraclePhrase,
) -> None:
    common = {
        "phrases": (OraclePhrase("A", 0, 1), phrase),
        "composition_bars": 2,
        "beats_per_bar": 2,
        "steps_per_bar": 2,
        "tonic_pitch_class": 0,
        "rhythm": ("onset",) * 4,
        "bass": (48,) * 4,
        "chord_degrees": (0,) * 4,
    }
    assert adjudicate_phrases(melody=melody, **common).valid
    mutated = (*melody[:2], melody[2] + 1, *melody[3:])
    decision = adjudicate_phrases(melody=mutated, **common)
    assert decision.failed_rules == ("CM024",), relation

    changed_rhythm = ("onset", "onset", "rest", "onset")
    decision = adjudicate_phrases(melody=melody, **(common | {"rhythm": changed_rhythm}))
    assert decision.failed_rules == ("CM024",), relation


@pytest.mark.parametrize(
    ("cadence", "chords"),
    [
        ("tonic_close", (1, 0)),
        ("dominant_open", (0, 4)),
        ("dominant_to_tonic", (4, 0)),
        ("leading_tone_to_tonic", (6, 0)),
    ],
)
def test_phrase_cadence_oracle_covers_every_label(
    cadence: str,
    chords: tuple[int, int],
) -> None:
    phrase = OraclePhrase("A", 0, 1, cadence=cadence)
    common = {
        "phrases": (phrase,),
        "composition_bars": 1,
        "beats_per_bar": 2,
        "steps_per_bar": 2,
        "tonic_pitch_class": 0,
        "melody": (62, 60),
        "rhythm": ("onset", "onset"),
        "bass": (50, 48),
    }
    assert adjudicate_phrases(chord_degrees=chords, **common).valid
    mutation = (chords[0], 1) if cadence != "dominant_open" else (chords[0], 0)
    decision = adjudicate_phrases(chord_degrees=mutation, **common)
    assert decision.failed_rules == ("CM025",)


@pytest.mark.parametrize("role", ["statement", "transition"])
def test_unconstrained_phrase_roles_add_no_hidden_semantics(role: str) -> None:
    decision = adjudicate_phrases(
        phrases=(OraclePhrase("A", 0, 1, role=role),),
        composition_bars=1,
        beats_per_bar=1,
        steps_per_bar=1,
        tonic_pitch_class=0,
        melody=(61,),
        rhythm=("rest",),
        bass=(49,),
        chord_degrees=(3,),
    )
    assert decision.valid


@pytest.mark.parametrize("role", ["antecedent", "consequent", "cadential"])
def test_phrase_role_oracle_covers_every_constrained_role(role: str) -> None:
    chords = (0, 4) if role == "antecedent" else (4, 0)
    melody = (62, 60)
    common = {
        "phrases": (OraclePhrase("A", 0, 1, role=role),),
        "composition_bars": 1,
        "beats_per_bar": 2,
        "steps_per_bar": 2,
        "tonic_pitch_class": 0,
        "rhythm": ("onset", "onset"),
        "bass": (50, 48),
    }
    assert adjudicate_phrases(melody=melody, chord_degrees=chords, **common).valid
    if role == "antecedent":
        decision = adjudicate_phrases(
            melody=melody,
            chord_degrees=(1, 4),
            **common,
        )
    else:
        decision = adjudicate_phrases(
            melody=(62, 61),
            chord_degrees=chords,
            **common,
        )
    assert decision.failed_rules == ("CM023",)


def test_period_oracle_matches_verifier_and_rejects_each_structural_anchor() -> None:
    baseline = _period_result()
    assert _adjudicate_result_phrases(baseline).valid
    phrase_rules = {"CM022", "CM023", "CM024", "CM025", "CM026"}
    assert not (set(verify_result(baseline).failed_rules) & phrase_rules)

    mutations = (
        (replace(baseline, melody=(60, 62, 68, 60)), {"CM024"}),
        (
            replace(baseline, chord_degrees=(0, 4, 4, 1)),
            {"CM023", "CM025", "CM026"},
        ),
        (replace(baseline, chord_degrees=(0, 4, 0, 0)), {"CM025", "CM026"}),
        (replace(baseline, bass=(48, 55, 43, 49)), {"CM023", "CM025", "CM026"}),
        (
            replace(
                baseline,
                rhythm=(
                    RhythmState.ONSET,
                    RhythmState.ONSET,
                    RhythmState.ONSET,
                    RhythmState.REST,
                ),
            ),
            {"CM023", "CM025", "CM026"},
        ),
    )
    for mutated, expected in mutations:
        oracle = set(_adjudicate_result_phrases(mutated).failed_rules)
        production = set(verify_result(mutated).failed_rules) & _FORM_RULES
        assert oracle == expected
        assert production & {"CM022", "CM023", "CM024", "CM025", "CM026"} == expected
