from __future__ import annotations

from itertools import permutations

import pytest
from research.oracle.contextual_harmony import (
    DiatonicKind,
    TonalMode,
    adjudicate_applied_dominant,
    adjudicate_applied_dominant_resolution,
    adjudicate_diatonic_chord,
    adjudicate_diatonic_seventh_resolution,
    applied_dominant_pitch_classes,
    applied_dominant_support_degree,
    diatonic_pitch_classes,
    eligible_applied_dominant_targets,
)

from constraint_music.theory import PC_TO_SHARP_NAME, Key, Mode


def _realization(
    tones: tuple[int, ...],
    inversion: int,
    *,
    double_root: bool = False,
) -> tuple[int, int, int, int]:
    members = (tones[0], tones[0], tones[1], tones[2]) if double_root else tones
    return next(values for values in permutations(members) if values[3] == tones[inversion])


@pytest.mark.parametrize("tonic_pc", range(12))
@pytest.mark.parametrize("mode", [Mode.MAJOR, Mode.MINOR])
def test_diatonic_oracle_matches_every_production_degree_kind_and_inversion(
    tonic_pc: int,
    mode: Mode,
) -> None:
    key = Key(PC_TO_SHARP_NAME[tonic_pc], mode)
    oracle_mode = TonalMode(mode.value)
    for degree in range(7):
        triad = diatonic_pitch_classes(
            tonic_pc,
            oracle_mode,
            degree,
            DiatonicKind.TRIAD,
        )
        seventh = diatonic_pitch_classes(
            tonic_pc,
            oracle_mode,
            degree,
            DiatonicKind.SEVENTH,
        )
        assert triad == key.triad_pitch_classes(degree)
        assert seventh == key.seventh_pitch_classes(degree)
        for inversion in range(3):
            triad_decision = adjudicate_diatonic_chord(
                _realization(triad, inversion, double_root=True),
                tonic_pc=tonic_pc,
                active_mode=oracle_mode,
                degree=degree,
                kind=DiatonicKind.TRIAD,
                inversion=inversion,
            )
            seventh_decision = adjudicate_diatonic_chord(
                _realization(seventh, inversion),
                tonic_pc=tonic_pc,
                active_mode=oracle_mode,
                degree=degree,
                kind=DiatonicKind.SEVENTH,
                inversion=inversion,
            )
            assert triad_decision.valid, triad_decision.reason
            assert seventh_decision.valid, seventh_decision.reason


def test_diatonic_oracle_rejects_doubling_tone_and_inversion_forgeries() -> None:
    triad = diatonic_pitch_classes(0, TonalMode.MAJOR, 0, DiatonicKind.TRIAD)
    assert not adjudicate_diatonic_chord(
        (triad[0], triad[1], triad[1], triad[2]),
        tonic_pc=0,
        active_mode=TonalMode.MAJOR,
        degree=0,
        kind=DiatonicKind.TRIAD,
        inversion=2,
    ).valid

    seventh = diatonic_pitch_classes(0, TonalMode.MAJOR, 4, DiatonicKind.SEVENTH)
    valid = _realization(seventh, 0)
    assert not adjudicate_diatonic_chord(
        (valid[0], valid[1], valid[2], valid[2]),
        tonic_pc=0,
        active_mode=TonalMode.MAJOR,
        degree=4,
        kind=DiatonicKind.SEVENTH,
        inversion=0,
    ).valid
    assert not adjudicate_diatonic_chord(
        valid,
        tonic_pc=0,
        active_mode=TonalMode.MAJOR,
        degree=4,
        kind=DiatonicKind.SEVENTH,
        inversion=1,
    ).valid
    assert not adjudicate_diatonic_chord(
        valid,
        tonic_pc=0,
        active_mode=TonalMode.MAJOR,
        degree=4,
        kind=DiatonicKind.SEVENTH,
        inversion=3,
    ).valid


@pytest.mark.parametrize("tonic_pc", range(12))
@pytest.mark.parametrize("mode", [TonalMode.MAJOR, TonalMode.MINOR])
def test_diatonic_seventh_oracle_accepts_every_tendency_pattern(
    tonic_pc: int,
    mode: TonalMode,
) -> None:
    for degree in range(7):
        tones = diatonic_pitch_classes(tonic_pc, mode, degree, DiatonicKind.SEVENTH)
        current = tuple(60 + pc for pc in tones)
        following = list(current)
        following[3] -= 1
        if degree == 4:
            leading_tone = (tonic_pc - 1) % 12
            leading_index = next(
                index for index, pitch in enumerate(current) if pitch % 12 == leading_tone
            )
            following[leading_index] += 1
        decision = adjudicate_diatonic_seventh_resolution(
            current,
            tuple(following),
            tonic_pc=tonic_pc,
            active_mode=mode,
            degree=degree,
            following_degree=0 if degree == 4 else degree,
        )
        assert decision.valid, decision.reason


