from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import cache
from itertools import pairwise, product
from typing import Any

from ._optional_cp import cp_model
from .modal_mixture import (
    NO_MODAL_SOURCE,
    ModalSource,
    borrowed_chord_name,
    borrowed_seventh_chord_name,
    borrowed_triad_pitch_classes,
    canonical_modal_source,
    supported_borrowed_degrees,
)
from .models import GenerationResult, GenerationSpec
from .secondary_leading_tone import (
    secondary_leading_tone_name,
    secondary_leading_tone_seventh_name,
    secondary_leading_tone_seventh_pitch_class_variants,
    secondary_leading_tone_seventh_support_degree,
    secondary_leading_tone_support_degree,
    secondary_leading_tone_triad_pitch_classes,
)
from .semantic_dispatch import (
    ContextualHarmonyFamily,
    SemanticDispatch,
    has_family,
)
from .theory import (
    NO_TONICIZATION_TARGET,
    ChordKind,
    Key,
    is_parallel_perfect,
    midi_note_name,
)

ALTO_LOW = 55
ALTO_HIGH = 74
TENOR_LOW = 48
TENOR_HIGH = 67
MAX_UPPER_SPACING = 12


@dataclass(frozen=True, slots=True)
class SatbGenerationResult(GenerationResult):
    soprano: tuple[int, ...] = ()
    alto: tuple[int, ...] = ()
    tenor: tuple[int, ...] = ()
    chord_kinds: tuple[ChordKind, ...] = ()
    chord_inversions: tuple[int, ...] = ()
    tonicization_targets: tuple[int | None, ...] = ()
    modal_sources: tuple[ModalSource | None, ...] = ()

    @property
    def soprano_names(self) -> tuple[str, ...]:
        return tuple(midi_note_name(note) for note in self.soprano)

    @property
    def alto_names(self) -> tuple[str, ...]:
        return tuple(midi_note_name(note) for note in self.alto)

    @property
    def tenor_names(self) -> tuple[str, ...]:
        return tuple(midi_note_name(note) for note in self.tenor)

    @property
    def chord_form_names(self) -> tuple[str, ...]:
        beat_count = len(self.chord_degrees)
        if not (
            len(self.chord_kinds)
            == len(self.chord_inversions)
            == beat_count
            == len(self.soprano)
            == len(self.alto)
            == len(self.tenor)
            == len(self.bass)
        ):
            return ()
        targets = (
            self.tonicization_targets
            if self.tonicization_targets
            else (None,) * beat_count
        )
        sources = self.modal_sources if self.modal_sources else (None,) * beat_count
        if not (len(targets) == len(sources) == beat_count):
            return ()

        names: list[str] = []
        try:
            for beat, (degree, raw_kind, inversion, target, raw_source) in enumerate(
                zip(
                    self.chord_degrees,
                    self.chord_kinds,
                    self.chord_inversions,
                    targets,
                    sources,
                    strict=True,
                )
            ):
                key = self.spec.active_key_at_beat(beat)
                kind = ChordKind.parse(raw_kind)
                source = None if raw_source is None else ModalSource.parse(raw_source)
                pcs = (
                    self.soprano[beat] % 12,
                    self.alto[beat] % 12,
                    self.tenor[beat] % 12,
                    self.bass[beat] % 12,
                )
                if target is not None and source is not None:
                    return ()
                if target is not None:
                    if kind is ChordKind.SEVENTH:
                        is_applied = False
                        if (
                            self.spec.tonicization_enabled
                            and target in key.applied_dominant_targets
                            and degree == key.applied_dominant_root_degree(target)
                            and 0 <= inversion <= 2
                        ):
                            applied = key.applied_dominant_seventh_pitch_classes(target)
                            is_applied = (
                                set(pcs) == set(applied)
                                and len(set(pcs)) == 4
                                and self.bass[beat] % 12 == applied[inversion]
                            )
                        if is_applied:
                            names.append(key.applied_dominant_name(target, inversion))
                            continue
                        if not self.spec.secondary_leading_tone_seventh_enabled:
                            return ()
                        matched = False
                        variants = secondary_leading_tone_seventh_pitch_class_variants(
                            key,
                            target,
                        )
                        for quality, expected in variants:
                            try:
                                support = secondary_leading_tone_seventh_support_degree(
                                    key,
                                    target,
                                    self.spec.progression_graph,
                                    quality,
                                )
                            except ValueError:
                                continue
                            if (
                                degree == support
                                and set(pcs) == set(expected)
                                and len(set(pcs)) == 4
                                and 0 <= inversion <= 3
                                and self.bass[beat] % 12 == expected[inversion]
                            ):
                                names.append(
                                    secondary_leading_tone_seventh_name(
                                        key,
                                        target,
                                        inversion,
                                        quality,
                                    )
                                )
                                matched = True
                                break
                        if not matched:
                            return ()
                        continue

                    if kind is ChordKind.TRIAD and self.spec.secondary_leading_tone_enabled:
                        expected_triad = secondary_leading_tone_triad_pitch_classes(
                            key,
                            target,
                        )
                        support = secondary_leading_tone_support_degree(
                            key,
                            target,
                            self.spec.progression_graph,
                        )
                        if (
                            degree == support
                            and set(pcs) == set(expected_triad)
                            and 0 <= inversion <= 2
                            and self.bass[beat] % 12 == expected_triad[inversion]
                        ):
                            names.append(secondary_leading_tone_name(key, target, inversion))
                            continue
                    return ()

                if source is not None:
                    if kind is ChordKind.TRIAD:
                        names.append(borrowed_chord_name(key, degree, source, inversion))
                    elif kind is ChordKind.SEVENTH:
                        names.append(
                            borrowed_seventh_chord_name(key, degree, source, inversion)
                        )
                    else:
                        return ()
                    continue

                names.append(key.chord_form_name(degree, kind, inversion))
        except (IndexError, ValueError):
            return ()
        return tuple(names)

    def to_dict(self) -> dict[str, Any]:
        payload = GenerationResult.to_dict(self)
        music = payload["music"]
        music["soprano_midi"] = list(self.soprano)
        music["soprano_names"] = list(self.soprano_names)
        music["alto_midi"] = list(self.alto)
        music["alto_names"] = list(self.alto_names)
        music["tenor_midi"] = list(self.tenor)
        music["tenor_names"] = list(self.tenor_names)
        music["chord_kinds"] = [ChordKind.parse(kind).label for kind in self.chord_kinds]
        music["chord_inversions"] = list(self.chord_inversions)
        music["tonicization_targets"] = list(self.tonicization_targets)
        music["modal_sources"] = [
            None if source is None else ModalSource.parse(source).label
            for source in self.modal_sources
        ]
        if self.chord_form_names:
            music["chord_form_names"] = list(self.chord_form_names)
        return payload


