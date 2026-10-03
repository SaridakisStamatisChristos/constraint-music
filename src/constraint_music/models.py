from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Any

import yaml

from .theory import DEFAULT_PROGRESSION_GRAPH_ROWS, Key, Mode, midi_note_name


class RhythmState(IntEnum):
    REST = 0
    ONSET = 1
    TIE = 2

    @classmethod
    def parse(cls, value: object) -> RhythmState:
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            names = {"rest": cls.REST, "onset": cls.ONSET, "tie": cls.TIE}
            if normalized in names:
                return names[normalized]
        if isinstance(value, int):
            try:
                return cls(value)
            except ValueError as exc:
                raise ValueError(f"Unknown rhythm state: {value!r}") from exc
        raise ValueError(f"Unknown rhythm state: {value!r}")


@dataclass(frozen=True, slots=True)
class GenerationSpec:
    key: str = "C"
    mode: Mode = Mode.MAJOR
    bars: int = 4
    beats_per_bar: int = 4
    subdivisions_per_beat: int = 2
    tempo_bpm: int = 108
    melody_low: int = 60
    melody_high: int = 81
    bass_low: int = 36
    bass_high: int = 55
    max_melody_leap: int = 12
    max_bass_leap: int = 7
    max_repeated_notes: int = 2
    require_authentic_cadence: bool = True
    resolve_leading_tone: bool = True
    avoid_parallel_perfects: bool = True
    progression_graph: tuple[tuple[int, ...], ...] = DEFAULT_PROGRESSION_GRAPH_ROWS
    tension_curve: tuple[float, ...] = (0.08, 0.20, 0.48, 0.82, 0.18, 0.02)

    rhythm_enabled: bool = False
    min_onsets_per_bar: int = 1
    max_onsets_per_bar: int = 16
    min_rests_per_bar: int = 0
    max_rests_per_bar: int = 4
    min_ties_per_bar: int = 0
    max_ties_per_bar: int = 4
    max_consecutive_rests: int = 1
    max_tie_steps: int = 1
    require_bar_downbeat_onset: bool = True

    motif_relation: str = "none"
    motif_source_bar: int = 0
    motif_target_bar: int = 2
    motif_length_steps: int = 4
    motif_transpose_semitones: int = 0

    seed: int = 7
    max_time_seconds: float = 15.0
    workers: int = 8

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", Mode(self.mode))
        object.__setattr__(
            self, "progression_graph", _normalize_progression_graph(self.progression_graph)
        )
        object.__setattr__(self, "tension_curve", tuple(float(x) for x in self.tension_curve))
        object.__setattr__(self, "motif_relation", str(self.motif_relation).strip().lower())
        self.validate()

    @property
    def tonal_key(self) -> Key:
        return Key(self.key, self.mode)

    @property
    def total_beats(self) -> int:
        return self.bars * self.beats_per_bar

    @property
    def total_steps(self) -> int:
        return self.total_beats * self.subdivisions_per_beat

    @property
    def steps_per_bar(self) -> int:
        return self.beats_per_bar * self.subdivisions_per_beat

    @property
    def progression_pairs(self) -> tuple[tuple[int, int], ...]:
        return tuple(
            (source, target)
            for source, targets in enumerate(self.progression_graph)
            for target in targets
        )

    @property
    def motif_source_start(self) -> int:
        return self.motif_source_bar * self.steps_per_bar

    @property
    def motif_target_start(self) -> int:
        return self.motif_target_bar * self.steps_per_bar

    def validate(self) -> None:
        _between("bars", self.bars, 1, 32)
        _between("beats_per_bar", self.beats_per_bar, 2, 12)
        _between("subdivisions_per_beat", self.subdivisions_per_beat, 1, 4)
        _between("tempo_bpm", self.tempo_bpm, 30, 300)
        _between("melody_low", self.melody_low, 0, 127)
        _between("melody_high", self.melody_high, 0, 127)
        _between("bass_low", self.bass_low, 0, 127)
        _between("bass_high", self.bass_high, 0, 127)
        _between("max_melody_leap", self.max_melody_leap, 1, 24)
        _between("max_bass_leap", self.max_bass_leap, 1, 24)
        _between("max_repeated_notes", self.max_repeated_notes, 1, 8)
        _between("seed", self.seed, 0, 2**31 - 1)
        _between("workers", self.workers, 1, 64)
        if self.melody_low >= self.melody_high:
            raise ValueError("melody_low must be lower than melody_high")
        if self.bass_low >= self.bass_high:
            raise ValueError("bass_low must be lower than bass_high")
        if self.bass_high >= self.melody_low:
            raise ValueError("bass_high must be below melody_low to prevent voice crossing")
        if not 0.05 <= self.max_time_seconds <= 600:
            raise ValueError("max_time_seconds must be in 0.05..600")
        if len(self.tension_curve) < 2:
            raise ValueError("tension_curve needs at least two control points")
        if any(not 0.0 <= x <= 1.0 for x in self.tension_curve):
            raise ValueError("Every tension_curve value must be in 0.0..1.0")
        if self.require_authentic_cadence and not (
            (4, 0) in self.progression_pairs or (6, 0) in self.progression_pairs
        ):
            raise ValueError("Authentic cadence requires progression_graph to allow 4->0 or 6->0")
        _ = self.tonal_key
        if len(self.tonal_key.pitches_in_range(self.melody_low, self.melody_high)) < 8:
            raise ValueError("Melody range is too narrow for the selected key")
        if len(self.tonal_key.pitches_in_range(self.bass_low, self.bass_high)) < 5:
            raise ValueError("Bass range is too narrow for the selected key")

        if self.rhythm_enabled:
            steps = self.steps_per_bar
            for name, value in (
                ("min_onsets_per_bar", self.min_onsets_per_bar),
                ("max_onsets_per_bar", self.max_onsets_per_bar),
                ("min_rests_per_bar", self.min_rests_per_bar),
                ("max_rests_per_bar", self.max_rests_per_bar),
                ("min_ties_per_bar", self.min_ties_per_bar),
                ("max_ties_per_bar", self.max_ties_per_bar),
            ):
                _between(name, value, 0, steps)
            if self.min_onsets_per_bar > self.max_onsets_per_bar:
                raise ValueError("min_onsets_per_bar cannot exceed max_onsets_per_bar")
            if self.min_rests_per_bar > self.max_rests_per_bar:
                raise ValueError("min_rests_per_bar cannot exceed max_rests_per_bar")
            if self.min_ties_per_bar > self.max_ties_per_bar:
                raise ValueError("min_ties_per_bar cannot exceed max_ties_per_bar")
            if (
                self.min_onsets_per_bar + self.min_rests_per_bar + self.min_ties_per_bar
                > steps
            ):
                raise ValueError("Minimum rhythm-state counts exceed steps_per_bar")
            if (
                self.max_onsets_per_bar + self.max_rests_per_bar + self.max_ties_per_bar
                < steps
            ):
                raise ValueError("Maximum rhythm-state counts cannot cover steps_per_bar")
            _between("max_consecutive_rests", self.max_consecutive_rests, 0, steps)
            _between("max_tie_steps", self.max_tie_steps, 0, steps)

        if self.motif_relation not in {"none", "repeat", "transpose"}:
            raise ValueError("motif_relation must be one of: none, repeat, transpose")
        if self.motif_relation != "none":
            _between("motif_source_bar", self.motif_source_bar, 0, self.bars - 1)
            _between("motif_target_bar", self.motif_target_bar, 0, self.bars - 1)
            if self.motif_source_bar == self.motif_target_bar:
                raise ValueError("motif_source_bar and motif_target_bar must differ")
            _between("motif_length_steps", self.motif_length_steps, 1, self.steps_per_bar)
            if not -24 <= self.motif_transpose_semitones <= 24:
                raise ValueError("motif_transpose_semitones must be in -24..24")
            if self.motif_relation == "repeat" and self.motif_transpose_semitones != 0:
                raise ValueError("repeat motifs require motif_transpose_semitones=0")

    def expanded_tension(self) -> tuple[int, ...]:
        """Linearly interpolate control points to one integer target per beat (0..100)."""
        points = self.tension_curve
        if self.total_beats == 1:
            return (round(points[0] * 100),)
        output: list[int] = []
        last = len(points) - 1
        for beat in range(self.total_beats):
            position = beat * last / (self.total_beats - 1)
            left = int(position)
            right = min(left + 1, last)
            alpha = position - left
            value = points[left] * (1.0 - alpha) + points[right] * alpha
            output.append(round(value * 100))
        return tuple(output)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> GenerationSpec:
        known = {item.name for item in cls.__dataclass_fields__.values()}
        unknown = sorted(set(data) - known)
        if unknown:
            raise ValueError(f"Unknown configuration keys: {', '.join(unknown)}")
        return cls(**dict(data))

    @classmethod
    def from_yaml(cls, path: str | Path) -> GenerationSpec:
        source = Path(path)
        with source.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
        if not isinstance(payload, Mapping):
            raise ValueError(f"Expected a YAML mapping in {source}")
        return cls.from_mapping(payload)