def test_diatonic_seventh_oracle_rejects_tendency_and_target_failures() -> None:
    tones = diatonic_pitch_classes(0, TonalMode.MAJOR, 4, DiatonicKind.SEVENTH)
    current = tuple(60 + pc for pc in tones)
    assert not adjudicate_diatonic_seventh_resolution(
        current,
        current,
        tonic_pc=0,
        active_mode=TonalMode.MAJOR,
        degree=4,
        following_degree=0,
    ).valid

    following = list(current)
    following[1] += 1
    following[3] -= 1
    assert not adjudicate_diatonic_seventh_resolution(
        current,
        tuple(following),
        tonic_pc=0,
        active_mode=TonalMode.MAJOR,
        degree=4,
        following_degree=4,
    ).valid


@pytest.mark.parametrize("tonic_pc", range(12))
@pytest.mark.parametrize("mode", [Mode.MAJOR, Mode.MINOR])
def test_applied_dominant_oracle_matches_all_production_policies(
    tonic_pc: int,
    mode: Mode,
) -> None:
    key = Key(PC_TO_SHARP_NAME[tonic_pc], mode)
    oracle_mode = TonalMode(mode.value)
    targets = eligible_applied_dominant_targets(tonic_pc, oracle_mode)
    assert targets == key.applied_dominant_targets
    for target in targets:
        tones = applied_dominant_pitch_classes(tonic_pc, oracle_mode, target)
        support = applied_dominant_support_degree(tonic_pc, oracle_mode, target)
        assert tones == key.applied_dominant_seventh_pitch_classes(target)
        assert support == key.applied_dominant_root_degree(target)
        for inversion in range(3):
            decision = adjudicate_applied_dominant(
                _realization(tones, inversion),
                tonic_pc=tonic_pc,
                active_mode=oracle_mode,
                target_degree=target,
                support_degree=support,
                inversion=inversion,
            )
            assert decision.valid, decision.reason


def test_applied_dominant_oracle_rejects_context_tone_and_inversion_forgeries() -> None:
    mode = TonalMode.MAJOR
    target = 4
    tones = applied_dominant_pitch_classes(0, mode, target)
    support = applied_dominant_support_degree(0, mode, target)
    voices = _realization(tones, 0)
    assert not adjudicate_applied_dominant(
        voices,
        tonic_pc=0,
        active_mode=mode,
        target_degree=2,
        support_degree=support,
        inversion=0,
    ).valid
    assert not adjudicate_applied_dominant(
        voices,
        tonic_pc=0,
        active_mode=mode,
        target_degree=target,
        support_degree=(support + 1) % 7,
        inversion=0,
    ).valid
    assert not adjudicate_applied_dominant(
        (voices[0], voices[1], voices[2], voices[2]),
        tonic_pc=0,
        active_mode=mode,
        target_degree=target,
        support_degree=support,
        inversion=0,
    ).valid
    assert not adjudicate_applied_dominant(
        voices,
        tonic_pc=0,
        active_mode=mode,
        target_degree=target,
        support_degree=support,
        inversion=3,
    ).valid


@pytest.mark.parametrize("tonic_pc", range(12))
@pytest.mark.parametrize("mode", [TonalMode.MAJOR, TonalMode.MINOR])
def test_applied_dominant_oracle_accepts_every_target_resolution(
    tonic_pc: int,
    mode: TonalMode,
) -> None:
    for target in eligible_applied_dominant_targets(tonic_pc, mode):
        tones = applied_dominant_pitch_classes(tonic_pc, mode, target)
        current = tuple(60 + pc for pc in tones)
        following = list(current)
        following[1] += 1
        following[3] -= 1
        decision = adjudicate_applied_dominant_resolution(
            current,
            tuple(following),
            tonic_pc=tonic_pc,
            active_mode=mode,
            target_degree=target,
            following_degree=target,
            following_target=None,
        )
        assert decision.valid, decision.reason


def test_applied_dominant_oracle_rejects_target_chain_and_tendency_failures() -> None:
    current = tuple(
        60 + pc for pc in applied_dominant_pitch_classes(0, TonalMode.MAJOR, 4)
    )
    valid_following = (current[0], current[1] + 1, current[2], current[3] - 1)
    assert not adjudicate_applied_dominant_resolution(
        current,
        valid_following,
        tonic_pc=0,
        active_mode=TonalMode.MAJOR,
        target_degree=4,
        following_degree=3,
        following_target=None,
    ).valid
    assert not adjudicate_applied_dominant_resolution(
        current,
        valid_following,
        tonic_pc=0,
        active_mode=TonalMode.MAJOR,
        target_degree=4,
        following_degree=4,
        following_target=1,
    ).valid
    assert not adjudicate_applied_dominant_resolution(
        current,
        current,
        tonic_pc=0,
        active_mode=TonalMode.MAJOR,
        target_degree=4,
        following_degree=4,
        following_target=None,
    ).valid