@dataclass(slots=True)
class SatbVariables:
    soprano: list[cp_model.IntVar]
    alto: list[cp_model.IntVar]
    tenor: list[cp_model.IntVar]
    chord_kind: list[cp_model.IntVar]
    chord_inversion: list[cp_model.IntVar]
    tonicization_target: list[cp_model.IntVar]
    modal_source: list[cp_model.IntVar]


def result_from_dict(payload: Mapping[str, Any]) -> GenerationResult:
    base = GenerationResult.from_dict(payload)
    raw_music = payload.get("music")
    if not isinstance(raw_music, Mapping) or "alto_midi" not in raw_music:
        return base

    def values(key: str) -> tuple[object, ...]:
        value = raw_music.get(key, ())
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
            raise ValueError(f"Result JSON music.{key} must be an array")
        return tuple(value)

    def integers(key: str) -> tuple[int, ...]:
        parsed: list[int] = []
        for item in values(key):
            if not isinstance(item, (int, str)):
                raise ValueError(f"Result JSON music.{key} must contain integers")
            try:
                parsed.append(int(item))
            except ValueError as exc:
                raise ValueError(f"Result JSON music.{key} must contain integers") from exc
        return tuple(parsed)

    def optional_integers(key: str) -> tuple[int | None, ...]:
        parsed: list[int | None] = []
        for item in values(key):
            if item is None:
                parsed.append(None)
                continue
            if not isinstance(item, (int, str)):
                raise ValueError(f"Result JSON music.{key} must contain integers or null")
            try:
                parsed.append(int(item))
            except ValueError as exc:
                raise ValueError(
                    f"Result JSON music.{key} must contain integers or null"
                ) from exc
        return tuple(parsed)

    def optional_sources(key: str) -> tuple[ModalSource | None, ...]:
        parsed: list[ModalSource | None] = []
        for item in values(key):
            if item is None:
                parsed.append(None)
            else:
                parsed.append(ModalSource.parse(item))
        return tuple(parsed)

    raw_kinds = values("chord_kinds") if "chord_kinds" in raw_music else ()
    raw_inversions = integers("chord_inversions") if "chord_inversions" in raw_music else ()
    raw_targets = (
        optional_integers("tonicization_targets")
        if "tonicization_targets" in raw_music
        else ()
    )
    raw_sources = optional_sources("modal_sources") if "modal_sources" in raw_music else ()
    return SatbGenerationResult(
        spec=base.spec,
        melody=base.melody,
        bass=base.bass,
        chord_degrees=base.chord_degrees,
        target_tension=base.target_tension,
        actual_tension=base.actual_tension,
        objective_value=base.objective_value,
        solver_status=base.solver_status,
        wall_time_seconds=base.wall_time_seconds,
        rhythm=base.rhythm,
        validation=base.validation,
        soprano=integers("soprano_midi"),
        alto=integers("alto_midi"),
        tenor=integers("tenor_midi"),
        chord_kinds=tuple(ChordKind.parse(item) for item in raw_kinds),
        chord_inversions=raw_inversions,
        tonicization_targets=raw_targets,
        modal_sources=raw_sources,
    )


