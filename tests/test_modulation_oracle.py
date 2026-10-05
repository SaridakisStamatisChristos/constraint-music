from __future__ import annotations

import pytest
from research.oracle.contextual_harmony import (
    DiatonicKind,
    TonalMode,
    adjudicate_diatonic_chord,
    diatonic_pitch_classes,
)
from research.oracle.modulation import (
    OracleKey,
    active_key_contexts,
    adjudicate_common_tonic_pivot,
    adjudicate_destination_cadence,
    adjudicate_modulation_plan,
    dominant_destination,
    pivot_destination_degree,
)

from constraint_music.models import GenerationSpec
from constraint_music.modulation import (
    common_tonic_pivot_destination_degree,
    dominant_key,
)
from constraint_music.theory import PC_TO_SHARP_NAME, Key, Mode


def _oracle_key(key: Key) -> OracleKey:
    return OracleKey(key.tonic_pc, TonalMode(key.mode.value))


def _valid_terminal_voices(
    destination: OracleKey,
) -> tuple[tuple[int, int, int, int], tuple[int, int, int, int]]:
    leading = 60 + destination.pitch_classes[6]
    tonic = 48 + destination.tonic_pc
    fifth = 48 + destination.pitch_classes[4]
    penultimate = (leading, tonic, fifth, tonic - 12)
    final = (leading + 1, tonic, fifth, tonic - 12)
    return penultimate, final


@pytest.mark.parametrize("tonic_pc", range(12))
@pytest.mark.parametrize("mode", [Mode.MAJOR, Mode.MINOR])
def test_modulation_oracle_matches_every_destination_context_and_pivot_policy(
    tonic_pc: int,
    mode: Mode,
) -> None:
    source = Key(PC_TO_SHARP_NAME[tonic_pc], mode)
    production_destination = dominant_key(source)
    oracle_source = _oracle_key(source)
    oracle_destination = dominant_destination(oracle_source)
    assert oracle_destination == _oracle_key(production_destination)
    assert pivot_destination_degree(oracle_source, oracle_destination) == (
        common_tonic_pivot_destination_degree(source, production_destination)
    )

    total_beats = 8
    for boundary in range(2, total_beats - 1):
        expected = active_key_contexts(
            oracle_source,
            oracle_destination,
            boundary=boundary,
            total_beats=total_beats,
        )
        spec = GenerationSpec(
            key=source.tonic,
            mode=mode,
            bars=2,
            beats_per_bar=4,
            subdivisions_per_beat=1,
            require_authentic_cadence=False,
            modulation_enabled=True,
            modulation_destination_key=production_destination.tonic,
            modulation_boundary_beat=boundary,
        )
        assert expected == tuple(_oracle_key(key) for key in spec.expected_key_contexts)
        decision = adjudicate_modulation_plan(
            source=oracle_source,
            destination=oracle_destination,
            boundary=boundary,
            total_beats=total_beats,
            serialized_contexts=expected,
        )
        assert decision.valid, decision.reason


@pytest.mark.parametrize("tonic_pc", range(12))
@pytest.mark.parametrize("mode", [TonalMode.MAJOR, TonalMode.MINOR])
def test_modulation_oracle_accepts_every_common_tonic_pivot(
    tonic_pc: int,
    mode: TonalMode,
) -> None:
    source = OracleKey(tonic_pc, mode)
    destination = dominant_destination(source)
    tones = diatonic_pitch_classes(tonic_pc, mode, 0, DiatonicKind.TRIAD)
    decision = adjudicate_common_tonic_pivot(
        (tones[1], tones[2], tones[0], tones[0]),
        source=source,
        destination=destination,
        structural_degree=0,
        kind=DiatonicKind.TRIAD,
        tonicization_target=None,
        modal_source=None,
    )
    assert decision.valid, decision.reason


@pytest.mark.parametrize("tonic_pc", range(12))
@pytest.mark.parametrize("mode", [TonalMode.MAJOR, TonalMode.MINOR])
def test_destination_context_composes_with_every_diatonic_realization(
    tonic_pc: int,
    mode: TonalMode,
) -> None:
    destination = dominant_destination(OracleKey(tonic_pc, mode))
    for degree in range(7):
        tones = diatonic_pitch_classes(
            destination.tonic_pc,
            destination.mode,
            degree,
            DiatonicKind.TRIAD,
        )
        for inversion in range(3):
            upper = [tones[0], tones[0], tones[1], tones[2]]
            bass = tones[inversion]
            upper.remove(bass)
            voices = (*upper, bass)
            decision = adjudicate_diatonic_chord(
                voices,
                tonic_pc=destination.tonic_pc,
                active_mode=destination.mode,
                degree=degree,
                kind=DiatonicKind.TRIAD,
                inversion=inversion,
            )
            assert decision.valid, decision.reason


