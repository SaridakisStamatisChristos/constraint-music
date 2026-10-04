from __future__ import annotations

from enum import StrEnum
from functools import cache

from .theory import Key


class SecondaryLeadingToneSeventhQuality(StrEnum):
    """Verifier-reconstructable qualities for secondary leading-tone sevenths."""

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
            raise ValueError(
                f"Unknown secondary leading-tone seventh quality: {value!r}"
            ) from exc

    @property
    def symbol(self) -> str:
        return "°" if self is self.FULLY_DIMINISHED else "ø"

    @property
    def solver_id(self) -> int:
        return 1 if self is self.FULLY_DIMINISHED else 2

    @classmethod
    def from_solver_id(cls, value: int) -> SecondaryLeadingToneSeventhQuality:
        if value == 1:
            return cls.FULLY_DIMINISHED
        if value == 2:
            return cls.HALF_DIMINISHED
        raise ValueError(f"Unknown secondary leading-tone seventh solver id: {value}")


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
    """Return the common-practice qualities eligible for a diatonic target.

    Fully diminished leading-tone sevenths are certified for temporary major and
    minor targets. Half-diminished leading-tone sevenths are certified for temporary
    major targets, where scale degree 6 of the temporary key is diatonic. Diminished
    and augmented targets are not treated as local tonics by this subsystem.
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
    """Return one exact target-derived secondary leading-tone seventh.

    The default quality remains fully diminished so existing v2.11 API calls keep
    their meaning. v2.12's runtime explicitly enumerates all eligible qualities.
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
    seventh_interval = (
        9
        if parsed is SecondaryLeadingToneSeventhQuality.FULLY_DIMINISHED
        else 10
    )
    return (root, third, diminished_fifth, (root + seventh_interval) % 12)


@cache
def secondary_leading_tone_seventh_pitch_class_variants(
    key: Key,
    target_degree: int,
) -> tuple[
    tuple[SecondaryLeadingToneSeventhQuality, tuple[int, int, int, int]], ...
]:
    """Enumerate every quality/pitch realization certified for one target."""
    return tuple(
        (
            quality,
            secondary_leading_tone_seventh_pitch_classes(
                key,
                target_degree,
                quality,
            ),
        )
        for quality in secondary_leading_tone_seventh_qualities(key, target_degree)
    )


def identify_secondary_leading_tone_seventh_quality(
    key: Key,
    target_degree: int,
    pitch_classes: tuple[int, ...],
) -> SecondaryLeadingToneSeventhQuality | None:
    """Reconstruct quality from target and complete four-tone pitch content."""
    if len(pitch_classes) != 4 or len(set(pitch_classes)) != 4:
        return None
    actual = set(pitch_classes)
    for quality, expected in secondary_leading_tone_seventh_pitch_class_variants(
        key,
        target_degree,
    ):
        if actual == set(expected):
            return quality
    return None


def _secondary_support_degree(
    key: Key,
    target_degree: int,
    progression_graph: tuple[tuple[int, ...], ...],
    chromatic_pitch_classes: tuple[int, ...],
    *,
    minimum_overlap: int,
) -> int:
    """Choose a deterministic structural support degree for a chromatic function.

    ``chord_degrees`` remains the structural axis used by the legacy progression
    graph. The secondary function itself is reconstructed independently from target,
    quality, inversion, and SATB pitch content. Triads retain the historical two-tone
    overlap requirement; v2.12 sevenths no longer need that workaround because CM005
    and CM006 admit exact reconstructed secondary-seventh chord members directly.
    """
    if len(progression_graph) != 7:
        raise ValueError("progression_graph must contain exactly seven source rows")
    if not 1 <= target_degree <= 6:
        raise ValueError("Secondary leading-tone target degree must be in 1..6")
    if key.triad_quality(target_degree) not in {"major", "minor"}:
        raise ValueError("Secondary leading-tone target must be a major or minor triad")
    if not 0 <= minimum_overlap <= 4:
        raise ValueError("minimum_overlap must be in 0..4")

    chromatic = set(chromatic_pitch_classes)
    candidates: list[tuple[int, int]] = []
    for support_degree, targets in enumerate(progression_graph):
        if target_degree not in targets:
            continue
        overlap = len(chromatic & set(key.triad_pitch_classes(support_degree)))
        if overlap >= minimum_overlap:
            candidates.append((overlap, support_degree))
    if not candidates:
        raise ValueError(
            "No progression-compatible support degree for secondary leading-tone "
            f"target {target_degree} in {key}"
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
    """Choose the deterministic support degree for a secondary diminished triad."""
    return _secondary_support_degree(
        key,
        target_degree,
        progression_graph,
        secondary_leading_tone_triad_pitch_classes(key, target_degree),
        minimum_overlap=2,
    )


def secondary_leading_tone_seventh_support_degree(
    key: Key,
    target_degree: int,
    progression_graph: tuple[tuple[int, ...], ...],
    quality: SecondaryLeadingToneSeventhQuality | str = (
        SecondaryLeadingToneSeventhQuality.FULLY_DIMINISHED
    ),
) -> int:
    """Choose structural support for one complete v2.12 seventh variant.

    Unlike v2.11, no diatonic-overlap threshold is required. The support degree only
    preserves the configured progression graph; exact chord membership is certified
    independently by CM055-CM057. Among all graph-compatible predecessors, the most
    pitch-overlapping degree is selected deterministically, with the lowest degree as
    a stable tie-breaker.
    """
    return _secondary_support_degree(
        key,
        target_degree,
        progression_graph,
        secondary_leading_tone_seventh_pitch_classes(
            key,
            target_degree,
            quality,
        ),
        minimum_overlap=0,
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
            secondary_leading_tone_support_degree(
                key,
                target_degree,
                progression_graph,
            )
        except ValueError:
            continue
        supported.append(target_degree)
    return tuple(supported)


def supported_secondary_leading_tone_seventh_variants(
    key: Key,
    progression_graph: tuple[tuple[int, ...], ...],
) -> tuple[tuple[int, SecondaryLeadingToneSeventhQuality, int], ...]:
    """Return (target, quality, support degree) for every certified variant."""
    supported: list[tuple[int, SecondaryLeadingToneSeventhQuality, int]] = []
    for target_degree in range(1, 7):
        for quality in secondary_leading_tone_seventh_qualities(key, target_degree):
            try:
                support = secondary_leading_tone_seventh_support_degree(
                    key,
                    target_degree,
                    progression_graph,
                    quality,
                )
            except ValueError:
                continue
            supported.append((target_degree, quality, support))
    return tuple(supported)


def supported_secondary_leading_tone_seventh_targets(
    key: Key,
    progression_graph: tuple[tuple[int, ...], ...],
) -> tuple[int, ...]:
    """Return target degrees with at least one verifier-certified seventh quality."""
    return tuple(
        dict.fromkeys(
            target
            for target, _quality, _support in (
                supported_secondary_leading_tone_seventh_variants(
                    key,
                    progression_graph,
                )
            )
        )
    )


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
