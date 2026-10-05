"""Independent bounded reference for secondary leading-tone sevenths."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SeventhQuality(StrEnum):
    FULLY_DIMINISHED = "fully-diminished"
    HALF_DIMINISHED = "half-diminished"


_INTERVALS = {
    SeventhQuality.FULLY_DIMINISHED: (0, 3, 6, 9),
    SeventhQuality.HALF_DIMINISHED: (0, 3, 6, 10),
}


@dataclass(frozen=True, slots=True)
class OracleDecision:
    valid: bool
    reason: str
    expected_pitch_classes: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class SatbRegisterBounds:
    """Finite register used by the bounded conformance experiment."""

    soprano: tuple[int, int] = (60, 81)
    alto: tuple[int, int] = (55, 74)
    tenor: tuple[int, int] = (48, 67)
    bass: tuple[int, int] = (36, 55)
    max_upper_spacing: int = 12


@dataclass(frozen=True, slots=True)
class RegisterDecision:
    valid: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ResolutionDecision:
    valid: bool
    reasons: tuple[str, ...]


_DEFAULT_SATB_REGISTER_BOUNDS = SatbRegisterBounds()


def secondary_seventh_pitch_classes(
    target_pitch_class: int, quality: str | SeventhQuality
) -> tuple[int, ...]:
    """Derive vii°7/x or viiø7/x from the local target, modulo 12."""

    parsed = quality if isinstance(quality, SeventhQuality) else SeventhQuality(quality)
    root = (target_pitch_class - 1) % 12
    return tuple((root + interval) % 12 for interval in _INTERVALS[parsed])


def adjudicate_secondary_seventh(
    voices: tuple[int, int, int, int],
    *,
    target_pitch_class: int,
    quality: str | SeventhQuality,
    inversion: int,
    half_diminished_eligible: bool,
) -> OracleDecision:
    parsed = quality if isinstance(quality, SeventhQuality) else SeventhQuality(quality)
    expected = secondary_seventh_pitch_classes(target_pitch_class, parsed)
    if parsed is SeventhQuality.HALF_DIMINISHED and not half_diminished_eligible:
        return OracleDecision(False, "half-diminished quality is ineligible", expected)
    if inversion not in range(4):
        return OracleDecision(False, "inversion is outside 0..3", expected)
    realized = tuple(pitch % 12 for pitch in voices)
    if len(set(realized)) != 4 or set(realized) != set(expected):
        return OracleDecision(False, "realization is not the exact four-tone relation", expected)
    if realized[3] != expected[inversion]:
        return OracleDecision(False, "bass does not realize the declared inversion", expected)
    return OracleDecision(True, "exact target-derived seventh and inversion", expected)


def pitches_for_pitch_classes(
    low: int,
    high: int,
    pitch_classes: tuple[int, ...],
) -> tuple[int, ...]:
    """Enumerate a closed MIDI range without using production range helpers."""

    allowed = set(pitch_classes)
    return tuple(note for note in range(low, high + 1) if note % 12 in allowed)


def adjudicate_satb_register(
    voices: tuple[int, int, int, int],
    *,
    bounds: SatbRegisterBounds = _DEFAULT_SATB_REGISTER_BOUNDS,
) -> RegisterDecision:
    """Check the explicitly bounded S/A/T/B range, ordering, and spacing relation."""

    soprano, alto, tenor, bass = voices
    reasons: list[str] = []
    for label, note, (low, high) in zip(
        ("soprano", "alto", "tenor", "bass"),
        voices,
        (bounds.soprano, bounds.alto, bounds.tenor, bounds.bass),
        strict=True,
    ):
        if not low <= note <= high:
            reasons.append(f"{label} is outside {low}..{high}")
    if not bass < tenor < alto < soprano:
        reasons.append("SATB voices are not strictly ordered")
    if soprano - alto > bounds.max_upper_spacing:
        reasons.append("soprano/alto spacing exceeds the bound")
    if alto - tenor > bounds.max_upper_spacing:
        reasons.append("alto/tenor spacing exceeds the bound")
    return RegisterDecision(not reasons, tuple(reasons))


def adjudicate_voice_resolutions(
    source: tuple[int, int, int, int],
    destination: tuple[int, int, int, int],
    *,
    target_pitch_class: int,
    target_is_major: bool,
    quality: str | SeventhQuality,
) -> ResolutionDecision:
    """Check every voice-specific tendency motion, leaving the stable third unconstrained."""

    parsed = quality if isinstance(quality, SeventhQuality) else SeventhQuality(quality)
    root, _third, diminished_fifth, chordal_seventh = secondary_seventh_pitch_classes(
        target_pitch_class,
        parsed,
    )
    required = {
        root: 1,
        diminished_fifth: -1 if target_is_major else -2,
        chordal_seventh: -1 if parsed is SeventhQuality.FULLY_DIMINISHED else -2,
    }
    reasons: list[str] = []
    for label, before, after in zip(
        ("soprano", "alto", "tenor", "bass"),
        source,
        destination,
        strict=True,
    ):
        expected_delta = required.get(before % 12)
        if expected_delta is not None and after - before != expected_delta:
            reasons.append(
                f"{label} moves {after - before:+d}; expected {expected_delta:+d}"
            )
    return ResolutionDecision(not reasons, tuple(reasons))


def target_triad_pitch_classes(
    target_pitch_class: int,
    *,
    target_is_major: bool,
) -> tuple[int, int, int]:
    third = 4 if target_is_major else 3
    return (
        target_pitch_class % 12,
        (target_pitch_class + third) % 12,
        (target_pitch_class + 7) % 12,
    )


def adjudicate_target_triad(
    voices: tuple[int, int, int, int],
    *,
    target_pitch_class: int,
    target_is_major: bool,
) -> OracleDecision:
    """Require an exact complete target triad with one doubled member."""

    expected = target_triad_pitch_classes(
        target_pitch_class,
        target_is_major=target_is_major,
    )
    realized = tuple(note % 12 for note in voices)
    valid = set(realized) == set(expected) and len(realized) == 4
    return OracleDecision(
        valid,
        "exact complete target triad" if valid else "destination is not a complete target triad",
        expected,
    )
