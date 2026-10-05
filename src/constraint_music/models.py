from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from enum import IntEnum
from itertools import pairwise
from pathlib import Path
from typing import Any

import yaml

from .contract import RuleDiagnostic, RuleOutcome, RuleStatus
from .modal_mixture import supported_borrowed_degrees
from .modulation import dominant_key
from .phrase import PhraseSpec, normalize_phrases, phrase_by_id
from .secondary_leading_tone import (
    supported_secondary_leading_tone_seventh_targets,
    supported_secondary_leading_tone_targets,
)
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

    # Expanded harmony remains opt-in so pre-v2.5 specifications keep their feasible set.
    harmony_vocabulary: str = "triads"
    minimum_seventh_chords: int = 0

    # v2.6 keeps tonicization orthogonal to chord vocabulary. Applied dominants are
    # dominant-seventh forms with an explicit local target; generic chromaticism is not enabled.
    tonicization_enabled: bool = False
    minimum_applied_dominants: int = 0

    # v2.7 modal mixture is independent of seventh vocabulary and tonicization. Borrowed
    # triads carry explicit parallel-source identity while legacy outer-voice rules stay intact.
    modal_mixture_enabled: bool = False
    minimum_borrowed_chords: int = 0

    # v2.10 adds a distinct chromatic function that reuses local target identity while
    # preserving the legacy outer-voice/progression contract through a verified support degree.
    secondary_leading_tone_enabled: bool = False
    minimum_secondary_leading_tone_chords: int = 0

    # v2.12 completes the decomposed secondary-leading-tone seventh model with eligible fully
    # diminished and half-diminished qualities plus all four seventh inversions. This remains a
    # separate opt-in so v2.10 triad specifications retain their established feasible set.
    secondary_leading_tone_seventh_enabled: bool = False
    minimum_secondary_leading_tone_seventh_chords: int = 0

    # v2.8 adds one explicit, persistent same-mode modulation to the dominant key.
    modulation_enabled: bool = False
    modulation_destination_key: str | None = None
    modulation_boundary_beat: int | None = None

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

    phrases: tuple[PhraseSpec, ...] = ()

    seed: int = 7
    max_time_seconds: float = 15.0
    workers: int = 8

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", Mode(self.mode))
        object.__setattr__(
            self, "progression_graph", _normalize_progression_graph(self.progression_graph)
        )
        object.__setattr__(self, "tension_curve", tuple(float(x) for x in self.tension_curve))
        object.__setattr__(
            self, "harmony_vocabulary", str(self.harmony_vocabulary).strip().lower()
        )
        if self.modulation_destination_key is not None:
            destination = Key(str(self.modulation_destination_key), self.mode)
            object.__setattr__(self, "modulation_destination_key", destination.tonic)
        object.__setattr__(self, "motif_relation", str(self.motif_relation).strip().lower())
        object.__setattr__(self, "phrases", normalize_phrases(self.phrases))
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
    def expanded_harmony_enabled(self) -> bool:
        return self.harmony_vocabulary == "triads+sevenths"

    @property
    def modulation_destination(self) -> Key | None:
        if not self.modulation_enabled or self.modulation_destination_key is None:
            return None
        return Key(self.modulation_destination_key, self.mode)

    def active_key_at_beat(self, beat: int) -> Key:
        if not 0 <= beat < self.total_beats:
            raise IndexError(f"Beat {beat} is outside 0..{self.total_beats - 1}")
        boundary = self.modulation_boundary_beat
        destination = self.modulation_destination
        if (
            not self.modulation_enabled
            or boundary is None
            or destination is None
            or beat < boundary
        ):
            return self.tonal_key
        return destination

    @property
    def expected_key_contexts(self) -> tuple[Key, ...]:
        return tuple(self.active_key_at_beat(beat) for beat in range(self.total_beats))

    @property
    def context_keys(self) -> tuple[Key, ...]:
        keys = [self.tonal_key]
        destination = self.modulation_destination
        if destination is not None and destination not in keys:
            keys.append(destination)
        return tuple(keys)

    def context_pitches_in_range(self, low: int, high: int) -> tuple[int, ...]:
        """Return pitches admitted by any declared persistent local-key region."""
        pitch_classes = {
            pitch_class
            for key in self.context_keys
            for pitch_class in key.pitch_classes
        }
        return tuple(
            note for note in range(low, high + 1) if note % 12 in pitch_classes
        )

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
        if self.harmony_vocabulary not in {"triads", "triads+sevenths"}:
            raise ValueError("harmony_vocabulary must be 'triads' or 'triads+sevenths'")

        if self.modulation_enabled:
            if self.require_authentic_cadence:
                raise ValueError(
                    "modulation_enabled requires require_authentic_cadence=false because CM016 "
                    "remains the legacy global-key closure rule"
                )
            if self.total_beats < 4:
                raise ValueError("modulation requires at least four beats")
            destination = self.modulation_destination
            boundary = self.modulation_boundary_beat
            if destination is None:
                raise ValueError("modulation_enabled requires modulation_destination_key")
            if boundary is None:
                raise ValueError("modulation_enabled requires modulation_boundary_beat")
            expected = dominant_key(self.tonal_key)
            if destination != expected:
                raise ValueError(
                    "v2.8 modulation_destination_key must be the same-mode dominant key "
                    f"{expected.tonic}"
                )
            _between("modulation_boundary_beat", boundary, 2, self.total_beats - 2)
            if self.phrases:
                raise ValueError(
                    "v2.8 modulation does not yet compose with explicit phrase grammar; "
                    "leave phrases empty"
                )
        elif (
            self.modulation_destination_key is not None
            or self.modulation_boundary_beat is not None
        ):
            raise ValueError(
                "modulation destination/boundary require modulation_enabled=true"
            )

        _between("minimum_seventh_chords", self.minimum_seventh_chords, 0, self.total_beats)
        if not self.expanded_harmony_enabled and self.minimum_seventh_chords != 0:
            raise ValueError(
                "minimum_seventh_chords requires harmony_vocabulary='triads+sevenths'"
            )
        if self.expanded_harmony_enabled and self.minimum_seventh_chords > self.total_beats - 1:
            raise ValueError(
                "minimum_seventh_chords cannot include the final beat because sevenths must resolve"
            )
        if self.tonicization_enabled and not self.expanded_harmony_enabled:
            raise ValueError(
                "tonicization_enabled requires harmony_vocabulary='triads+sevenths'"
            )
        _between(
            "minimum_applied_dominants",
            self.minimum_applied_dominants,
            0,
            self.total_beats,
        )
        if not self.tonicization_enabled and self.minimum_applied_dominants != 0:
            raise ValueError("minimum_applied_dominants requires tonicization_enabled=true")
        reserved_applied = 4 if self.modulation_enabled else 1
        maximum_applied = max(0, self.total_beats - reserved_applied)
        if self.tonicization_enabled and self.minimum_applied_dominants > maximum_applied:
            raise ValueError(
                "minimum_applied_dominants exceeds beats available outside required "
                "closure/context anchors"
            )

        _between(
            "minimum_borrowed_chords",
            self.minimum_borrowed_chords,
            0,
            self.total_beats,
        )
        if not self.modal_mixture_enabled and self.minimum_borrowed_chords != 0:
            raise ValueError("minimum_borrowed_chords requires modal_mixture_enabled=true")
        reserved_cadence_beats = (
            4 if self.modulation_enabled else (2 if self.require_authentic_cadence else 1)
        )
        maximum_borrowed = max(0, self.total_beats - reserved_cadence_beats)
        if self.modal_mixture_enabled and self.minimum_borrowed_chords > maximum_borrowed:
            boundary_name = (
                "preserved cadential/context boundary"
                if self.modulation_enabled
                else "preserved global cadential boundary"
            )
            raise ValueError(
                "minimum_borrowed_chords exceeds beats available outside the " + boundary_name
            )

        _between(
            "minimum_secondary_leading_tone_chords",
            self.minimum_secondary_leading_tone_chords,
            0,
            self.total_beats,
        )
        if (
            not self.secondary_leading_tone_enabled
            and self.minimum_secondary_leading_tone_chords != 0
        ):
            raise ValueError(
                "minimum_secondary_leading_tone_chords requires "
                "secondary_leading_tone_enabled=true"
            )
        maximum_secondary = max(0, self.total_beats - reserved_cadence_beats)
        if (
            self.secondary_leading_tone_enabled
            and self.minimum_secondary_leading_tone_chords > maximum_secondary
        ):
            raise ValueError(
                "minimum_secondary_leading_tone_chords exceeds beats available outside "
                "preserved closure/context anchors"
            )

        _between(
            "minimum_secondary_leading_tone_seventh_chords",
            self.minimum_secondary_leading_tone_seventh_chords,
            0,
            self.total_beats,
        )
        if self.secondary_leading_tone_seventh_enabled and not self.expanded_harmony_enabled:
            raise ValueError(
                "secondary_leading_tone_seventh_enabled requires "
                "harmony_vocabulary='triads+sevenths'"
            )
        if (
            not self.secondary_leading_tone_seventh_enabled
            and self.minimum_secondary_leading_tone_seventh_chords != 0
        ):
            raise ValueError(
                "minimum_secondary_leading_tone_seventh_chords requires "
                "secondary_leading_tone_seventh_enabled=true"
            )
        if (
            self.secondary_leading_tone_seventh_enabled
            and self.minimum_secondary_leading_tone_seventh_chords > maximum_secondary
        ):
            raise ValueError(
                "minimum_secondary_leading_tone_seventh_chords exceeds beats available outside "
                "preserved closure/context anchors"
            )

        _ = self.tonal_key
        if self.tonicization_enabled:
            for context_key in self.context_keys:
                if not context_key.applied_dominant_targets:
                    raise ValueError(
                        f"Key context {context_key} has no applied-dominant targets compatible "
                        "with the current outer-voice contract"
                    )
        if self.modal_mixture_enabled:
            for context_key in self.context_keys:
                if not supported_borrowed_degrees(context_key):
                    raise ValueError(
                        f"Key context {context_key} has no borrowed triads compatible with the "
                        "current outer-voice contract"
                    )
        if self.secondary_leading_tone_enabled:
            for context_key in self.context_keys:
                if not supported_secondary_leading_tone_targets(
                    context_key,
                    self.progression_graph,
                ):
                    raise ValueError(
                        f"Key context {context_key} has no secondary leading-tone targets "
                        "compatible with CM005/CM006 and progression_graph"
                    )
        if self.secondary_leading_tone_seventh_enabled:
            for context_key in self.context_keys:
                if not supported_secondary_leading_tone_seventh_targets(
                    context_key,
                    self.progression_graph,
                ):
                    raise ValueError(
                        f"Key context {context_key} has no secondary leading-tone seventh "
                        "targets compatible with progression_graph and v2.12 quality policy"
                    )
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

        self._validate_phrases()

    def _validate_phrases(self) -> None:
        if not self.phrases:
            return
        ids = [phrase.id for phrase in self.phrases]
        if len(ids) != len(set(ids)):
            raise ValueError("phrase ids must be unique")
        ordered = sorted(self.phrases, key=lambda phrase: phrase.start_bar)
        for phrase in ordered:
            if phrase.end_bar > self.bars:
                raise ValueError(
                    f"phrase {phrase.id!r} extends beyond composition: "
                    f"end_bar={phrase.end_bar}, bars={self.bars}"
                )
        for left, right in pairwise(ordered):
            if left.end_bar > right.start_bar:
                raise ValueError(f"phrases {left.id!r} and {right.id!r} overlap")

        by_id = phrase_by_id(self.phrases)
        for phrase in self.phrases:
            if phrase.relation == "independent":
                if phrase.relation_steps != 0:
                    raise ValueError(
                        f"phrase {phrase.id!r}: independent relation requires relation_steps=0"
                    )
                continue
            source = by_id.get(phrase.source or "")
            if source is None:
                raise ValueError(f"phrase {phrase.id!r}: unknown source {phrase.source!r}")
            if source.start_bar >= phrase.start_bar:
                raise ValueError(f"phrase {phrase.id!r}: source must precede target phrase")
            source_steps = source.bars * self.steps_per_bar
            target_steps = phrase.bars * self.steps_per_bar
            if phrase.relation in {"repeat", "transpose"}:
                if source_steps != target_steps:
                    raise ValueError(
                        f"phrase {phrase.id!r}: {phrase.relation} requires equal phrase lengths"
                    )
                if phrase.relation_steps != 0:
                    raise ValueError(
                        f"phrase {phrase.id!r}: {phrase.relation} always spans the full phrase"
                    )
                continue
            fragment_steps = phrase.relation_steps or self.steps_per_bar
            if fragment_steps > source_steps or fragment_steps > target_steps:
                raise ValueError(
                    f"phrase {phrase.id!r}: relation fragment exceeds source/target span"
                )
            if phrase.relation == "sequence" and target_steps % fragment_steps != 0:
                raise ValueError(
                    f"phrase {phrase.id!r}: sequence target length must be divisible "
                    "by relation_steps"
                )

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
    rule_outcomes: tuple[RuleOutcome, ...] = ()
    diagnostics: tuple[RuleDiagnostic, ...] = ()

    @property
    def evaluated_rule_ids(self) -> tuple[str, ...]:
        return tuple(
            outcome.rule_id
            for outcome in self.rule_outcomes
            if outcome.status in {RuleStatus.PASS, RuleStatus.FAIL}
        )

    @property
    def not_applicable_rule_ids(self) -> tuple[str, ...]:
        return tuple(
            outcome.rule_id
            for outcome in self.rule_outcomes
            if outcome.status is RuleStatus.NOT_APPLICABLE
        )

    @property
    def blocked_rule_ids(self) -> tuple[str, ...]:
        return tuple(
            outcome.rule_id
            for outcome in self.rule_outcomes
            if outcome.status is RuleStatus.BLOCKED
        )


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
        return tuple(
            self.spec.active_key_at_beat(beat).chord_name(degree)
            for beat, degree in enumerate(self.chord_degrees)
        )

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
                "rule_outcomes": [
                    outcome.to_dict() for outcome in self.validation.rule_outcomes
                ],
                "diagnostics": [
                    diagnostic.to_dict() for diagnostic in self.validation.diagnostics
                ],
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
            tuple(
                RuleOutcome.from_mapping(item)
                for item in raw_validation.get("rule_outcomes", ())
            ),
            tuple(
                RuleDiagnostic.from_mapping(item)
                for item in raw_validation.get("diagnostics", ())
            ),
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
