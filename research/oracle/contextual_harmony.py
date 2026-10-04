"""Independent local oracle for borrowed sevenths and secondary diminished triads."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class TonalMode(StrEnum):
    MAJOR = "major"
    MINOR = "minor"


class ParallelSource(StrEnum):
    MAJOR = "parallel_major"
    NATURAL_MINOR = "parallel_natural_minor"


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
