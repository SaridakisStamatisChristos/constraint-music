"""Independent pitch and tendency oracle for contextual and diatonic harmony."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class TonalMode(StrEnum):
    MAJOR = "major"
    MINOR = "minor"


class ParallelSource(StrEnum):
    MAJOR = "parallel_major"
    NATURAL_MINOR = "parallel_natural_minor"


class DiatonicKind(StrEnum):
    TRIAD = "triad"
    SEVENTH = "seventh"


_ACTIVE_INTERVALS = {
    TonalMode.MAJOR: (0, 2, 4, 5, 7, 9, 11),
    TonalMode.MINOR: (0, 2, 3, 5, 7, 8, 11),
}
_SOURCE_INTERVALS = {
    ParallelSource.MAJOR: (0, 2, 4, 5, 7, 9, 11),
    ParallelSource.NATURAL_MINOR: (0, 2, 3, 5, 7, 8, 10),
}


@dataclass(frozen=True, slots=True)
class ContextualDecision:
    valid: bool
    reason: str
    expected_pitch_classes: tuple[int, ...]


def _stacked_thirds(scale: tuple[int, ...], degree: int, tones: int) -> tuple[int, ...]:
    if not 0 <= degree <= 6:
        raise ValueError("degree must be in 0..6")
    return tuple(scale[(degree + 2 * offset) % 7] for offset in range(tones))


def _scale(tonic_pc: int, intervals: tuple[int, ...]) -> tuple[int, ...]:
    if not 0 <= tonic_pc <= 11:
        raise ValueError("tonic pitch class must be in 0..11")
    return tuple((tonic_pc + interval) % 12 for interval in intervals)


def canonical_parallel_source(active_mode: str | TonalMode) -> ParallelSource:
    mode = active_mode if isinstance(active_mode, TonalMode) else TonalMode(active_mode)
    return ParallelSource.NATURAL_MINOR if mode is TonalMode.MAJOR else ParallelSource.MAJOR


def diatonic_pitch_classes(
    tonic_pc: int,
    active_mode: str | TonalMode,
    degree: int,
    kind: str | DiatonicKind,
) -> tuple[int, ...]:
    mode = active_mode if isinstance(active_mode, TonalMode) else TonalMode(active_mode)
    parsed_kind = kind if isinstance(kind, DiatonicKind) else DiatonicKind(kind)
    scale = _scale(tonic_pc, _ACTIVE_INTERVALS[mode])
    tones = 3 if parsed_kind is DiatonicKind.TRIAD else 4
    return _stacked_thirds(scale, degree, tones)


def adjudicate_diatonic_chord(
    voices: tuple[int, int, int, int],
    *,
    tonic_pc: int,
    active_mode: str | TonalMode,
    degree: int,
    kind: str | DiatonicKind,
    inversion: int,
) -> ContextualDecision:
    parsed_kind = kind if isinstance(kind, DiatonicKind) else DiatonicKind(kind)
    expected = diatonic_pitch_classes(tonic_pc, active_mode, degree, parsed_kind)
    if inversion not in range(3):
        return ContextualDecision(False, "diatonic inversion is outside 0..2", expected)
    realized = tuple(pitch % 12 for pitch in voices)
    if parsed_kind is DiatonicKind.TRIAD:
        root = expected[0]
        if set(realized) != set(expected) or realized.count(root) != 2:
            return ContextualDecision(
                False, "triad is incomplete or root doubling is not exact", expected
            )
    elif len(set(realized)) != 4 or set(realized) != set(expected):
        return ContextualDecision(False, "seventh does not realize four distinct tones", expected)
    if realized[3] != expected[inversion]:
        return ContextualDecision(False, "bass does not realize the declared inversion", expected)
    return ContextualDecision(True, "exact diatonic realization and inversion", expected)


def adjudicate_diatonic_seventh_resolution(
    current: tuple[int, int, int, int],
    following: tuple[int, int, int, int],
    *,
    tonic_pc: int,
    active_mode: str | TonalMode,
    degree: int,
    following_degree: int,
) -> ContextualDecision:
    mode = active_mode if isinstance(active_mode, TonalMode) else TonalMode(active_mode)
    expected = diatonic_pitch_classes(tonic_pc, mode, degree, DiatonicKind.SEVENTH)
    chordal_seventh = expected[3]
    leading_tone = _scale(tonic_pc, _ACTIVE_INTERVALS[mode])[6]
    for left, right in zip(current, following, strict=True):
        if left % 12 == chordal_seventh and right - left not in {-1, -2}:
            return ContextualDecision(False, "chordal seventh does not fall by step", expected)
        if degree == 4 and left % 12 == leading_tone and right != left + 1:
            return ContextualDecision(
                False, "dominant leading tone does not rise by semitone", expected
            )
    if degree == 4 and following_degree != 0:
        return ContextualDecision(False, "dominant seventh does not resolve to tonic", expected)
    return ContextualDecision(True, "all diatonic-seventh tendencies resolve", expected)


def applied_dominant_pitch_classes(
    tonic_pc: int,
    active_mode: str | TonalMode,
    target_degree: int,
) -> tuple[int, int, int, int]:
    mode = active_mode if isinstance(active_mode, TonalMode) else TonalMode(active_mode)
    if not 1 <= target_degree <= 6:
        raise ValueError("applied-dominant target degree must be in 1..6")
    scale = _scale(tonic_pc, _ACTIVE_INTERVALS[mode])
    root = (scale[target_degree] + 7) % 12
    return root, (root + 4) % 12, (root + 7) % 12, (root + 10) % 12


def eligible_applied_dominant_targets(
    tonic_pc: int,
    active_mode: str | TonalMode,
) -> tuple[int, ...]:
    """Derive targets compatible with the retained diatonic outer-voice contract."""

    mode = active_mode if isinstance(active_mode, TonalMode) else TonalMode(active_mode)
    scale = _scale(tonic_pc, _ACTIVE_INTERVALS[mode])
    eligible: list[int] = []
    for target_degree in range(1, 7):
        target = _stacked_thirds(scale, target_degree, 3)
        quality = ((target[1] - target[0]) % 12, (target[2] - target[0]) % 12)
        if quality not in {(4, 7), (3, 7)}:
            continue
        applied = applied_dominant_pitch_classes(tonic_pc, mode, target_degree)
        if applied[0] not in scale:
            continue
        support_degree = scale.index(applied[0])
        support = _stacked_thirds(scale, support_degree, 3)
        if len(set(support) & set(applied)) >= 2:
            eligible.append(target_degree)
    return tuple(eligible)


def applied_dominant_support_degree(
    tonic_pc: int,
    active_mode: str | TonalMode,
    target_degree: int,
) -> int:
    mode = active_mode if isinstance(active_mode, TonalMode) else TonalMode(active_mode)
    if target_degree not in eligible_applied_dominant_targets(tonic_pc, mode):
        raise ValueError("target is outside the applied-dominant policy")
    scale = _scale(tonic_pc, _ACTIVE_INTERVALS[mode])
    root = applied_dominant_pitch_classes(tonic_pc, mode, target_degree)[0]
    return scale.index(root)


def adjudicate_applied_dominant(
    voices: tuple[int, int, int, int],
    *,
    tonic_pc: int,
    active_mode: str | TonalMode,
    target_degree: int,
    support_degree: int,
    inversion: int,
) -> ContextualDecision:
    mode = active_mode if isinstance(active_mode, TonalMode) else TonalMode(active_mode)
    expected = applied_dominant_pitch_classes(tonic_pc, mode, target_degree)
    if target_degree not in eligible_applied_dominant_targets(tonic_pc, mode):
        return ContextualDecision(False, "target is outside the applied-dominant policy", expected)
    if support_degree != applied_dominant_support_degree(tonic_pc, mode, target_degree):
        return ContextualDecision(
            False, "support degree does not encode the applied root", expected
        )
    if inversion not in range(3):
        return ContextualDecision(False, "applied-dominant inversion is outside 0..2", expected)
    realized = tuple(pitch % 12 for pitch in voices)
    if len(set(realized)) != 4 or set(realized) != set(expected):
        return ContextualDecision(False, "realization is not the exact applied dominant", expected)
    if realized[3] != expected[inversion]:
        return ContextualDecision(False, "bass does not realize the declared inversion", expected)
    return ContextualDecision(True, "exact target-derived applied dominant", expected)


def adjudicate_applied_dominant_resolution(
    current: tuple[int, int, int, int],
    following: tuple[int, int, int, int],
    *,
    tonic_pc: int,
    active_mode: str | TonalMode,
    target_degree: int,
    following_degree: int,
    following_target: int | None,
) -> ContextualDecision:
    mode = active_mode if isinstance(active_mode, TonalMode) else TonalMode(active_mode)
    expected = applied_dominant_pitch_classes(tonic_pc, mode, target_degree)
    if target_degree not in eligible_applied_dominant_targets(tonic_pc, mode):
        return ContextualDecision(False, "target is outside the applied-dominant policy", expected)
    if following_degree != target_degree or following_target is not None:
        return ContextualDecision(
            False, "applied dominant misses its untargeted local tonic", expected
        )
    local_leading_tone = expected[1]
    chordal_seventh = expected[3]
    for left, right in zip(current, following, strict=True):
        if left % 12 == chordal_seventh and right - left not in {-1, -2}:
            return ContextualDecision(
                False, "applied chordal seventh does not fall by step", expected
            )
        if left % 12 == local_leading_tone and right != left + 1:
            return ContextualDecision(
                False, "applied leading tone does not rise by semitone", expected
            )
    return ContextualDecision(True, "target and applied tendencies resolve", expected)


def borrowed_seventh_pitch_classes(
    tonic_pc: int,
    source: str | ParallelSource,
    degree: int,
) -> tuple[int, ...]:
    parsed = source if isinstance(source, ParallelSource) else ParallelSource(source)
    scale = _scale(tonic_pc, _SOURCE_INTERVALS[parsed])
    return _stacked_thirds(scale, degree, 4)


def eligible_borrowed_seventh_degrees(
    tonic_pc: int,
    active_mode: str | TonalMode,
) -> tuple[int, ...]:
    """Derive the narrow eligibility policy without importing production theory code."""

    mode = active_mode if isinstance(active_mode, TonalMode) else TonalMode(active_mode)
    active_scale = _scale(tonic_pc, _ACTIVE_INTERVALS[mode])
    source = canonical_parallel_source(mode)
    source_leading = (tonic_pc - 1) % 12 if source is ParallelSource.MAJOR else None
    eligible: list[int] = []
    for degree in range(7):
        if degree == 4:
            continue
        active_triad = _stacked_thirds(active_scale, degree, 3)
        active_seventh = _stacked_thirds(active_scale, degree, 4)
        borrowed = borrowed_seventh_pitch_classes(tonic_pc, source, degree)
        if set(borrowed) == set(active_seventh):
            continue
        if len(set(active_triad) & set(borrowed)) < 2:
            continue
        if borrowed[3] != active_seventh[3]:
            continue
        if source_leading is not None and borrowed[3] == source_leading:
            continue
        eligible.append(degree)
    return tuple(eligible)


def adjudicate_borrowed_seventh(
    voices: tuple[int, int, int, int],
    *,
    tonic_pc: int,
    active_mode: str | TonalMode,
    source: str | ParallelSource,
    degree: int,
    inversion: int,
) -> ContextualDecision:
    mode = active_mode if isinstance(active_mode, TonalMode) else TonalMode(active_mode)
    parsed_source = source if isinstance(source, ParallelSource) else ParallelSource(source)
    expected = borrowed_seventh_pitch_classes(tonic_pc, parsed_source, degree)
    if parsed_source is not canonical_parallel_source(mode):
        return ContextualDecision(False, "source is not the canonical parallel mode", expected)
    if degree not in eligible_borrowed_seventh_degrees(tonic_pc, mode):
        return ContextualDecision(False, "degree is outside the borrowed-seventh policy", expected)
    if inversion not in range(3):
        return ContextualDecision(False, "borrowed-seventh inversion is outside 0..2", expected)
    realized = tuple(pitch % 12 for pitch in voices)
    if len(set(realized)) != 4 or set(realized) != set(expected):
        return ContextualDecision(False, "realization is not the exact source seventh", expected)
    if realized[3] != expected[inversion]:
        return ContextualDecision(False, "bass does not realize the declared inversion", expected)
    return ContextualDecision(True, "exact source-derived seventh and inversion", expected)


def secondary_triad_pitch_classes(target_pitch_class: int) -> tuple[int, int, int]:
    if not 0 <= target_pitch_class <= 11:
        raise ValueError("target pitch class must be in 0..11")
    root = (target_pitch_class - 1) % 12
    return root, (root + 3) % 12, (root + 6) % 12


def adjudicate_secondary_triad(
    voices: tuple[int, int, int, int],
    *,
    target_pitch_class: int,
    inversion: int,
) -> ContextualDecision:
    expected = secondary_triad_pitch_classes(target_pitch_class)
    if inversion not in range(3):
        return ContextualDecision(False, "secondary-triad inversion is outside 0..2", expected)
    realized = tuple(pitch % 12 for pitch in voices)
    root, third, diminished_fifth = expected
    if (
        set(realized) != set(expected)
        or realized.count(root) != 1
        or realized.count(third) != 2
        or realized.count(diminished_fifth) != 1
    ):
        return ContextualDecision(
            False, "triad does not have exact tendency-tone doubling", expected
        )
    if realized[3] != expected[inversion]:
        return ContextualDecision(False, "bass does not realize the declared inversion", expected)
    return ContextualDecision(True, "exact target-derived triad and inversion", expected)


def adjudicate_secondary_triad_resolution(
    current: tuple[int, int, int, int],
    following: tuple[int, int, int, int],
    *,
    target_pitch_class: int,
) -> ContextualDecision:
    expected = secondary_triad_pitch_classes(target_pitch_class)
    root, _third, diminished_fifth = expected
    for left, right in zip(current, following, strict=True):
        if left % 12 == root and right != left + 1:
            return ContextualDecision(
                False, "local leading tone does not rise by semitone", expected
            )
        if left % 12 == diminished_fifth and right - left not in {-1, -2}:
            return ContextualDecision(False, "diminished fifth does not fall by step", expected)
    return ContextualDecision(True, "all secondary-triad tendency tones resolve", expected)