def test_modulation_plan_oracle_rejects_destination_boundary_and_context_forgeries() -> None:
    source = OracleKey(0, TonalMode.MAJOR)
    destination = dominant_destination(source)
    contexts = active_key_contexts(source, destination, boundary=2, total_beats=8)
    assert not adjudicate_modulation_plan(
        source=source,
        destination=OracleKey(5, TonalMode.MAJOR),
        boundary=2,
        total_beats=8,
        serialized_contexts=contexts,
    ).valid
    assert not adjudicate_modulation_plan(
        source=source,
        destination=destination,
        boundary=1,
        total_beats=8,
        serialized_contexts=contexts,
    ).valid
    assert not adjudicate_modulation_plan(
        source=source,
        destination=destination,
        boundary=2,
        total_beats=8,
        serialized_contexts=contexts[:-1],
    ).valid
    shifted = (source, source, source, *contexts[3:])
    assert not adjudicate_modulation_plan(
        source=source,
        destination=destination,
        boundary=2,
        total_beats=8,
        serialized_contexts=shifted,
    ).valid


def test_pivot_oracle_rejects_structural_context_and_pitch_forgeries() -> None:
    source = OracleKey(0, TonalMode.MAJOR)
    destination = dominant_destination(source)
    tones = diatonic_pitch_classes(0, TonalMode.MAJOR, 0, DiatonicKind.TRIAD)
    voices = (tones[1], tones[2], tones[0], tones[0])
    common = {
        "voices": voices,
        "source": source,
        "destination": destination,
        "structural_degree": 0,
        "kind": DiatonicKind.TRIAD,
        "tonicization_target": None,
        "modal_source": None,
    }
    for changes in (
        {"destination": OracleKey(5, TonalMode.MAJOR)},
        {"structural_degree": 3},
        {"kind": DiatonicKind.SEVENTH},
        {"tonicization_target": 4},
        {"modal_source": "parallel_natural_minor"},
        {"voices": (tones[2], tones[2], tones[2], tones[0])},
    ):
        decision = adjudicate_common_tonic_pivot(**(common | changes))
        assert not decision.valid


@pytest.mark.parametrize("tonic_pc", range(12))
@pytest.mark.parametrize("mode", [TonalMode.MAJOR, TonalMode.MINOR])
def test_modulation_oracle_accepts_every_destination_terminal_confirmation(
    tonic_pc: int,
    mode: TonalMode,
) -> None:
    destination = dominant_destination(OracleKey(tonic_pc, mode))
    penultimate, final = _valid_terminal_voices(destination)
    decision = adjudicate_destination_cadence(
        penultimate,
        final,
        destination=destination,
        chord_degrees=(4, 0),
        key_contexts=(destination, destination),
        tonicization_targets=(None, None),
        modal_sources=(None, None),
        final_is_onset=True,
    )
    assert decision.valid, decision.reason


def test_destination_cadence_oracle_rejects_every_protected_anchor_forgery() -> None:
    destination = dominant_destination(OracleKey(0, TonalMode.MAJOR))
    stale = OracleKey(0, TonalMode.MAJOR)
    penultimate, final = _valid_terminal_voices(destination)
    common = {
        "penultimate_voices": penultimate,
        "final_voices": final,
        "destination": destination,
        "chord_degrees": (4, 0),
        "key_contexts": (destination, destination),
        "tonicization_targets": (None, None),
        "modal_sources": (None, None),
        "final_is_onset": True,
    }
    no_leading = (destination.tonic_pc,) * 4
    leading = 60 + destination.pitch_classes[6]
    tonic = 60 + destination.tonic_pc
    unresolved_penultimate = (tonic, leading, penultimate[2], penultimate[3])
    unresolved_final = (tonic, leading, final[2], final[3])
    for changes in (
        {"chord_degrees": (3, 0)},
        {"key_contexts": (stale, destination)},
        {"tonicization_targets": (4, None)},
        {"modal_sources": ("parallel_natural_minor", None)},
        {"final_is_onset": False},
        {"final_voices": (final[0] + 2, final[1], final[2], final[3])},
        {"final_voices": (final[0], final[1], final[2], final[3] + 2)},
        {"penultimate_voices": no_leading},
        {
            "penultimate_voices": unresolved_penultimate,
            "final_voices": unresolved_final,
        },
    ):
        decision = adjudicate_destination_cadence(**(common | changes))
        assert not decision.valid