def add_satb_constraints(
    model: cp_model.CpModel,
    spec: GenerationSpec,
    chord: list[cp_model.IntVar],
    melody_note: list[cp_model.IntVar],
    bass_note: list[cp_model.IntVar],
) -> SatbVariables:
    key = spec.tonal_key
    soprano_domain = key.pitches_in_range(spec.melody_low, spec.melody_high)
    inner_pitch_classes = set(key.pitch_classes)
    if spec.tonicization_enabled:
        for target_degree in key.applied_dominant_targets:
            inner_pitch_classes.update(
                key.applied_dominant_seventh_pitch_classes(target_degree)
            )
    if spec.modal_mixture_enabled:
        source = canonical_modal_source(key)
        for degree in supported_borrowed_degrees(key):
            inner_pitch_classes.update(borrowed_triad_pitch_classes(key, degree, source))
    alto_domain = _pitches_for_pitch_classes(ALTO_LOW, ALTO_HIGH, inner_pitch_classes)
    tenor_domain = _pitches_for_pitch_classes(TENOR_LOW, TENOR_HIGH, inner_pitch_classes)
    bass_domain = key.pitches_in_range(spec.bass_low, spec.bass_high)

    if not alto_domain or not tenor_domain:
        raise ValueError("SATB inner-voice ranges contain no pitches in the selected harmony")

    soprano = [
        model.new_int_var(spec.melody_low, spec.melody_high, f"soprano_{beat}")
        for beat in range(spec.total_beats)
    ]
    alto = [
        model.new_int_var(ALTO_LOW, ALTO_HIGH, f"alto_{beat}")
        for beat in range(spec.total_beats)
    ]
    tenor = [
        model.new_int_var(TENOR_LOW, TENOR_HIGH, f"tenor_{beat}")
        for beat in range(spec.total_beats)
    ]
    chord_kind = [
        model.new_bool_var(f"chord_kind_{beat}") for beat in range(spec.total_beats)
    ]
    chord_inversion = [
        model.new_int_var(0, 2, f"chord_inversion_{beat}")
        for beat in range(spec.total_beats)
    ]
    tonicization_target = [
        model.new_int_var(0, NO_TONICIZATION_TARGET, f"tonicization_target_{beat}")
        for beat in range(spec.total_beats)
    ]
    modal_source = [
        model.new_int_var(
            NO_MODAL_SOURCE,
            int(ModalSource.PARALLEL_NATURAL_MINOR),
            f"modal_source_{beat}",
        )
        for beat in range(spec.total_beats)
    ]

    if spec.expanded_harmony_enabled:
        if spec.minimum_seventh_chords:
            model.add(sum(chord_kind) >= spec.minimum_seventh_chords)
        model.add(chord_kind[-1] == int(ChordKind.TRIAD))
    else:
        for kind in chord_kind:
            model.add(kind == int(ChordKind.TRIAD))

    applied_flags: list[cp_model.IntVar] = []
    if spec.tonicization_enabled:
        for beat, target in enumerate(tonicization_target):
            applied = model.new_bool_var(f"applied_dominant_{beat}")
            model.add(target != NO_TONICIZATION_TARGET).only_enforce_if(applied)
            model.add(target == NO_TONICIZATION_TARGET).only_enforce_if(applied.negated())
            applied_flags.append(applied)
        if spec.minimum_applied_dominants:
            model.add(sum(applied_flags) >= spec.minimum_applied_dominants)
        model.add(tonicization_target[-1] == NO_TONICIZATION_TARGET)
    else:
        for target in tonicization_target:
            model.add(target == NO_TONICIZATION_TARGET)

    borrowed_flags: list[cp_model.IntVar] = []
    if spec.modal_mixture_enabled:
        canonical_source = int(canonical_modal_source(key))
        for beat, source_var in enumerate(modal_source):
            model.add_allowed_assignments(
                [source_var],
                [(NO_MODAL_SOURCE,), (canonical_source,)],
            )
            borrowed = model.new_bool_var(f"borrowed_chord_{beat}")
            model.add(source_var == canonical_source).only_enforce_if(borrowed)
            model.add(source_var == NO_MODAL_SOURCE).only_enforce_if(borrowed.negated())
            borrowed_flags.append(borrowed)
        if spec.minimum_borrowed_chords:
            model.add(sum(borrowed_flags) >= spec.minimum_borrowed_chords)
        model.add(modal_source[-1] == NO_MODAL_SOURCE)
        if spec.require_authentic_cadence and spec.total_beats >= 2:
            model.add(modal_source[-2] == NO_MODAL_SOURCE)
    else:
        for source_var in modal_source:
            model.add(source_var == NO_MODAL_SOURCE)

    chord_rows = _satb_chord_rows(
        key,
        spec.expanded_harmony_enabled,
        spec.tonicization_enabled,
        spec.modal_mixture_enabled,
    )
    pitch_classes: list[list[cp_model.IntVar]] = []

    for beat in range(spec.total_beats):
        strong_step = beat * spec.subdivisions_per_beat
        model.add(soprano[beat] == melody_note[strong_step])
        model.add_allowed_assignments([alto[beat]], [(note,) for note in alto_domain])
        model.add_allowed_assignments([tenor[beat]], [(note,) for note in tenor_domain])
        model.add(bass_note[beat] < tenor[beat])
        model.add(tenor[beat] < alto[beat])
        model.add(alto[beat] < soprano[beat])
        model.add(soprano[beat] - alto[beat] <= MAX_UPPER_SPACING)
        model.add(alto[beat] - tenor[beat] <= MAX_UPPER_SPACING)

        pcs = [model.new_int_var(0, 11, f"satb_pc_{beat}_{index}") for index in range(4)]
        pitch_classes.append(pcs)
        voice_notes = (soprano[beat], alto[beat], tenor[beat], bass_note[beat])
        for pc, note_var in zip(pcs, voice_notes, strict=True):
            model.add_modulo_equality(pc, note_var, 12)
        model.add_allowed_assignments(
            [
                chord[beat],
                chord_kind[beat],
                chord_inversion[beat],
                tonicization_target[beat],
                modal_source[beat],
                *pcs,
            ],
            chord_rows,
        )

    if spec.avoid_parallel_perfects:
        pair_domains = (
            (soprano, alto, soprano_domain, alto_domain),
            (soprano, tenor, soprano_domain, tenor_domain),
            (alto, tenor, alto_domain, tenor_domain),
            (alto, bass_note, alto_domain, bass_domain),
            (tenor, bass_note, tenor_domain, bass_domain),
        )
        for left_voice, right_voice, left_domain, right_domain in pair_domains:
            forbidden = _parallel_rows(left_domain, right_domain)
            for beat in range(spec.total_beats - 1):
                model.add_forbidden_assignments(
                    [
                        left_voice[beat],
                        right_voice[beat],
                        left_voice[beat + 1],
                        right_voice[beat + 1],
                    ],
                    forbidden,
                )

    if spec.resolve_leading_tone:
        resolution_voices: tuple[
            tuple[list[cp_model.IntVar], tuple[int, ...]], ...
        ] = (
            (alto, alto_domain),
            (tenor, tenor_domain),
        )
        for voice_vars, domain in resolution_voices:
            allowed = [
                (left_note, right_note)
                for left_note in domain
                for right_note in domain
                if left_note % 12 != key.leading_tone_pc or right_note == left_note + 1
            ]
            for left_var, right_var in pairwise(voice_vars):
                model.add_allowed_assignments([left_var, right_var], allowed)

    if spec.expanded_harmony_enabled:
        _add_expanded_harmony_motion_constraints(
            model,
            key,
            spec.tonicization_enabled,
            chord,
            chord_kind,
            tonicization_target,
            pitch_classes,
            soprano,
            alto,
            tenor,
            bass_note,
        )

    return SatbVariables(
        soprano=soprano,
        alto=alto,
        tenor=tenor,
        chord_kind=chord_kind,
        chord_inversion=chord_inversion,
        tonicization_target=tonicization_target,
        modal_source=modal_source,
    )


