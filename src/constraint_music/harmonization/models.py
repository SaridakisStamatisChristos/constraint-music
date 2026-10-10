"""Immutable, validated obligations for bounded major-key harmonization."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

KEYS = ("C", "G", "D", "A", "E", "F", "Bb", "Eb")
VOICES = ("Soprano", "Alto", "Tenor", "Bass")
DEFAULT_RANGES = ((60, 84), (55, 74), (48, 67), (48, 59))


def integer(value: object, low: int, high: int, name: str) -> None:
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{name} must be an integer in {low}..{high}")


@dataclass(frozen=True, slots=True)
class ChordRequest:
    degree: int
    inversion: int = 0
    seventh: bool = False

    def __post_init__(self) -> None:
        integer(self.degree, 0, 6, "degree")
        integer(self.inversion, 0, 2, "inversion")
        if type(self.seventh) is not bool:
            raise ValueError("seventh must be boolean")
        if self.seventh and self.degree != 4:
            raise ValueError("this profile supports dominant sevenths only")


@dataclass(frozen=True, slots=True)
class HarmonizationRequest:
    key: str
    chords: tuple[ChordRequest, ...]
    # A row is S/A/T/B; None leaves that voice free. No feasibility witnesses.
    given_voices: tuple[tuple[int | None, ...], ...] = ()
    ranges: tuple[tuple[int, int], ...] = DEFAULT_RANGES
    tempo_bpm: int = 108
    beats_per_bar: int = 4
    max_upper_spacing: int = 12

    def __post_init__(self) -> None:
        if self.key not in KEYS:
            raise ValueError(f"key must be one of {KEYS}; this profile is major only")
        object.__setattr__(self, "chords", tuple(self.chords))
        object.__setattr__(self, "ranges", tuple(tuple(r) for r in self.ranges))
        if not 1 <= len(self.chords) <= 128:
            raise ValueError("chords must contain 1..128 entries")
        if any(not isinstance(c, ChordRequest) for c in self.chords):
            raise ValueError("chords must contain ChordRequest entries")
        for i, chord in enumerate(self.chords):
            if chord.seventh and (i + 1 == len(self.chords) or self.chords[i + 1].degree != 0):
                raise ValueError("each dominant seventh must be followed by tonic")
        if len(self.ranges) != 4 or any(len(r) != 2 for r in self.ranges):
            raise ValueError("ranges must contain four lower/upper pairs in S/A/T/B order")
        for low, high in self.ranges:
            integer(low, 0, 127, "range lower bound")
            integer(high, low, 127, "range upper bound")
        given = self.given_voices or ((None, None, None, None),) * len(self.chords)
        object.__setattr__(self, "given_voices", tuple(tuple(row) for row in given))
        if len(given) != len(self.chords) or any(len(row) != 4 for row in given):
            raise ValueError("given_voices must contain one S/A/T/B row per chord")
        for row in given:
            for pitch, (low, high) in zip(row, self.ranges, strict=True):
                if pitch is not None:
                    integer(pitch, low, high, "given pitch")
        integer(self.tempo_bpm, 30, 300, "tempo_bpm")
        integer(self.beats_per_bar, 2, 12, "beats_per_bar")
        integer(self.max_upper_spacing, 1, 24, "max_upper_spacing")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> HarmonizationRequest:
        allowed = {
            "key",
            "chords",
            "given_voices",
            "ranges",
            "tempo_bpm",
            "beats_per_bar",
            "max_upper_spacing",
        }
        if set(raw) - allowed:
            raise ValueError("unknown harmonization request fields")
        payload = dict(raw)
        payload["chords"] = tuple(ChordRequest(**c) for c in payload["chords"])
        return cls(**payload)


@dataclass(frozen=True, slots=True)
class HarmonizationResult:
    request: HarmonizationRequest
    rows: tuple[tuple[int, ...], ...]
    solver_status: str
    wall_time_seconds: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "rows", tuple(tuple(row) for row in self.rows))
        if self.solver_status not in ("OPTIMAL", "FEASIBLE"):
            raise ValueError("result must describe a feasible solve")
        if not math.isfinite(self.wall_time_seconds) or self.wall_time_seconds < 0:
            raise ValueError("wall time must be finite and nonnegative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "request-bound-satb-v1",
            "request": self.request.to_dict(),
            "rows": [list(row) for row in self.rows],
            "solver_status": self.solver_status,
            "wall_time_seconds": self.wall_time_seconds,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> HarmonizationResult:
        if set(raw) != {"schema", "request", "rows", "solver_status", "wall_time_seconds"}:
            raise ValueError("unexpected harmonization result fields")
        if raw["schema"] != "request-bound-satb-v1":
            raise ValueError("unknown harmonization result schema")
        return cls(
            HarmonizationRequest.from_dict(raw["request"]),
            tuple(raw["rows"]),
            raw["solver_status"],
            raw["wall_time_seconds"],
        )
