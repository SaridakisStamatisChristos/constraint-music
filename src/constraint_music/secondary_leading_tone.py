from __future__ import annotations

from functools import cache

from .theory import Key


@cache
def secondary_leading_tone_triad_pitch_classes(
    key: Key,
    target_degree: int,
) -> tuple[int, int, int]:
    """Return the diminished leading-tone triad that tonicizes a diatonic target."""
    if not 1 <= target_degree <= 6:
        raise ValueError("Secondary leading-tone target degree must be in 1..6")
    target_pc = key.pitch_classes[target_degree]
    root = (target_pc - 1) % 12
    return (root, (root + 3) % 12, (root + 6) % 12)


@cache
def secondary_leading_tone_seventh_pitch_classes(
    key: Key,
    target_degree: int,
) -> tuple[int, int, int, int]:
    """Return v2.11's fully diminished leading-tone seventh for a diatonic target.

    v2.11 deliberately admits only the fully diminished quality. Half-diminished
    secondary leading-tone sevenths remain outside the certified contract so that
    target + seventh has a deterministic, verifier-reconstructable pitch identity.
    """
    root, third, diminished_fifth = secondary_leading_tone_triad_pitch_classes(
        key,
        target_degree,
    )
    return (root, third, diminished_fifth, (root + 9) % 12)


def _secondary_support_degree(
    key: Key,
    target_degree: int,
    progression_graph: tuple[tuple[int, ...], ...],
    chromatic_pitch_classes: tuple[int, ...],
) -> int:
    if len(progression_graph) != 7:
        raise ValueError("progression_graph must contain exactly seven source rows")
    if not 1 <= target_degree <= 6:
        raise ValueError("Secondary leading-tone target degree must be in 1..6")
    if key.triad_quality(target_degree) not in {"major", "minor"}:
        raise ValueError("Secondary leading-tone target must be a major or minor triad")

    chromatic = set(chromatic_pitch_classes)
    candidates: list[tuple[int, int]] = []
    for support_degree, targets in enumerate(progression_graph):
        if target_degree not in targets:
            continue
        overlap = len(chromatic & set(key.triad_pitch_classes(support_degree)))
        if overlap >= 2:
            candidates.append((overlap, support_degree))
    if not candidates:
        raise ValueError(
            f"No CM005/CM006-compatible support degree for secondary leading-tone target "
            f"{target_degree} in {key}"
        )
    best_overlap = max(item[0] for item in candidates)
    return min(
        support_degree
        for overlap, support_degree in candidates
        if overlap == best_overlap
    )


def secondary_leading_tone_support_degree(
    key: Key,
    target_degree: int,
    progression_graph: tuple[tuple[int, ...], ...],
) -> int:
    """Choose the active-key support degree that preserves CM005/CM006.

    The chromatic leading-tone triad has its own functional identity in target metadata.
    ``chord_degrees`` continues to drive the legacy outer-voice and progression contract,
    so the support degree is the best diatonic triad sharing at least two chord tones and
    already permitted to progress directly to the declared target.
    """
    return _secondary_support_degree(
        key,
        target_degree,
        progression_graph,
        secondary_leading_tone_triad_pitch_classes(key, target_degree),
    )


def secondary_leading_tone_seventh_support_degree(
    key: Key,
    target_degree: int,
    progression_graph: tuple[tuple[int, ...], ...],
) -> int:
    """Choose the CM005/CM006 support degree for a v2.11 fully diminished seventh."""
    return _secondary_support_degree(
        key,
        target_degree,
        progression_graph,
        secondary_leading_tone_seventh_pitch_classes(key, target_degree),
    )


def supported_secondary_leading_tone_targets(
    key: Key,
    progression_graph: tuple[tuple[int, ...], ...],
) -> tuple[int, ...]:
    supported: list[int] = []
    for target_degree in range(1, 7):
        if key.triad_quality(target_degree) not in {"major", "minor"}:
            continue
        try:
            secondary_leading_tone_support_degree(key, target_degree, progression_graph)
        except ValueError:
            continue
        supported.append(target_degree)
    return tuple(supported)


def supported_secondary_leading_tone_seventh_targets(
    key: Key,
    progression_graph: tuple[tuple[int, ...], ...],
) -> tuple[int, ...]:
    supported: list[int] = []
    for target_degree in range(1, 7):
        if key.triad_quality(target_degree) not in {"major", "minor"}:
            continue
        try:
            secondary_leading_tone_seventh_support_degree(
                key,
                target_degree,
                progression_graph,
            )
        except ValueError:
            continue
        supported.append(target_degree)
    return tuple(supported)


def secondary_leading_tone_name(
    key: Key,
    target_degree: int,
    inversion: int,
) -> str:
    if not 0 <= inversion <= 2:
        raise ValueError("Secondary leading-tone inversion must be in 0..2")
    figures = ("", "6", "64")
    return f"vii°{figures[inversion]}/{key.chord_name(target_degree)}"


def secondary_leading_tone_seventh_name(
    key: Key,
    target_degree: int,
    inversion: int,
) -> str:
    if not 0 <= inversion <= 2:
        raise ValueError("Secondary leading-tone seventh inversion must be in 0..2")
    figures = ("7", "65", "43")
    return f"vii°{figures[inversion]}/{key.chord_name(target_degree)}"