def _add_expanded_harmony_motion_constraints(
    model: cp_model.CpModel,
    key: Key,
    tonicization_enabled: bool,
    chord: list[cp_model.IntVar],
    chord_kind: list[cp_model.IntVar],
    tonicization_target: list[cp_model.IntVar],
    pitch_classes: list[list[cp_model.IntVar]],
    soprano: list[cp_model.IntVar],
    alto: list[cp_model.IntVar],
    tenor: list[cp_model.IntVar],
    bass: list[cp_model.IntVar],
) -> None:
    seventh_rows = _chordal_seventh_flag_rows(key, tonicization_enabled)
    global_dominant_rows = _global_dominant_seventh_flag_rows()
    leading_rows = _dominant_leading_flag_rows(key, tonicization_enabled)
    voices = (soprano, alto, tenor, bass)

    for beat in range(len(chord) - 1):
        target = tonicization_target[beat]
        applied = model.new_bool_var(f"motion_applied_dominant_{beat}")
        model.add(target != NO_TONICIZATION_TARGET).only_enforce_if(applied)
        model.add(target == NO_TONICIZATION_TARGET).only_enforce_if(applied.negated())
        model.add(chord[beat + 1] == target).only_enforce_if(applied)
        model.add(tonicization_target[beat + 1] == NO_TONICIZATION_TARGET).only_enforce_if(
            applied
        )

        global_dominant = model.new_bool_var(f"global_dominant_seventh_{beat}")
        model.add_allowed_assignments(
            [chord[beat], chord_kind[beat], target, global_dominant],
            global_dominant_rows,
        )
        model.add(chord[beat + 1] == 0).only_enforce_if(global_dominant)

        for voice_index, voice in enumerate(voices):
            current_pc = pitch_classes[beat][voice_index]
            carries_seventh = model.new_bool_var(f"chordal_seventh_{beat}_{voice_index}")
            model.add_allowed_assignments(
                [
                    chord[beat],
                    chord_kind[beat],
                    target,
                    current_pc,
                    carries_seventh,
                ],
                seventh_rows,
            )
            model.add(voice[beat + 1] <= voice[beat] - 1).only_enforce_if(carries_seventh)
            model.add(voice[beat + 1] >= voice[beat] - 2).only_enforce_if(carries_seventh)

            carries_dominant_leading = model.new_bool_var(
                f"dominant_leading_{beat}_{voice_index}"
            )
            model.add_allowed_assignments(
                [
                    chord[beat],
                    chord_kind[beat],
                    target,
                    current_pc,
                    carries_dominant_leading,
                ],
                leading_rows,
            )
            model.add(voice[beat + 1] == voice[beat] + 1).only_enforce_if(
                carries_dominant_leading
            )


