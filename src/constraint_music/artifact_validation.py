"""Fail-closed validation for serialized certification artifacts.

This module deliberately validates the wire representation before any result
object is reconstructed.  Keeping this boundary separate prevents permissive
Python conversions (``int(True)``, numeric strings, partial SATB payloads) from
silently changing the certification profile.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import fields
from typing import Any, Final

from .models import GenerationSpec

CURRENT_SCHEMA_VERSION: Final = "2.13"
SUPPORTED_SCHEMA_VERSIONS: Final = frozenset({"2.12", CURRENT_SCHEMA_VERSION})


class ArtifactShapeError(ValueError):
    """Raised when an artifact cannot safely enter semantic verification."""

    def __init__(self, issues: Sequence[str]) -> None:
        self.issues = tuple(issues)
        super().__init__("artifact shape is invalid: " + "; ".join(self.issues))


_INTEGER_SPEC_FIELDS: Final = {
    "bars",
    "beats_per_bar",
    "subdivisions_per_beat",
    "tempo_bpm",
    "melody_low",
    "melody_high",
    "bass_low",
    "bass_high",
    "max_melody_leap",
    "max_bass_leap",
    "max_repeated_notes",
    "minimum_seventh_chords",
    "minimum_applied_dominants",
    "minimum_borrowed_chords",
    "minimum_secondary_leading_tone_chords",
    "minimum_secondary_leading_tone_seventh_chords",
    "modulation_boundary_beat",
    "min_onsets_per_bar",
    "max_onsets_per_bar",
    "min_rests_per_bar",
    "max_rests_per_bar",
    "min_ties_per_bar",
    "max_ties_per_bar",
    "max_consecutive_rests",
    "max_tie_steps",
    "motif_source_bar",
    "motif_target_bar",
    "motif_length_steps",
    "motif_transpose_semitones",
    "seed",
    "workers",
}

_BOOLEAN_SPEC_FIELDS: Final = {
    "require_authentic_cadence",
    "resolve_leading_tone",
    "avoid_parallel_perfects",
    "tonicization_enabled",
    "modal_mixture_enabled",
    "secondary_leading_tone_enabled",
    "secondary_leading_tone_seventh_enabled",
    "modulation_enabled",
    "rhythm_enabled",
    "require_bar_downbeat_onset",
}


def validate_artifact_payload(
    payload: Mapping[str, Any], *, require_current: bool = True
) -> GenerationSpec:
    """Validate a complete SATB artifact and return its normalized specification.

    Validation is aggregate: callers receive every safe-to-detect structural
    defect in one deterministic exception.  Semantic checking starts only after
    this function succeeds.
    """

    issues: list[str] = []
    schema = payload.get("schema_version")
    if not isinstance(schema, str):
        issues.append("schema_version must be a string")
    elif schema not in SUPPORTED_SCHEMA_VERSIONS:
        issues.append(f"unsupported schema_version {schema!r}")
    elif require_current and schema != CURRENT_SCHEMA_VERSION:
        issues.append(
            f"strict certification requires schema {CURRENT_SCHEMA_VERSION!r}, got {schema!r}"
        )

    raw_spec = _mapping(payload, "spec", issues)
    raw_solver = _mapping(payload, "solver", issues)
    raw_validation = _mapping(payload, "validation", issues)
    raw_music = _mapping(payload, "music", issues)
    _mapping(payload, "search", issues)
    _mapping(payload, "provenance", issues)

    spec: GenerationSpec | None = None
    if raw_spec is not None:
        _validate_spec_wire_types(raw_spec, issues)
        required_spec_fields = {field.name for field in fields(GenerationSpec)}
        missing = sorted(required_spec_fields - set(raw_spec))
        if missing:
            issues.append("spec is missing fields: " + ", ".join(missing))
        try:
            spec = GenerationSpec.from_mapping(raw_spec)
        except (TypeError, ValueError) as exc:
            issues.append(f"spec is invalid: {exc}")

    if raw_solver is not None:
        _finite_number(raw_solver, "objective", "solver.objective", issues)
        _finite_number(raw_solver, "wall_time_seconds", "solver.wall_time_seconds", issues)
        if not isinstance(raw_solver.get("status"), str):
            issues.append("solver.status must be a string")

    if raw_validation is not None:
        if type(raw_validation.get("valid")) is not bool:
            issues.append("validation.valid must be a boolean")
        for key in ("issues", "checked_rules", "failed_rules"):
            _string_array(raw_validation, key, f"validation.{key}", issues)

    if spec is not None and raw_music is not None:
        beats = spec.total_beats
        steps = spec.total_steps
        for key in ("melody_midi",):
            _integer_array(raw_music, key, steps, f"music.{key}", issues)
        for key in (
            "bass_midi",
            "chord_degrees",
            "target_tension",
            "actual_tension",
            "soprano_midi",
            "alto_midi",
            "tenor_midi",
            "chord_inversions",
        ):
            _integer_array(raw_music, key, beats, f"music.{key}", issues)
        _string_array(raw_music, "rhythm", "music.rhythm", issues, expected=steps)
        _string_array(raw_music, "chord_kinds", "music.chord_kinds", issues, expected=beats)
        _nullable_integer_array(
            raw_music,
            "tonicization_targets",
            beats,
            "music.tonicization_targets",
            issues,
        )
        _nullable_string_array(
            raw_music,
            "modal_sources",
            beats,
            "music.modal_sources",
            issues,
        )
        if spec.modulation_enabled:
            contexts = _array(raw_music, "key_contexts", "music.key_contexts", issues)
            if contexts is not None:
                if len(contexts) != beats:
                    issues.append(
                        "music.key_contexts must contain exactly "
                        f"{beats} entries, got {len(contexts)}"
                    )
                for index, context in enumerate(contexts):
                    if not isinstance(context, Mapping):
                        issues.append(f"music.key_contexts[{index}] must be an object")
                        continue
                    if not isinstance(context.get("tonic"), str) or not isinstance(
                        context.get("mode"), str
                    ):
                        issues.append(
                            f"music.key_contexts[{index}] requires string tonic and mode"
                        )

    if issues:
        raise ArtifactShapeError(issues)
    assert spec is not None
    return spec


def _mapping(
    payload: Mapping[str, Any], key: str, issues: list[str]
) -> Mapping[str, Any] | None:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        issues.append(f"{key} must be an object")
        return None
    return value


def _array(
    mapping: Mapping[str, Any], key: str, label: str, issues: list[str]
) -> Sequence[Any] | None:
    value = mapping.get(key)
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        issues.append(f"{label} must be an array")
        return None
    return value


def _integer_array(
    mapping: Mapping[str, Any],
    key: str,
    expected: int,
    label: str,
    issues: list[str],
) -> None:
    values = _array(mapping, key, label, issues)
    if values is None:
        return
    if len(values) != expected:
        issues.append(f"{label} must contain exactly {expected} entries, got {len(values)}")
    for index, value in enumerate(values):
        if type(value) is not int:
            issues.append(f"{label}[{index}] must be an integer (booleans/strings are forbidden)")


def _nullable_integer_array(
    mapping: Mapping[str, Any],
    key: str,
    expected: int,
    label: str,
    issues: list[str],
) -> None:
    values = _array(mapping, key, label, issues)
    if values is None:
        return
    if len(values) != expected:
        issues.append(f"{label} must contain exactly {expected} entries, got {len(values)}")
    for index, value in enumerate(values):
        if value is not None and type(value) is not int:
            issues.append(f"{label}[{index}] must be an integer or null")


def _string_array(
    mapping: Mapping[str, Any],
    key: str,
    label: str,
    issues: list[str],
    *,
    expected: int | None = None,
) -> None:
    values = _array(mapping, key, label, issues)
    if values is None:
        return
    if expected is not None and len(values) != expected:
        issues.append(f"{label} must contain exactly {expected} entries, got {len(values)}")
    for index, value in enumerate(values):
        if not isinstance(value, str):
            issues.append(f"{label}[{index}] must be a string")


def _nullable_string_array(
    mapping: Mapping[str, Any],
    key: str,
    expected: int,
    label: str,
    issues: list[str],
) -> None:
    values = _array(mapping, key, label, issues)
    if values is None:
        return
    if len(values) != expected:
        issues.append(f"{label} must contain exactly {expected} entries, got {len(values)}")
    for index, value in enumerate(values):
        if value is not None and not isinstance(value, str):
            issues.append(f"{label}[{index}] must be a string or null")


def _finite_number(
    mapping: Mapping[str, Any], key: str, label: str, issues: list[str]
) -> None:
    value = mapping.get(key)
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
    ):
        issues.append(f"{label} must be a finite number (booleans/strings are forbidden)")


def _validate_spec_wire_types(spec: Mapping[str, Any], issues: list[str]) -> None:
    for key in _INTEGER_SPEC_FIELDS:
        if key in spec and spec[key] is not None and type(spec[key]) is not int:
            issues.append(f"spec.{key} must be an integer")
    for key in _BOOLEAN_SPEC_FIELDS:
        if key in spec and type(spec[key]) is not bool:
            issues.append(f"spec.{key} must be a boolean")
    value = spec.get("max_time_seconds")
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
    ):
        issues.append("spec.max_time_seconds must be a finite number")
    tension = spec.get("tension_curve")
    if isinstance(tension, Sequence) and not isinstance(tension, (str, bytes)):
        for index, item in enumerate(tension):
            if (
                not isinstance(item, (int, float))
                or isinstance(item, bool)
                or not math.isfinite(float(item))
            ):
                issues.append(f"spec.tension_curve[{index}] must be a finite number")