@dataclass(frozen=True, slots=True)
class ValidationReport:
    valid: bool
    issues: tuple[str, ...] = ()
    checked_rules: tuple[str, ...] = ()
    failed_rules: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GenerationResult:
    spec: GenerationSpec
    melody: tuple[int, ...]
    bass: tuple[int, ...]
    chord_degrees: tuple[int, ...]
    target_tension: tuple[int, ...]
    actual_tension: tuple[int, ...]
    objective_value: float
    solver_status: str
    wall_time_seconds: float
    rhythm: tuple[RhythmState, ...] = ()
    validation: ValidationReport = field(
        default_factory=lambda: ValidationReport(False, ("Not independently verified",))
    )

    @property
    def effective_rhythm(self) -> tuple[RhythmState, ...]:
        if self.rhythm:
            return tuple(RhythmState.parse(state) for state in self.rhythm)
        return (RhythmState.ONSET,) * len(self.melody)

    @property
    def chord_names(self) -> tuple[str, ...]:
        key = self.spec.tonal_key
        return tuple(key.chord_name(degree) for degree in self.chord_degrees)

    @property
    def melody_names(self) -> tuple[str, ...]:
        return tuple(midi_note_name(note) for note in self.melody)

    @property
    def bass_names(self) -> tuple[str, ...]:
        return tuple(midi_note_name(note) for note in self.bass)

    @property
    def rhythm_names(self) -> tuple[str, ...]:
        return tuple(state.name.lower() for state in self.effective_rhythm)

    def to_dict(self) -> dict[str, Any]:
        spec_dict = asdict(self.spec)
        spec_dict["mode"] = self.spec.mode.value
        spec_dict["progression_graph"] = {
            str(degree): list(targets) for degree, targets in enumerate(self.spec.progression_graph)
        }
        return {
            "spec": spec_dict,
            "solver": {
                "status": self.solver_status,
                "objective": self.objective_value,
                "wall_time_seconds": self.wall_time_seconds,
            },
            "validation": {
                "valid": self.validation.valid,
                "issues": list(self.validation.issues),
                "checked_rules": list(self.validation.checked_rules),
                "failed_rules": list(self.validation.failed_rules),
            },
            "music": {
                "melody_midi": list(self.melody),
                "melody_names": list(self.melody_names),
                "rhythm": list(self.rhythm_names),
                "bass_midi": list(self.bass),
                "bass_names": list(self.bass_names),
                "chord_degrees": list(self.chord_degrees),
                "chord_names": list(self.chord_names),
                "target_tension": list(self.target_tension),
                "actual_tension": list(self.actual_tension),
            },
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> GenerationResult:
        try:
            raw_spec = payload["spec"]
            raw_solver = payload["solver"]
            raw_music = payload["music"]
        except KeyError as exc:
            raise ValueError(f"Result JSON is missing required section: {exc.args[0]}") from exc
        if (
            not isinstance(raw_spec, Mapping)
            or not isinstance(raw_solver, Mapping)
            or not isinstance(raw_music, Mapping)
        ):
            raise ValueError("Result JSON sections spec, solver, and music must be objects")
        spec = GenerationSpec.from_mapping(raw_spec)
        raw_validation = payload.get("validation", {})
        if not isinstance(raw_validation, Mapping):
            raise ValueError("Result JSON validation section must be an object")
        validation = ValidationReport(
            bool(raw_validation.get("valid", False)),
            tuple(str(x) for x in raw_validation.get("issues", ())),
            tuple(str(x) for x in raw_validation.get("checked_rules", ())),
            tuple(str(x) for x in raw_validation.get("failed_rules", ())),
        )
        raw_rhythm = raw_music.get("rhythm", ())
        if not isinstance(raw_rhythm, Sequence) or isinstance(raw_rhythm, (str, bytes)):
            raise ValueError("Result JSON music.rhythm must be an array")
        rhythm = tuple(RhythmState.parse(state) for state in raw_rhythm)
        return cls(
            spec=spec,
            melody=tuple(int(x) for x in _sequence(raw_music, "melody_midi")),
            bass=tuple(int(x) for x in _sequence(raw_music, "bass_midi")),
            chord_degrees=tuple(int(x) for x in _sequence(raw_music, "chord_degrees")),
            target_tension=tuple(int(x) for x in _sequence(raw_music, "target_tension")),
            actual_tension=tuple(int(x) for x in _sequence(raw_music, "actual_tension")),
            objective_value=float(raw_solver.get("objective", 0.0)),
            solver_status=str(raw_solver.get("status", "IMPORTED")),
            wall_time_seconds=float(raw_solver.get("wall_time_seconds", 0.0)),
            rhythm=rhythm,
            validation=validation,
        )


def _sequence(mapping: Mapping[str, Any], key: str) -> Sequence[Any]:
    value = mapping.get(key)
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"Result JSON music.{key} must be an array")
    return value