def satb_verification_issues(
    result: GenerationResult,
    *,
    semantic_dispatch: SemanticDispatch | None = None,
) -> tuple[tuple[str, str], ...]:
    if not isinstance(result, SatbGenerationResult):
        return ()
    spec = result.spec
    key = spec.tonal_key
    soprano, alto, tenor, bass = result.soprano, result.alto, result.tenor, result.bass
    issues: list[tuple[str, str]] = []

    if not all(
        len(voice) == spec.total_beats for voice in (soprano, alto, tenor, bass)
    ):
        issues.append(("CM027", "SATB voices must contain exactly one note per beat"))
        return tuple(issues)
    for beat, note in enumerate(soprano):
        strong_step = beat * spec.subdivisions_per_beat
        if strong_step >= len(result.melody) or note != result.melody[strong_step]:
            issues.append(
                ("CM027", f"Beat {beat}: soprano is not anchored to the strong-step melody")
            )

    metadata_present = bool(result.chord_kinds or result.chord_inversions)
    metadata_valid = False
    kinds: tuple[ChordKind, ...] = (ChordKind.TRIAD,) * spec.total_beats
    inversions: tuple[int, ...] = ()

    if metadata_present:
        if not (
            len(result.chord_kinds)
            == len(result.chord_inversions)
            == spec.total_beats
        ):
            issues.append(
                ("CM033", "Harmonic kind/inversion arrays must contain one value per beat")
            )
        else:
            try:
                kinds = tuple(ChordKind.parse(item) for item in result.chord_kinds)
            except ValueError:
                issues.append(("CM033", "Harmonic form contains an unknown chord kind"))
            else:
                inversions = tuple(int(item) for item in result.chord_inversions)
                metadata_valid = True
                if any(
                    not 0 <= inversion <= 2
                    and not (
                        inversion == 3
                        and has_family(
                            semantic_dispatch,
                            beat,
                            ContextualHarmonyFamily.SECONDARY_LEADING_TONE_SEVENTH,
                        )
                    )
                    for beat, inversion in enumerate(inversions)
                ):
                    issues.append(("CM033", "Chord inversions must be encoded in 0..2"))
                if not spec.expanded_harmony_enabled and any(
                    kind is ChordKind.SEVENTH for kind in kinds
                ):
                    issues.append(
                        ("CM033", "Seventh chords require harmony_vocabulary='triads+sevenths'")
                    )
                if sum(kind is ChordKind.SEVENTH for kind in kinds) < spec.minimum_seventh_chords:
                    issues.append(
                        ("CM033", "Serialized harmony does not meet minimum_seventh_chords")
                    )
    elif spec.expanded_harmony_enabled:
        issues.append(("CM033", "Expanded harmony requires explicit chord kind/inversion metadata"))

    targets_present = bool(result.tonicization_targets)
    targets: tuple[int | None, ...] = (None,) * spec.total_beats
    context_valid = False
    if targets_present:
        if len(result.tonicization_targets) != spec.total_beats:
            issues.append(
                ("CM037", "Tonicization target metadata must contain one value per beat")
            )
        else:
            targets = result.tonicization_targets
            context_valid = True
    elif spec.tonicization_enabled:
        issues.append(("CM037", "Enabled tonicization requires explicit target metadata"))
    else:
        context_valid = True

    supported_targets = set(key.applied_dominant_targets)
    applied_count = 0
    if context_valid:
        for beat, target in enumerate(targets):
            if target is None:
                continue
            if has_family(
                semantic_dispatch,
                beat,
                ContextualHarmonyFamily.SECONDARY_LEADING_TONE_TRIAD,
                ContextualHarmonyFamily.SECONDARY_LEADING_TONE_SEVENTH,
            ):
                continue
            applied_count += 1
            if not spec.tonicization_enabled:
                issues.append(("CM037", f"Beat {beat}: tonicization is not enabled by the spec"))
                continue
            if target not in supported_targets:
                issues.append(
                    ("CM037", f"Beat {beat}: unsupported tonicization target degree {target}"))
                continue
            if (
                metadata_valid
                and kinds[beat] is not ChordKind.SEVENTH
                and not has_family(
                    semantic_dispatch,
                    beat,
                    ContextualHarmonyFamily.SECONDARY_LEADING_TONE_TRIAD,
                )
            ):
                issues.append(("CM037", f"Beat {beat}: applied dominant must be a seventh chord"))
        if applied_count < spec.minimum_applied_dominants:
            issues.append(
                ("CM037", "Serialized harmony does not meet minimum_applied_dominants")
            )

    source_metadata_present = bool(result.modal_sources)
    sources: tuple[ModalSource | None, ...] = (None,) * spec.total_beats
    source_context_valid = False
    if source_metadata_present:
        if len(result.modal_sources) != spec.total_beats:
            issues.append(("CM041", "Modal source metadata must contain one value per beat"))
        else:
            try:
                sources = tuple(
                    None if source is None else ModalSource.parse(source)
                    for source in result.modal_sources
                )
            except ValueError:
                issues.append(("CM041", "Modal source metadata contains an unknown source"))
            else:
                source_context_valid = True
    elif spec.modal_mixture_enabled:
        issues.append(("CM041", "Enabled modal mixture requires explicit source metadata"))
    else:
        source_context_valid = True

    canonical_source = canonical_modal_source(key)
    supported_borrowed = set(supported_borrowed_degrees(key))
    borrowed_count = 0
    if source_context_valid:
        for beat, source in enumerate(sources):
            if source is None:
                continue
            borrowed_count += 1
            if not spec.modal_mixture_enabled:
                issues.append(("CM041", f"Beat {beat}: modal mixture is not enabled by the spec"))
                continue
            if source is not canonical_source:
                issues.append(
                    (
                        "CM041",
                        f"Beat {beat}: modal source {source.label} is not canonical for {key}",
                    )
                )
                continue
            if beat == spec.total_beats - 1:
                issues.append(("CM041", f"Beat {beat}: final chord must remain in global context"))
            if spec.require_authentic_cadence and beat == spec.total_beats - 2:
                issues.append(
                    ("CM041", f"Beat {beat}: cadential dominant-function chord must remain global")
                )
            if (
                beat < len(result.chord_degrees)
                and result.chord_degrees[beat] not in supported_borrowed
            ):
                issues.append(
                    (
                        "CM041",
                        f"Beat {beat}: degree {result.chord_degrees[beat]} is not borrowable",
                    )
                )
            if context_valid and targets[beat] is not None:
                issues.append(("CM041", f"Beat {beat}: borrowing and tonicization cannot coexist"))
            if (
                metadata_valid
                and kinds[beat] is not ChordKind.TRIAD
                and not has_family(
                    semantic_dispatch,
                    beat,
                    ContextualHarmonyFamily.BORROWED_SEVENTH,
                )
            ):
                issues.append(("CM041", f"Beat {beat}: v2.7 borrowed harmony must be triadic"))
        if borrowed_count < spec.minimum_borrowed_chords:
            issues.append(
                ("CM041", "Serialized harmony does not meet minimum_borrowed_chords")
            )

    for beat, (sv, av, tv, bv) in enumerate(
        zip(soprano, alto, tenor, bass, strict=True)
    ):
        issues.extend(
            satb_register_verification_issues(
                (sv, av, tv, bv),
                melody_low=spec.melody_low,
                melody_high=spec.melody_high,
                beat=beat,
            )
        )

        if beat >= len(result.chord_degrees) or not 0 <= result.chord_degrees[beat] <= 6:
            continue
        degree = result.chord_degrees[beat]
        pcs = (sv % 12, av % 12, tv % 12, bv % 12)
        kind = kinds[beat] if metadata_valid else ChordKind.TRIAD
        target = targets[beat] if context_valid else None
        source = sources[beat] if source_context_valid else None

        if target is not None:
            if has_family(
                semantic_dispatch,
                beat,
                ContextualHarmonyFamily.SECONDARY_LEADING_TONE_TRIAD,
                ContextualHarmonyFamily.SECONDARY_LEADING_TONE_SEVENTH,
            ):
                continue
            if target not in supported_targets or not metadata_valid:
                continue
            expected_degree = key.applied_dominant_root_degree(target)
            applied_pcs = key.applied_dominant_seventh_pitch_classes(target)
            if degree != expected_degree:
                issues.append(
                    (
                        "CM038",
                        f"Beat {beat}: applied-dominant root degree does not match target {target}",
                    )
                )
            if kind is not ChordKind.SEVENTH or set(pcs) != set(applied_pcs) or len(set(pcs)) != 4:
                issues.append(
                    ("CM038", f"Beat {beat}: applied dominant is not a complete dominant seventh")
                )
            if 0 <= inversions[beat] <= 2 and bv % 12 != applied_pcs[inversions[beat]]:
                issues.append(
                    ("CM038", f"Beat {beat}: applied-dominant inversion does not match the bass")
                )
            continue

        if source is not None:
            if has_family(
                semantic_dispatch,
                beat,
                ContextualHarmonyFamily.BORROWED_SEVENTH,
            ):
                continue
            if (
                not metadata_valid
                or source is not canonical_source
                or degree not in supported_borrowed
            ):
                continue
            borrowed_pcs = borrowed_triad_pitch_classes(key, degree, source)
            if kind is not ChordKind.TRIAD or set(pcs) != set(borrowed_pcs) or len(set(pcs)) != 3:
                issues.append(
                    ("CM042", f"Beat {beat}: borrowed chord is not the complete source-mode triad")
                )
            if 0 <= inversions[beat] <= 2 and bv % 12 != borrowed_pcs[inversions[beat]]:
                issues.append(
                    ("CM042", f"Beat {beat}: borrowed-chord inversion does not match the bass")
                )
            continue

        if kind is ChordKind.TRIAD:
            triad = key.triad_pitch_classes(degree)
            root = triad[0]
            if (
                any(pc not in triad for pc in pcs)
                or set(pcs) != set(triad)
                or pcs.count(root) < 2
            ):
                issues.append(
                    (
                        "CM030",
                        f"Beat {beat}: SATB chord is incomplete or does not double the root",
                    )
                )
        elif metadata_valid:
            seventh = key.seventh_pitch_classes(degree)
            if set(pcs) != set(seventh) or len(set(pcs)) != 4:
                issues.append(
                    ("CM034", f"Beat {beat}: seventh chord does not contain four chord tones")
                )

        if metadata_valid:
            chord_tones = (
                key.triad_pitch_classes(degree)
                if kind is ChordKind.TRIAD
                else key.seventh_pitch_classes(degree)
            )
            inversion = inversions[beat]
            if not 0 <= inversion <= 2:
                continue
            if bv % 12 != chord_tones[inversion]:
                issues.append(
                    ("CM034", f"Beat {beat}: serialized inversion does not match the bass")
                )

    if spec.avoid_parallel_perfects:
        named = (
            ("S-A", soprano, alto),
            ("S-T", soprano, tenor),
            ("A-T", alto, tenor),
            ("A-B", alto, bass),
            ("T-B", tenor, bass),
        )
        for label, left_voice, right_voice in named:
            for beat in range(min(len(left_voice), len(right_voice)) - 1):
                if is_parallel_perfect(
                    left_voice[beat],
                    right_voice[beat],
                    left_voice[beat + 1],
                    right_voice[beat + 1],
                ):
                    issues.append(
                        ("CM031", f"Beats {beat}->{beat + 1}: parallel perfect in {label}")
                    )

    if spec.resolve_leading_tone:
        for label, voice in (("alto", alto), ("tenor", tenor)):
            for beat, (left, right) in enumerate(pairwise(voice)):
                if left % 12 == key.leading_tone_pc and right != left + 1:
                    issues.append(
                        ("CM032", f"{label} beat {beat}: leading tone does not resolve upward")
                    )

    if metadata_valid and context_valid:
        _verify_expanded_harmony_motion(
            result,
            kinds,
            targets,
            issues,
            semantic_dispatch=semantic_dispatch,
        )

    return tuple(issues)


