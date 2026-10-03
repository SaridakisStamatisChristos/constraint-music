from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum

NOTE_TO_PC: dict[str, int] = {
    "C": 0,
    "B#": 0,
    "C#": 1,
    "DB": 1,
    "D": 2,
    "D#": 3,
    "EB": 3,
    "E": 4,
    "FB": 4,
    "E#": 5,
    "F": 5,
    "F#": 6,
    "GB": 6,
    "G": 7,
    "G#": 8,
    "AB": 8,
    "A": 9,
    "A#": 10,
    "BB": 10,
    "B": 11,
    "CB": 11,
}

PC_TO_SHARP_NAME: tuple[str, ...] = (
    "C",
    "C#",
    "D",
    "D#",
    "E",
    "F",
    "F#",
    "G",
    "G#",
    "A",
    "A#",
    "B",
)


class Mode(StrEnum):
    MAJOR = "major"
    MINOR = "minor"


class ChordKind(IntEnum):
    TRIAD = 0
    SEVENTH = 1

    @classmethod
    def parse(cls, value: object) -> ChordKind:
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            names = {"triad": cls.TRIAD, "seventh": cls.SEVENTH, "7": cls.SEVENTH}
            if normalized in names:
                return names[normalized]
        if isinstance(value, int):
            try:
                return cls(value)
            except ValueError as exc:
                raise ValueError(f"Unknown chord kind: {value!r}") from exc
        raise ValueError(f"Unknown chord kind: {value!r}")

    @property
    def label(self) -> str:
        return "triad" if self is ChordKind.TRIAD else "seventh"


NO_TONICIZATION_TARGET = 7

SCALE_INTERVALS: dict[Mode, tuple[int, ...]] = {
    Mode.MAJOR: (0, 2, 4, 5, 7, 9, 11),
    # Harmonic minor is deliberate: it gives the solver a true leading tone and dominant.
    Mode.MINOR: (0, 2, 3, 5, 7, 8, 11),
}

ROMAN_NUMERALS: dict[Mode, tuple[str, ...]] = {
    Mode.MAJOR: ("I", "ii", "iii", "IV", "V", "vi", "vii°"),
    Mode.MINOR: ("i", "ii°", "III+", "iv", "V", "VI", "vii°"),
}

# Tonal-function tension on a 0..100 scale.
CHORD_TENSION: dict[Mode, tuple[int, ...]] = {
    Mode.MAJOR: (4, 34, 28, 42, 82, 30, 74),
    Mode.MINOR: (6, 44, 35, 46, 84, 38, 78),
}

# Scale-degree tension; degree 7 is strongest because it wants to resolve to tonic.
DEGREE_TENSION: tuple[int, ...] = (0, 42, 18, 48, 14, 54, 88)

# Default functional-harmony transition graph. Self-loops are intentionally allowed.
# Rows are indexed by source scale degree and contain permitted target degrees.
DEFAULT_PROGRESSION_GRAPH_ROWS: tuple[tuple[int, ...], ...] = (
    (0, 1, 2, 3, 4, 5),
    (1, 3, 4, 6),
    (2, 3, 5),
    (0, 1, 3, 4),
    (0, 4, 5, 6),
    (1, 3, 4, 5),
    (0, 2, 6),
)
DEFAULT_PROGRESSION_GRAPH: dict[int, tuple[int, ...]] = {
    degree: targets for degree, targets in enumerate(DEFAULT_PROGRESSION_GRAPH_ROWS)
}
# Backward-compatible alias for users importing the v1 constant directly.
PROGRESSION_GRAPH = DEFAULT_PROGRESSION_GRAPH


