"""Independent pitch-class relation for secondary leading-tone sevenths."""

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