def satb_register_verification_issues(
    voices: tuple[int, int, int, int],
    *,
    melody_low: int,
    melody_high: int,
    beat: int | None = None,
) -> tuple[tuple[str, str], ...]:
    """Classify one S/A/T/B register tuple under CM028 and CM029.

    The bass range is enforced by CM003 in the complete verifier. Bounded callers
    should enumerate bass notes inside the configured bass range before invoking
    this local predicate.
    """

    prefix = "" if beat is None else f"Beat {beat}: "
    soprano, alto, tenor, bass = voices
    issues: list[tuple[str, str]] = []
    if not melody_low <= soprano <= melody_high:
        issues.append(("CM028", f"{prefix}soprano is outside its configured range"))
    if not ALTO_LOW <= alto <= ALTO_HIGH:
        issues.append(("CM028", f"{prefix}alto is outside {ALTO_LOW}..{ALTO_HIGH}"))
    if not TENOR_LOW <= tenor <= TENOR_HIGH:
        issues.append(("CM028", f"{prefix}tenor is outside {TENOR_LOW}..{TENOR_HIGH}"))
    if not bass < tenor < alto < soprano:
        issues.append(("CM028", f"{prefix}SATB voice order/crossing invariant is violated"))
    if soprano - alto > MAX_UPPER_SPACING or alto - tenor > MAX_UPPER_SPACING:
        issues.append(("CM029", f"{prefix}adjacent upper voices exceed octave spacing"))
    return tuple(issues)