@dataclass(frozen=True, slots=True)
class Key:
    tonic: str
    mode: Mode

    def __post_init__(self) -> None:
        normalized = normalize_note_name(self.tonic)
        object.__setattr__(self, "tonic", normalized)

    @property
    def tonic_pc(self) -> int:
        return NOTE_TO_PC[self.tonic]

    @property
    def pitch_classes(self) -> tuple[int, ...]:
        return tuple((self.tonic_pc + interval) % 12 for interval in SCALE_INTERVALS[self.mode])

    @property
    def leading_tone_pc(self) -> int:
        return self.pitch_classes[6]

    def degree_of_pc(self, pitch_class: int) -> int:
        try:
            return self.pitch_classes.index(pitch_class % 12)
        except ValueError as exc:
            raise ValueError(f"Pitch class {pitch_class % 12} is outside {self}") from exc

    def triad_pitch_classes(self, degree: int) -> tuple[int, int, int]:
        scale = self.pitch_classes
        return (scale[degree % 7], scale[(degree + 2) % 7], scale[(degree + 4) % 7])

    def seventh_pitch_classes(self, degree: int) -> tuple[int, int, int, int]:
        scale = self.pitch_classes
        return (
            scale[degree % 7],
            scale[(degree + 2) % 7],
            scale[(degree + 4) % 7],
            scale[(degree + 6) % 7],
        )

    def triad_quality(self, degree: int) -> str:
        root, third, fifth = self.triad_pitch_classes(degree)
        intervals = ((third - root) % 12, (fifth - root) % 12)
        return {
            (4, 7): "major",
            (3, 7): "minor",
            (3, 6): "diminished",
            (4, 8): "augmented",
        }.get(intervals, "other")

    def applied_dominant_root_pc(self, target_degree: int) -> int:
        if not 1 <= target_degree <= 6:
            raise ValueError("Applied-dominant target degree must be in 1..6")
        return (self.pitch_classes[target_degree] + 7) % 12

    def applied_dominant_root_degree(self, target_degree: int) -> int:
        return self.degree_of_pc(self.applied_dominant_root_pc(target_degree))

    def applied_dominant_seventh_pitch_classes(
        self, target_degree: int
    ) -> tuple[int, int, int, int]:
        root = self.applied_dominant_root_pc(target_degree)
        return (root, (root + 4) % 12, (root + 7) % 12, (root + 10) % 12)

    @property
    def applied_dominant_targets(self) -> tuple[int, ...]:
        """Targets realizable without changing the established CM005/CM006 outer-voice contract."""
        supported: list[int] = []
        for target_degree in range(1, 7):
            if self.triad_quality(target_degree) not in {"major", "minor"}:
                continue
            try:
                root_degree = self.applied_dominant_root_degree(target_degree)
            except ValueError:
                continue
            legacy_outer_pcs = set(self.triad_pitch_classes(root_degree))
            applied_pcs = set(self.applied_dominant_seventh_pitch_classes(target_degree))
            # A complete seventh chord uses four distinct pitch classes. Because soprano and
            # bass retain CM005/CM006, at least two distinct applied tones must also belong to
            # the legacy diatonic triad rooted on chord_degrees[beat].
            if len(legacy_outer_pcs & applied_pcs) >= 2:
                supported.append(target_degree)
        return tuple(supported)

    def chord_name(self, degree: int) -> str:
        return ROMAN_NUMERALS[self.mode][degree]

    def chord_form_name(self, degree: int, kind: ChordKind, inversion: int) -> str:
        base = self.chord_name(degree)
        figures = ("", "6", "64") if kind is ChordKind.TRIAD else ("7", "65", "43")
        if not 0 <= inversion < len(figures):
            raise ValueError(f"Unsupported inversion {inversion} for {kind.label}")
        return f"{base}{figures[inversion]}"

    def applied_dominant_name(self, target_degree: int, inversion: int) -> str:
        if target_degree not in self.applied_dominant_targets:
            raise ValueError(f"Unsupported applied-dominant target degree: {target_degree}")
        figures = ("7", "65", "43")
        if not 0 <= inversion < len(figures):
            raise ValueError(f"Unsupported applied-dominant inversion: {inversion}")
        return f"V{figures[inversion]}/{self.chord_name(target_degree)}"

    def pitches_in_range(self, low: int, high: int) -> tuple[int, ...]:
        pcs = set(self.pitch_classes)
        return tuple(note for note in range(low, high + 1) if note % 12 in pcs)

    def __str__(self) -> str:
        return f"{self.tonic} {self.mode.value}"


def normalize_note_name(name: str) -> str:
    normalized = name.strip().upper().replace("♯", "#").replace("♭", "B")
    if normalized not in NOTE_TO_PC:
        valid = ", ".join(sorted({name for name in NOTE_TO_PC if len(name) <= 2}))
        raise ValueError(
            f"Unknown tonic {name!r}. Use a note name such as C, F#, or Bb. Valid: {valid}"
        )
    return normalized


def midi_note_name(note: int) -> str:
    if not 0 <= note <= 127:
        raise ValueError(f"MIDI note must be in 0..127, got {note}")
    octave = note // 12 - 1
    return f"{PC_TO_SHARP_NAME[note % 12]}{octave}"


def sign(value: int) -> int:
    return (value > 0) - (value < 0)


def is_parallel_perfect(
    melody_a: int,
    bass_a: int,
    melody_b: int,
    bass_b: int,
) -> bool:
    interval_a = (melody_a - bass_a) % 12
    interval_b = (melody_b - bass_b) % 12
    melody_motion = sign(melody_b - melody_a)
    bass_motion = sign(bass_b - bass_a)
    return (
        interval_a == interval_b
        and interval_a in {0, 7}
        and melody_motion != 0
        and melody_motion == bass_motion
    )
