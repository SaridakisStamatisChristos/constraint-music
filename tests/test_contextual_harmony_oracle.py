from __future__ import annotations

from itertools import permutations

import pytest
from research.oracle.contextual_harmony import (
    ParallelSource,
    TonalMode,
    adjudicate_borrowed_seventh,
    adjudicate_secondary_triad,
    adjudicate_secondary_triad_resolution,
    eligible_borrowed_seventh_degrees,
)
from research.oracle.contextual_harmony import (
    borrowed_seventh_pitch_classes as oracle_borrowed_seventh,
)
from research.oracle.contextual_harmony import (
    canonical_parallel_source as oracle_parallel_source,
)
from research.oracle.contextual_harmony import (
    secondary_triad_pitch_classes as oracle_secondary_triad,
)

from constraint_music.modal_mixture import (
    borrowed_seventh_pitch_classes,
    canonical_modal_source,
    supported_borrowed_seventh_degrees,
)
from constraint_music.secondary_leading_tone import (
    secondary_leading_tone_triad_pitch_classes,
)
from constraint_music.theory import PC_TO_SHARP_NAME, Key, Mode


@pytest.mark.parametrize("tonic_pc", range(12))
@pytest.mark.parametrize("mode", [Mode.MAJOR, Mode.MINOR])
def test_borrowed_seventh_oracle_matches_all_production_key_policies(
    tonic_pc: int,
    mode: Mode,
) -> None:
    key = Key(PC_TO_SHARP_NAME[tonic_pc], mode)
    source = canonical_modal_source(key)
    oracle_mode = TonalMode(mode.value)
    oracle_source = oracle_parallel_source(oracle_mode)
    assert oracle_source.value == source.label
    assert eligible_borrowed_seventh_degrees(tonic_pc, oracle_mode) == (
        supported_borrowed_seventh_degrees(key)
    )
    for degree in range(7):
        assert oracle_borrowed_seventh(tonic_pc, oracle_source, degree) == (
            borrowed_seventh_pitch_classes(key, degree, source)
        )


@pytest.mark.parametrize("tonic_pc", range(12))
@pytest.mark.parametrize("mode", [Mode.MAJOR, Mode.MINOR])
def test_borrowed_seventh_oracle_accepts_every_eligible_inversion(
    tonic_pc: int,
    mode: Mode,
) -> None:
    oracle_mode = TonalMode(mode.value)
    source = oracle_parallel_source(oracle_mode)
    for degree in eligible_borrowed_seventh_degrees(tonic_pc, oracle_mode):
        tones = oracle_borrowed_seventh(tonic_pc, source, degree)
        for inversion in range(3):
            upper = tuple(pc for index, pc in enumerate(tones) if index != inversion)
            voices = (*upper, tones[inversion])
            decision = adjudicate_borrowed_seventh(
                voices,
                tonic_pc=tonic_pc,
                active_mode=oracle_mode,
                source=source,
                degree=degree,
                inversion=inversion,
            )
            assert decision.valid, decision.reason


def test_borrowed_seventh_oracle_rejects_false_source_degree_tone_and_inversion() -> None:
    tonic_pc = 0
    mode = TonalMode.MAJOR
    source = ParallelSource.NATURAL_MINOR
    degree = eligible_borrowed_seventh_degrees(tonic_pc, mode)[0]
    tones = oracle_borrowed_seventh(tonic_pc, source, degree)
    voices = (tones[1], tones[2], tones[3], tones[0])
    assert (
        adjudicate_borrowed_seventh(
            voices,
            tonic_pc=tonic_pc,
            active_mode=mode,
            source=ParallelSource.MAJOR,
            degree=degree,
            inversion=0,
        ).valid
        is False
    )
    assert (
        adjudicate_borrowed_seventh(
            voices,
            tonic_pc=tonic_pc,
            active_mode=mode,
            source=source,
            degree=4,
            inversion=0,
        ).valid
        is False
    )
    assert (
        adjudicate_borrowed_seventh(
            (voices[0], voices[1], voices[2], voices[2]),
            tonic_pc=tonic_pc,
            active_mode=mode,
            source=source,
            degree=degree,
            inversion=0,
        ).valid
        is False
    )
    assert (
        adjudicate_borrowed_seventh(
            voices,
            tonic_pc=tonic_pc,
            active_mode=mode,
            source=source,
            degree=degree,
            inversion=3,
        ).valid
        is False
    )


@pytest.mark.parametrize("target_pc", range(12))
@pytest.mark.parametrize("inversion", range(3))
def test_secondary_triad_oracle_matches_production_and_exact_doubling(
    target_pc: int,
    inversion: int,
) -> None:
    key = Key("C", Mode.MAJOR)
    target_degree = (
        next(degree for degree, pc in enumerate(key.pitch_classes) if pc == target_pc)
        if target_pc in key.pitch_classes[1:]
        else None
    )
    expected = oracle_secondary_triad(target_pc)
    if target_degree is not None:
        assert expected == secondary_leading_tone_triad_pitch_classes(key, target_degree)
    root, third, fifth = expected
    multiset = (root, third, third, fifth)
    voices = next(values for values in permutations(multiset) if values[3] == expected[inversion])
    assert adjudicate_secondary_triad(
        voices,
        target_pitch_class=target_pc,
        inversion=inversion,
    ).valid


def test_secondary_triad_oracle_rejects_doubled_tendency_and_bad_resolution() -> None:
    target_pc = 7
    root, third, fifth = oracle_secondary_triad(target_pc)
    assert not adjudicate_secondary_triad(
        (root, root, third, fifth),
        target_pitch_class=target_pc,
        inversion=2,
    ).valid
    current = (root + 60, third + 60, third + 48, fifth + 48)
    valid_next = (current[0] + 1, current[1], current[2], current[3] - 1)
    assert adjudicate_secondary_triad_resolution(
        current,
        valid_next,
        target_pitch_class=target_pc,
    ).valid
    assert not adjudicate_secondary_triad_resolution(
        current,
        current,
        target_pitch_class=target_pc,
    ).valid