def _verify_expanded_harmony_motion(
    result: SatbGenerationResult,
    kinds: tuple[ChordKind, ...],
    targets: tuple[int | None, ...],
    issues: list[tuple[str, str]],
    *,
    semantic_dispatch: SemanticDispatch | None = None,
) -> None:
    key = result.spec.tonal_key
    voices = (
        ("soprano", result.soprano),
        ("alto", result.alto),
        ("tenor", result.tenor),
        ("bass", result.bass),
    )
    supported_targets = set(key.applied_dominant_targets)
    beats = min(len(result.chord_degrees), len(kinds), len(targets))
    for beat in range(beats):
        if kinds[beat] is not ChordKind.SEVENTH:
            continue
        target = targets[beat]
        if target is not None:
            if has_family(
                semantic_dispatch,
                beat,
                ContextualHarmonyFamily.SECONDARY_LEADING_TONE_TRIAD,
                ContextualHarmonyFamily.SECONDARY_LEADING_TONE_SEVENTH,
            ):
                continue
            if target not in supported_targets:
                continue
            if beat + 1 >= beats:
                issues.append(("CM039", f"Beat {beat}: applied dominant has no target resolution"))
                continue
            if (
                result.chord_degrees[beat + 1] != target
                or targets[beat + 1] is not None
            ):
                issues.append(
                    (
                        "CM039",
                        f"Beat {beat}: applied dominant does not resolve to its declared target",
                    )
                )
            applied_pcs = key.applied_dominant_seventh_pitch_classes(target)
            seventh_pc = applied_pcs[3]
            leading_pc = applied_pcs[1]
            for label, voice in voices:
                if voice[beat] % 12 == seventh_pc:
                    delta = voice[beat + 1] - voice[beat]
                    if delta not in {-1, -2}:
                        issues.append(
                            (
                                "CM040",
                                (
                                    f"{label} beat {beat}: applied chordal seventh "
                                    "does not resolve down"
                                ),
                            )
                        )
                if voice[beat] % 12 == leading_pc and voice[beat + 1] != voice[beat] + 1:
                    issues.append(
                        (
                            "CM040",
                            f"{label} beat {beat}: applied leading tone does not resolve upward",
                        )
                    )
            continue

        if beat + 1 >= beats:
            issues.append(("CM035", f"Beat {beat}: chordal seventh has no following resolution"))
            continue
        degree = result.chord_degrees[beat]
        if not 0 <= degree <= 6:
            continue
        seventh_pc = key.seventh_pitch_classes(degree)[3]
        for label, voice in voices:
            if voice[beat] % 12 == seventh_pc:
                delta = voice[beat + 1] - voice[beat]
                if delta not in {-1, -2}:
                    issues.append(
                        (
                            "CM035",
                            f"{label} beat {beat}: chordal seventh does not resolve down by step",
                        )
                    )

        if degree == 4:
            if result.chord_degrees[beat + 1] != 0:
                issues.append(("CM036", f"Beat {beat}: dominant seventh does not resolve to tonic"))
            for label, voice in voices:
                if voice[beat] % 12 == key.leading_tone_pc and voice[beat + 1] != voice[beat] + 1:
                    issues.append(
                        (
                            "CM036",
                            f"{label} beat {beat}: dominant leading tone does not resolve upward",
                        )
                    )


