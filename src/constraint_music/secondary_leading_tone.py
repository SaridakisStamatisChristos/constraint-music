from __future__ import annotations

from enum import StrEnum
from functools import cache

from .theory import Key


class SecondaryLeadingToneSeventhQuality(StrEnum):
    """Certified seventh qualities for secondary leading-tone function."""

    FULLY_DIMINISHED = "fully_diminished"
    HALF_DIMINISHED = "half_diminished"

    @classmethod
    def parse(
        cls,
        value: SecondaryLeadingToneSeventhQuality | str,
    ) -> SecondaryLeadingToneSeventhQuality:
        if isinstance(value, cls):
            return value
        normalized = str(value).strip().lower().replace("-", "_")
        aliases = {
            "fully_diminished": cls.FULLY_DIMINISHED,
            "full": cls.FULLY_DIMINISHED,
            "diminished": cls.FULLY_DIMINISHED,
            "o7": cls.FULLY_DIMINISHED,
            "°7": cls.FULLY_DIMINISHED,
            "half_diminished": cls.HALF_DIMINISHED,
            "half": cls.HALF_DIMINISHED,
            "ø7": cls.HALF_DIMINISHED,
        }
        try:
            return aliases[normalized]
        except KeyError as exc:
            raise ValueError(f"Unknown secondary leading-tone seventh quality: {value!r}") from exc

    @property
    def symbol(self) -> str:
        return "°" if self is self.FULLY_DIMINISHED else "ø"


@cache
def secondary_leading_tone_triad_pitch_classes(
    key: Key,
    target_degree: int,
) -> tuple[int, ...]:
    """Return the diminished leading-tone triad that tonicizes a diatonic target."""
    if not 1 <= target_degree <= 6:
        raise ValueError("Secondary leading-tone target degree must be in 1..6")
    target_pc = key.pitch_classes[target_degree]
    root = (target_pc - 1) % 12
    return (root, (root + 3) % 12, (root + 6) % 12)


@cache
def secondary_leading_tone_seventh_qualities(
    key: Key,
    target_degree: int,
) -> tuple[SecondaryLeadingToneSeventhQuality, ...]:
    """Return the common-practice seventh qualities eligible for a target.

    A fully diminished leading-tone seventh may tonicize either a major or minor
    diatonic triad. The half-diminished form belongs to the temporary major-mode
    leading-tone seventh vocabulary, so it is certified only for major targets.
    Diminished and augmented targets remain outside secondary tonicization.
    """
    if not 1 <= target_degree <= 6:
        raise ValueError("Secondary leading-tone target degree must be in 1..6")
    target_quality = key.triad_quality(target_degree)
    if target_quality == "major":
        return (
            SecondaryLeadingToneSeventhQuality.FULLY_DIMINISHED,
            SecondaryLeadingToneSeventhQuality.HALF_DIMINISHED,
        )
    if target_quality == "minor":
        return (SecondaryLeadingToneSeventhQuality.FULLY_DIMINISHED,)
    return ()


@cache
def secondary_leading_tone_seventh_pitch_classes(
    key: Key,
    target_degree: int,
    quality: SecondaryLeadingToneSeventhQuality | str = (
        SecondaryLeadingToneSeventhQuality.FULLY_DIMINISHED
    ),
) -> tuple[int, int, int, int]:
    """Return a certified target-derived secondary leading-tone seventh.

    The default remains fully diminished for source compatibility with v2.11.
    """
    parsed = SecondaryLeadingToneSeventhQuality.parse(quality)
    if parsed not in secondary_leading_tone_seventh_qualities(key, target_degree):
        raise ValueError(
            f"{parsed.value} is not eligible for target {target_degree} in {key}"
        )
    root, third, diminished_fifth = secondary_leading_tone_triad_pitch_classes(
        key,
        target_degree,
    )
    seventh_interval = 9 if parsed is SecondaryLeadingToneSeventhQuality.FULLY_DIMINISHED else 10
    return (root, third, diminished_fifth, (root + seventh_interval) % 12)


@cache
def secondary_leading_tone_seventh_pitch_class_variants(
    key: Key,
    target_degree: int,
) -> tuple[
    tuple[SecondaryLeadingToneSeventhQuality, tuple[int, int, int, int]], ...
]:
    return tuple(
        (
            quality,
            secondary_leading_tone_seventh_pitch_classes(key, target_degree, quality),
        )
        for quality in secondary_leading_tone_seventh_qualities(key, target_degree)
    )


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
    quality: SecondaryLeadingToneSeventhQuality | str = (
        SecondaryLeadingToneSeventhQuality.FULLY_DIMINISHED
    ),
) -> int:
    """Choose the CM005/CM006 support degree for a certified seventh quality."""
    return _secondary_support_degree(
        key,
        target_degree,
        progression_graph,
        secondary_leading_tone_seventh_pitch_classes(key, target_degree, quality),
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
        for quality in secondary_leading_tone_seventh_qualities(key, target_degree):
            try:
                secondary_leading_tone_seventh_support_degree(
                    key,
                    target_degree,
                    progression_graph,
                    quality,
                )
            except ValueError:
                continue
            supported.append(target_degree)
            break
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
    quality: SecondaryLeadingToneSeventhQuality | str = (
        SecondaryLeadingToneSeventhQuality.FULLY_DIMINISHED
    ),
) -> str:
    parsed = SecondaryLeadingToneSeventhQuality.parse(quality)
    if parsed not in secondary_leading_tone_seventh_qualities(key, target_degree):
        raise ValueError(
            f"{parsed.value} is not eligible for target {target_degree} in {key}"
        )
    if not 0 <= inversion <= 3:
        raise ValueError("Secondary leading-tone seventh inversion must be in 0..3")
    figures = ("7", "65", "43", "42")
    return f"vii{parsed.symbol}{figures[inversion]}/{key.chord_name(target_degree)}"