def _between(name: str, value: int, low: int, high: int) -> None:
    if not low <= value <= high:
        raise ValueError(f"{name} must be in {low}..{high}, got {value}")


def _normalize_progression_graph(value: object) -> tuple[tuple[int, ...], ...]:
    rows: list[object]
    if isinstance(value, Mapping):
        parsed: dict[int, object] = {}
        for raw_source, raw_targets in value.items():
            try:
                source = int(raw_source)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"progression_graph source {raw_source!r} is not an integer degree"
                ) from exc
            if source in parsed:
                raise ValueError(f"Duplicate progression_graph source degree: {source}")
            parsed[source] = raw_targets
        expected = set(range(7))
        if set(parsed) != expected:
            missing = sorted(expected - set(parsed))
            extra = sorted(set(parsed) - expected)
            raise ValueError(
                "progression_graph must define source degrees 0..6 "
                f"(missing={missing}, extra={extra})"
            )
        rows = [parsed[degree] for degree in range(7)]
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        rows = list(value)
        if len(rows) != 7:
            raise ValueError("progression_graph must contain exactly seven source rows")
    else:
        raise ValueError("progression_graph must be a mapping or seven-row sequence")

    canonical: list[tuple[int, ...]] = []
    for source, raw_targets in enumerate(rows):
        if not isinstance(raw_targets, Sequence) or isinstance(raw_targets, (str, bytes)):
            raise ValueError(f"progression_graph[{source}] must be a sequence of target degrees")
        targets = tuple(int(target) for target in raw_targets)
        if not targets:
            raise ValueError(f"progression_graph[{source}] must allow at least one target")
        if any(not 0 <= target <= 6 for target in targets):
            raise ValueError(f"progression_graph[{source}] targets must be in 0..6")
        if len(set(targets)) != len(targets):
            raise ValueError(f"progression_graph[{source}] contains duplicate targets")
        canonical.append(targets)
    return tuple(canonical)