@cache
def _satb_chord_rows(
    key: Key,
    expanded_harmony: bool,
    tonicization_enabled: bool,
    modal_mixture_enabled: bool,
) -> tuple[tuple[int, int, int, int, int, int, int, int, int], ...]:
    rows: list[tuple[int, int, int, int, int, int, int, int, int]] = []
    for degree in range(7):
        triad = key.triad_pitch_classes(degree)
        root = triad[0]
        for pcs in product(triad, repeat=4):
            if set(pcs) == set(triad) and pcs.count(root) >= 2:
                inversion = triad.index(pcs[3])
                rows.append(
                    (
                        degree,
                        int(ChordKind.TRIAD),
                        inversion,
                        NO_TONICIZATION_TARGET,
                        NO_MODAL_SOURCE,
                        pcs[0],
                        pcs[1],
                        pcs[2],
                        pcs[3],
                    )
                )
        if not expanded_harmony:
            continue
        seventh = key.seventh_pitch_classes(degree)
        for pcs in product(seventh, repeat=4):
            if set(pcs) != set(seventh):
                continue
            if pcs[0] not in triad or pcs[3] not in triad:
                continue
            inversion = seventh.index(pcs[3])
            if inversion > 2:
                continue
            rows.append(
                (
                    degree,
                    int(ChordKind.SEVENTH),
                    inversion,
                    NO_TONICIZATION_TARGET,
                    NO_MODAL_SOURCE,
                    pcs[0],
                    pcs[1],
                    pcs[2],
                    pcs[3],
                )
            )

    if tonicization_enabled:
        for target in key.applied_dominant_targets:
            degree = key.applied_dominant_root_degree(target)
            legacy_triad = key.triad_pitch_classes(degree)
            applied = key.applied_dominant_seventh_pitch_classes(target)
            for pcs in product(applied, repeat=4):
                if set(pcs) != set(applied):
                    continue
                if pcs[0] not in legacy_triad or pcs[3] not in legacy_triad:
                    continue
                inversion = applied.index(pcs[3])
                if inversion > 2:
                    continue
                rows.append(
                    (
                        degree,
                        int(ChordKind.SEVENTH),
                        inversion,
                        target,
                        NO_MODAL_SOURCE,
                        pcs[0],
                        pcs[1],
                        pcs[2],
                        pcs[3],
                    )
                )

    if modal_mixture_enabled:
        source = canonical_modal_source(key)
        for degree in supported_borrowed_degrees(key):
            legacy_triad = key.triad_pitch_classes(degree)
            borrowed = borrowed_triad_pitch_classes(key, degree, source)
            for pcs in product(borrowed, repeat=4):
                if set(pcs) != set(borrowed):
                    continue
                if pcs[0] not in legacy_triad or pcs[3] not in legacy_triad:
                    continue
                inversion = borrowed.index(pcs[3])
                rows.append(
                    (
                        degree,
                        int(ChordKind.TRIAD),
                        inversion,
                        NO_TONICIZATION_TARGET,
                        int(source),
                        pcs[0],
                        pcs[1],
                        pcs[2],
                        pcs[3],
                    )
                )
    return tuple(rows)


@cache
def _chordal_seventh_flag_rows(
    key: Key,
    tonicization_enabled: bool,
) -> tuple[tuple[int, int, int, int, int], ...]:
    supported = set(key.applied_dominant_targets) if tonicization_enabled else set()
    rows: list[tuple[int, int, int, int, int]] = []
    for degree in range(7):
        for kind in ChordKind:
            for target in range(NO_TONICIZATION_TARGET + 1):
                seventh_pc: int | None = None
                if kind is ChordKind.SEVENTH:
                    if target == NO_TONICIZATION_TARGET:
                        seventh_pc = key.seventh_pitch_classes(degree)[3]
                    elif target in supported and degree == key.applied_dominant_root_degree(target):
                        seventh_pc = key.applied_dominant_seventh_pitch_classes(target)[3]
                for pc in range(12):
                    flag = int(seventh_pc is not None and pc == seventh_pc)
                    rows.append((degree, int(kind), target, pc, flag))
    return tuple(rows)


@cache
def _global_dominant_seventh_flag_rows() -> tuple[tuple[int, int, int, int], ...]:
    return tuple(
        (
            degree,
            int(kind),
            target,
            int(
                degree == 4
                and kind is ChordKind.SEVENTH
                and target == NO_TONICIZATION_TARGET
            ),
        )
        for degree in range(7)
        for kind in ChordKind
        for target in range(NO_TONICIZATION_TARGET + 1)
    )


@cache
def _dominant_leading_flag_rows(
    key: Key,
    tonicization_enabled: bool,
) -> tuple[tuple[int, int, int, int, int], ...]:
    supported = set(key.applied_dominant_targets) if tonicization_enabled else set()
    rows: list[tuple[int, int, int, int, int]] = []
    for degree in range(7):
        for kind in ChordKind:
            for target in range(NO_TONICIZATION_TARGET + 1):
                leading_pc: int | None = None
                if kind is ChordKind.SEVENTH:
                    if target == NO_TONICIZATION_TARGET and degree == 4:
                        leading_pc = key.leading_tone_pc
                    elif target in supported and degree == key.applied_dominant_root_degree(target):
                        leading_pc = key.applied_dominant_seventh_pitch_classes(target)[1]
                for pc in range(12):
                    flag = int(leading_pc is not None and pc == leading_pc)
                    rows.append((degree, int(kind), target, pc, flag))
    return tuple(rows)


@cache
def _parallel_rows(
    left_domain: tuple[int, ...], right_domain: tuple[int, ...]
) -> tuple[tuple[int, int, int, int], ...]:
    perfect_pairs = tuple(
        (left, right)
        for left in left_domain
        for right in right_domain
        if (left - right) % 12 in {0, 7}
    )
    return tuple(
        (left_a, right_a, left_b, right_b)
        for left_a, right_a in perfect_pairs
        for left_b, right_b in perfect_pairs
        if is_parallel_perfect(left_a, right_a, left_b, right_b)
    )


def _pitches_for_pitch_classes(low: int, high: int, pitch_classes: set[int]) -> tuple[int, ...]:
    pcs = {pc % 12 for pc in pitch_classes}
    return tuple(note for note in range(low, high + 1) if note % 12 in pcs)
