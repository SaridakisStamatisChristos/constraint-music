from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise
from typing import Any

from ortools.sat.python import cp_model

from .modal_mixture import (
    NO_MODAL_SOURCE,
    ModalSource,
    borrowed_chord_name,
    borrowed_triad_pitch_classes,
    canonical_modal_source,
    supported_borrowed_degrees,
)
from .models import GenerationResult, GenerationSpec, RhythmState
from .modulation import common_tonic_pivot_destination_degree, dominant_key
from .satb import (
    ALTO_HIGH,
    ALTO_LOW,
    MAX_UPPER_SPACING,
    TENOR_HIGH,
    TENOR_LOW,
    SatbGenerationResult,
    SatbVariables,
    _chordal_seventh_flag_rows,
    _dominant_leading_flag_rows,
    _global_dominant_seventh_flag_rows,
    _parallel_rows,
    _pitches_for_pitch_classes,
    _satb_chord_rows,
)
from .satb import result_from_dict as legacy_result_from_dict
from .theory import NO_TONICIZATION_TARGET, ChordKind, Key, Mode, is_parallel_perfect


@dataclass(frozen=True, slots=True)
class ModulatedSatbGenerationResult(SatbGenerationResult):
    key_contexts: tuple[Key, ...] = ()

    @property
    def chord_form_names(self) -> tuple[str, ...]:
        if not (
            len(self.chord_kinds)
            == len(self.chord_inversions)
            == len(self.chord_degrees)
        ):
            return ()
        targets = self.tonicization_targets or (None,) * len(self.chord_degrees)
        sources = self.modal_sources or (None,) * len(self.chord_degrees)
        if not (len(targets) == len(sources) == len(self.chord_degrees)):
            return ()
        names: list[str] = []
        try:
            for beat, values in enumerate(
                zip(
                    self.chord_degrees,
                    self.chord_kinds,
                    self.chord_inversions,
                    targets,
                    sources,
                    strict=True,
                )
            ):
                degree, raw_kind, inversion, target, raw_source = values
                key = self.spec.active_key_at_beat(beat)
                kind = ChordKind.parse(raw_kind)
                source = None if raw_source is None else ModalSource.parse(raw_source)
                if target is not None and source is not None:
                    return ()
                if target is not None:
                    if kind is not ChordKind.SEVENTH:
                        return ()
                    names.append(key.applied_dominant_name(target, inversion))
                elif source is not None:
                    if kind is not ChordKind.TRIAD:
                        return ()
                    names.append(borrowed_chord_name(key, degree, source, inversion))
                else:
                    names.append(key.chord_form_name(degree, kind, inversion))
        except (IndexError, ValueError):
            return ()
        return tuple(names)

    def to_dict(self) -> dict[str, Any]:
        payload = SatbGenerationResult.to_dict(self)
        music = payload["music"]
        if self.key_contexts:
            music["key_contexts"] = [
                {"tonic": key.tonic, "mode": key.mode.value} for key in self.key_contexts
            ]
        return payload


def result_from_dict(payload: Mapping[str, Any]) -> GenerationResult:
    base = legacy_result_from_dict(payload)
    if not base.spec.modulation_enabled:
        return base
    if not isinstance(base, SatbGenerationResult):
        return base
    raw_music = payload.get("music")
    if not isinstance(raw_music, Mapping):
        raise ValueError("Result JSON music section must be an object")
    raw_contexts = raw_music.get("key_contexts", ())
    if not isinstance(raw_contexts, Sequence) or isinstance(raw_contexts, (str, bytes)):
        raise ValueError("Result JSON music.key_contexts must be an array")
    contexts: list[Key] = []
    for item in raw_contexts:
        if not isinstance(item, Mapping):
            raise ValueError("Result JSON music.key_contexts entries must be objects")
        tonic = item.get("tonic")
        mode = item.get("mode")
        if not isinstance(tonic, str) or not isinstance(mode, str):
            raise ValueError("Result JSON key_context entries require tonic/mode strings")
        contexts.append(Key(tonic, Mode(mode)))
    return ModulatedSatbGenerationResult(
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
        soprano=base.soprano,
        alto=base.alto,
        tenor=base.tenor,
        chord_kinds=base.chord_kinds,
        chord_inversions=base.chord_inversions,
        tonicization_targets=base.tonicization_targets,
        modal_sources=base.modal_sources,
        key_contexts=tuple(contexts),
    )


def add_modulated_satb_constraints(
    model: cp_model.CpModel,
    spec: GenerationSpec,
    chord: list[cp_model.IntVar],
    melody_note: list[cp_model.IntVar],
    bass_note: list[cp_model.IntVar],
) -> SatbVariables:
    global_key = spec.tonal_key
    soprano_domain = global_key.pitches_in_range(spec.melody_low, spec.melody_high)
    bass_domain = global_key.pitches_in_range(spec.bass_low, spec.bass_high)
    inner_pitch_classes: set[int] = set()
    for key in spec.context_keys:
        inner_pitch_classes.update(key.pitch_classes)
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
    if not alto_domain or not tenor_domain:
        raise ValueError("SATB inner-voice ranges contain no active-key pitches")

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
        for beat, source_var in enumerate(modal_source):
            canonical = int(canonical_modal_source(spec.active_key_at_beat(beat)))
            model.add_allowed_assignments([source_var], [(NO_MODAL_SOURCE,), (canonical,)])
            borrowed = model.new_bool_var(f"borrowed_chord_{beat}")
            model.add(source_var == canonical).only_enforce_if(borrowed)
            model.add(source_var == NO_MODAL_SOURCE).only_enforce_if(borrowed.negated())
            borrowed_flags.append(borrowed)
        if spec.minimum_borrowed_chords:
            model.add(sum(borrowed_flags) >= spec.minimum_borrowed_chords)
    else:
        for source_var in modal_source:
            model.add(source_var == NO_MODAL_SOURCE)

    boundary = spec.modulation_boundary_beat
    if boundary is None:
        raise ValueError("Validated modulation spec lost modulation_boundary_beat")
    reserved = {0, boundary - 1, spec.total_beats - 2, spec.total_beats - 1}
    for beat in reserved:
        model.add(tonicization_target[beat] == NO_TONICIZATION_TARGET)
        model.add(modal_source[beat] == NO_MODAL_SOURCE)
    model.add(chord_kind[0] == int(ChordKind.TRIAD))
    model.add(chord_kind[boundary - 1] == int(ChordKind.TRIAD))

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

        pcs = [
            model.new_int_var(0, 11, f"satb_pc_{beat}_{index}") for index in range(4)
        ]
        pitch_classes.append(pcs)
        voices = (soprano[beat], alto[beat], tenor[beat], bass_note[beat])
        for pc, note_var in zip(pcs, voices, strict=True):
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
            _satb_chord_rows(
                spec.active_key_at_beat(beat),
                spec.expanded_harmony_enabled,
                spec.tonicization_enabled,
                spec.modal_mixture_enabled,
            ),
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
        for voice_vars, domain in ((alto, alto_domain), (tenor, tenor_domain)):
            for beat, (left_var, right_var) in enumerate(pairwise(voice_vars)):
                key = spec.active_key_at_beat(beat)
                allowed = [
                    (left_note, right_note)
                    for left_note in domain
                    for right_note in domain
                    if left_note % 12 != key.leading_tone_pc
                    or right_note == left_note + 1
                ]
                model.add_allowed_assignments([left_var, right_var], allowed)

    if spec.expanded_harmony_enabled:
        _add_modulated_harmony_motion_constraints(
            model,
            spec,
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


def _add_modulated_harmony_motion_constraints(
    model: cp_model.CpModel,
    spec: GenerationSpec,
    chord: list[cp_model.IntVar],
    chord_kind: list[cp_model.IntVar],
    tonicization_target: list[cp_model.IntVar],
    pitch_classes: list[list[cp_model.IntVar]],
    soprano: list[cp_model.IntVar],
    alto: list[cp_model.IntVar],
    tenor: list[cp_model.IntVar],
    bass: list[cp_model.IntVar],
) -> None:
    global_dominant_rows = _global_dominant_seventh_flag_rows()
    voices = (soprano, alto, tenor, bass)
    for beat in range(len(chord) - 1):
        key = spec.active_key_at_beat(beat)
        seventh_rows = _chordal_seventh_flag_rows(key, spec.tonicization_enabled)
        leading_rows = _dominant_leading_flag_rows(key, spec.tonicization_enabled)
        target = tonicization_target[beat]
        applied = model.new_bool_var(f"motion_applied_dominant_{beat}")
        model.add(target != NO_TONICIZATION_TARGET).only_enforce_if(applied)
        model.add(target == NO_TONICIZATION_TARGET).only_enforce_if(applied.negated())
        model.add(chord[beat + 1] == target).only_enforce_if(applied)
        model.add(
            tonicization_target[beat + 1] == NO_TONICIZATION_TARGET
        ).only_enforce_if(applied)

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
            model.add(voice[beat + 1] <= voice[beat] - 1).only_enforce_if(
                carries_seventh
            )
            model.add(voice[beat + 1] >= voice[beat] - 2).only_enforce_if(
                carries_seventh
            )
            carries_leading = model.new_bool_var(f"dominant_leading_{beat}_{voice_index}")
            model.add_allowed_assignments(
                [chord[beat], chord_kind[beat], target, current_pc, carries_leading],
                leading_rows,
            )
            model.add(voice[beat + 1] == voice[beat] + 1).only_enforce_if(
                carries_leading
            )


def modulated_satb_verification_issues(
    result: GenerationResult,
) -> tuple[tuple[str, str], ...]:
    if not isinstance(result, ModulatedSatbGenerationResult):
        return (("CM043", "Enabled modulation requires modulated SATB result metadata"),)
    spec = result.spec
    soprano, alto, tenor, bass = result.soprano, result.alto, result.tenor, result.bass
    issues: list[tuple[str, str]] = []
    if not all(len(voice) == spec.total_beats for voice in (soprano, alto, tenor, bass)):
        return (("CM027", "SATB voices must contain exactly one note per beat"),)
    for beat, note in enumerate(soprano):
        strong_step = beat * spec.subdivisions_per_beat
        if strong_step >= len(result.melody) or note != result.melody[strong_step]:
            issues.append(
                ("CM027", f"Beat {beat}: soprano is not anchored to strong-step melody")
            )

    metadata_valid = (
        len(result.chord_kinds) == len(result.chord_inversions) == spec.total_beats
    )
    if not metadata_valid:
        issues.append(("CM033", "Harmonic kind/inversion arrays require one value per beat"))
        return tuple(issues)
    try:
        kinds = tuple(ChordKind.parse(item) for item in result.chord_kinds)
    except ValueError:
        issues.append(("CM033", "Harmonic form contains an unknown chord kind"))
        return tuple(issues)
    inversions = tuple(int(item) for item in result.chord_inversions)
    if any(not 0 <= inversion <= 2 for inversion in inversions):
        issues.append(("CM033", "Chord inversions must be encoded in 0..2"))
    if not spec.expanded_harmony_enabled and any(
        kind is ChordKind.SEVENTH for kind in kinds
    ):
        issues.append(("CM033", "Seventh chords require harmony_vocabulary='triads+sevenths'"))
    if sum(kind is ChordKind.SEVENTH for kind in kinds) < spec.minimum_seventh_chords:
        issues.append(("CM033", "Serialized harmony does not meet minimum_seventh_chords"))

    if result.tonicization_targets:
        if len(result.tonicization_targets) != spec.total_beats:
            issues.append(("CM037", "Tonicization metadata requires one value per beat"))
            targets: tuple[int | None, ...] = (None,) * spec.total_beats
            targets_valid = False
        else:
            targets = result.tonicization_targets
            targets_valid = True
    elif spec.tonicization_enabled:
        issues.append(("CM037", "Enabled tonicization requires explicit target metadata"))
        targets = (None,) * spec.total_beats
        targets_valid = False
    else:
        targets = (None,) * spec.total_beats
        targets_valid = True

    applied_count = 0
    if targets_valid:
        for beat, target in enumerate(targets):
            if target is None:
                continue
            applied_count += 1
            key = spec.active_key_at_beat(beat)
            if not spec.tonicization_enabled:
                issues.append(("CM037", f"Beat {beat}: tonicization is disabled"))
                continue
            if target not in key.applied_dominant_targets:
                issues.append(
                    ("CM037", f"Beat {beat}: target {target} is unsupported in {key}")
                )
            if kinds[beat] is not ChordKind.SEVENTH:
                issues.append(("CM037", f"Beat {beat}: applied dominant must be seventh"))
        if applied_count < spec.minimum_applied_dominants:
            issues.append(("CM037", "Serialized harmony misses minimum_applied_dominants"))

    if result.modal_sources:
        if len(result.modal_sources) != spec.total_beats:
            issues.append(("CM041", "Modal-source metadata requires one value per beat"))
            sources: tuple[ModalSource | None, ...] = (None,) * spec.total_beats
            sources_valid = False
        else:
            try:
                sources = tuple(
                    None if source is None else ModalSource.parse(source)
                    for source in result.modal_sources
                )
            except ValueError:
                issues.append(("CM041", "Modal-source metadata contains unknown source"))
                sources = (None,) * spec.total_beats
                sources_valid = False
            else:
                sources_valid = True
    elif spec.modal_mixture_enabled:
        issues.append(("CM041", "Enabled modal mixture requires explicit source metadata"))
        sources = (None,) * spec.total_beats
        sources_valid = False
    else:
        sources = (None,) * spec.total_beats
        sources_valid = True

    borrowed_count = 0
    if sources_valid:
        for beat, source in enumerate(sources):
            if source is None:
                continue
            borrowed_count += 1
            key = spec.active_key_at_beat(beat)
            if not spec.modal_mixture_enabled:
                issues.append(("CM041", f"Beat {beat}: modal mixture is disabled"))
                continue
            if source is not canonical_modal_source(key):
                issues.append(
                    ("CM041", f"Beat {beat}: source {source.label} is not canonical for {key}")
                )
            if beat >= spec.total_beats - 2:
                issues.append(("CM041", f"Beat {beat}: destination cadence must be unborrowed"))
            if result.chord_degrees[beat] not in supported_borrowed_degrees(key):
                issues.append(
                    ("CM041", f"Beat {beat}: degree is not borrowable in active key {key}")
                )
            if targets_valid and targets[beat] is not None:
                issues.append(("CM041", f"Beat {beat}: borrowing and tonicization overlap"))
            if kinds[beat] is not ChordKind.TRIAD:
                issues.append(("CM041", f"Beat {beat}: borrowed harmony must be triadic"))
        if borrowed_count < spec.minimum_borrowed_chords:
            issues.append(("CM041", "Serialized harmony misses minimum_borrowed_chords"))

    for beat, (sv, av, tv, bv) in enumerate(
        zip(soprano, alto, tenor, bass, strict=True)
    ):
        if not spec.melody_low <= sv <= spec.melody_high:
            issues.append(("CM028", f"Beat {beat}: soprano is outside configured range"))
        if not ALTO_LOW <= av <= ALTO_HIGH:
            issues.append(("CM028", f"Beat {beat}: alto is outside {ALTO_LOW}..{ALTO_HIGH}"))
        if not TENOR_LOW <= tv <= TENOR_HIGH:
            issues.append(("CM028", f"Beat {beat}: tenor is outside {TENOR_LOW}..{TENOR_HIGH}"))
        if not bv < tv < av < sv:
            issues.append(("CM028", f"Beat {beat}: SATB voice order is violated"))
        if sv - av > MAX_UPPER_SPACING or av - tv > MAX_UPPER_SPACING:
            issues.append(("CM029", f"Beat {beat}: upper voices exceed octave spacing"))
        if beat >= len(result.chord_degrees):
            continue
        degree = result.chord_degrees[beat]
        if not 0 <= degree <= 6:
            continue
        key = spec.active_key_at_beat(beat)
        pcs = (sv % 12, av % 12, tv % 12, bv % 12)
        kind = kinds[beat]
        target = targets[beat] if targets_valid else None
        source = sources[beat] if sources_valid else None

        if target is not None:
            if target not in key.applied_dominant_targets:
                continue
            expected_degree = key.applied_dominant_root_degree(target)
            applied = key.applied_dominant_seventh_pitch_classes(target)
            if degree != expected_degree:
                issues.append(("CM038", f"Beat {beat}: applied root degree mismatches target"))
            if kind is not ChordKind.SEVENTH or set(pcs) != set(applied):
                issues.append(("CM038", f"Beat {beat}: incomplete applied dominant seventh"))
            if 0 <= inversions[beat] <= 2 and bv % 12 != applied[inversions[beat]]:
                issues.append(("CM038", f"Beat {beat}: applied inversion mismatches bass"))
            continue

        if source is not None:
            if source is not canonical_modal_source(key):
                continue
            if degree not in supported_borrowed_degrees(key):
                continue
            borrowed = borrowed_triad_pitch_classes(key, degree, source)
            if kind is not ChordKind.TRIAD or set(pcs) != set(borrowed):
                issues.append(("CM042", f"Beat {beat}: incomplete active-key borrowed triad"))
            if 0 <= inversions[beat] <= 2 and bv % 12 != borrowed[inversions[beat]]:
                issues.append(("CM042", f"Beat {beat}: borrowed inversion mismatches bass"))
            continue

        tones: tuple[int, ...]
        if kind is ChordKind.TRIAD:
            triad = key.triad_pitch_classes(degree)
            root = triad[0]
            if set(pcs) != set(triad) or pcs.count(root) < 2:
                issues.append(
                    ("CM030", f"Beat {beat}: active-key triad incomplete/root not doubled")
                )
            tones = triad
        else:
            seventh = key.seventh_pitch_classes(degree)
            if set(pcs) != set(seventh) or len(set(pcs)) != 4:
                issues.append(("CM034", f"Beat {beat}: active-key seventh is incomplete"))
            tones = seventh
        if 0 <= inversions[beat] <= 2 and bv % 12 != tones[inversions[beat]]:
            issues.append(("CM034", f"Beat {beat}: inversion mismatches realized bass"))

    if spec.avoid_parallel_perfects:
        named = (
            ("S-A", soprano, alto),
            ("S-T", soprano, tenor),
            ("A-T", alto, tenor),
            ("A-B", alto, bass),
            ("T-B", tenor, bass),
        )
        for label, left_voice, right_voice in named:
            for beat in range(spec.total_beats - 1):
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
                key = spec.active_key_at_beat(beat)
                if left % 12 == key.leading_tone_pc and right != left + 1:
                    issues.append(
                        ("CM032", f"{label} beat {beat}: active leading tone fails to resolve")
                    )

    if targets_valid:
        _verify_modulated_harmony_motion(result, kinds, targets, issues)
    return tuple(issues)


def _verify_modulated_harmony_motion(
    result: ModulatedSatbGenerationResult,
    kinds: tuple[ChordKind, ...],
    targets: tuple[int | None, ...],
    issues: list[tuple[str, str]],
) -> None:
    voices = (
        ("soprano", result.soprano),
        ("alto", result.alto),
        ("tenor", result.tenor),
        ("bass", result.bass),
    )
    beats = min(len(result.chord_degrees), len(kinds), len(targets))
    for beat in range(beats):
        if kinds[beat] is not ChordKind.SEVENTH:
            continue
        key = result.spec.active_key_at_beat(beat)
        target = targets[beat]
        if target is not None:
            if target not in key.applied_dominant_targets:
                continue
            if beat + 1 >= beats:
                issues.append(("CM039", f"Beat {beat}: applied dominant has no resolution"))
                continue
            if result.chord_degrees[beat + 1] != target or targets[beat + 1] is not None:
                issues.append(("CM039", f"Beat {beat}: applied dominant misses target resolution"))
            applied = key.applied_dominant_seventh_pitch_classes(target)
            seventh_pc = applied[3]
            leading_pc = applied[1]
            for label, voice in voices:
                if voice[beat] % 12 == seventh_pc:
                    delta = voice[beat + 1] - voice[beat]
                    if delta not in {-1, -2}:
                        issues.append(
                            ("CM040", f"{label} beat {beat}: applied seventh fails down-step")
                        )
                if voice[beat] % 12 == leading_pc and voice[beat + 1] != voice[beat] + 1:
                    issues.append(
                        ("CM040", f"{label} beat {beat}: applied leading tone fails upward")
                    )
            continue

        if beat + 1 >= beats:
            issues.append(("CM035", f"Beat {beat}: chordal seventh has no resolution"))
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
                        ("CM035", f"{label} beat {beat}: chordal seventh fails down-step")
                    )
        if degree == 4:
            if result.chord_degrees[beat + 1] != 0:
                issues.append(("CM036", f"Beat {beat}: active dominant seventh misses tonic"))
            for label, voice in voices:
                if voice[beat] % 12 == key.leading_tone_pc and voice[beat + 1] != voice[beat] + 1:
                    issues.append(
                        ("CM036", f"{label} beat {beat}: dominant leading tone fails upward")
                    )


def modulation_verification_issues(
    result: GenerationResult,
) -> tuple[tuple[str, str], ...]:
    spec = result.spec
    if not spec.modulation_enabled:
        if isinstance(result, ModulatedSatbGenerationResult) and result.key_contexts:
            return (("CM043", "Key contexts are present while modulation is disabled"),)
        return ()
    if not isinstance(result, ModulatedSatbGenerationResult):
        return (("CM043", "Enabled modulation requires explicit key-context metadata"),)

    issues: list[tuple[str, str]] = []
    destination = spec.modulation_destination
    boundary = spec.modulation_boundary_beat
    if destination is None or boundary is None:
        return (("CM044", "Enabled modulation lacks destination or boundary identity"),)
    expected_destination = dominant_key(spec.tonal_key)
    if destination != expected_destination:
        issues.append(
            ("CM044", f"Destination {destination} is not dominant key {expected_destination}")
        )
    if not 2 <= boundary <= spec.total_beats - 2:
        issues.append(("CM044", f"Boundary {boundary} is outside certified range"))
        return tuple(issues)
    if len(result.key_contexts) != spec.total_beats:
        issues.append(("CM043", "Key-context metadata must contain one key per beat"))
        return tuple(issues)
    if result.key_contexts != spec.expected_key_contexts:
        issues.append(("CM048", "Serialized key contexts disagree with declared boundary"))

    pivot = boundary - 1
    try:
        pivot_destination_degree = common_tonic_pivot_destination_degree(
            spec.tonal_key, destination
        )
    except ValueError as exc:
        issues.append(("CM045", str(exc)))
        pivot_destination_degree = -1
    if pivot_destination_degree != 3:
        issues.append(("CM045", "Source I must reinterpret exactly as destination IV"))
    if result.chord_degrees[pivot] != 0:
        issues.append(("CM045", "Certified pivot must be source tonic degree 0"))
    if result.chord_kinds[pivot] is not ChordKind.TRIAD:
        issues.append(("CM045", "Certified pivot must remain triadic"))
    if result.tonicization_targets[pivot] is not None:
        issues.append(("CM045", "Certified pivot cannot be tonicized"))
    if result.modal_sources[pivot] is not None:
        issues.append(("CM045", "Certified pivot cannot be borrowed"))
    if all(
        len(voice) == spec.total_beats
        for voice in (result.soprano, result.alto, result.tenor, result.bass)
    ):
        pivot_pcs = {
            result.soprano[pivot] % 12,
            result.alto[pivot] % 12,
            result.tenor[pivot] % 12,
            result.bass[pivot] % 12,
        }
        if pivot_pcs != set(spec.tonal_key.triad_pitch_classes(0)):
            issues.append(("CM045", "Pivot realization is not exact source-tonic triad"))
        if pivot_pcs != set(destination.triad_pitch_classes(3)):
            issues.append(("CM045", "Pivot realization is not destination-IV common chord"))

    targets = result.tonicization_targets
    sources = result.modal_sources
    if (
        len(result.chord_kinds)
        == len(result.chord_degrees)
        == len(targets)
        == len(sources)
        == spec.total_beats
        and all(
            len(voice) == spec.total_beats
            for voice in (result.soprano, result.alto, result.tenor, result.bass)
        )
    ):
        for beat in range(boundary, spec.total_beats):
            degree = result.chord_degrees[beat]
            if not 0 <= degree <= 6:
                continue
            pcs = {
                result.soprano[beat] % 12,
                result.alto[beat] % 12,
                result.tenor[beat] % 12,
                result.bass[beat] % 12,
            }
            kind = ChordKind.parse(result.chord_kinds[beat])
            target = targets[beat]
            source = sources[beat]
            if target is not None:
                if target not in destination.applied_dominant_targets:
                    issues.append(("CM046", f"Beat {beat}: target invalid in destination key"))
                    continue
                expected = set(destination.applied_dominant_seventh_pitch_classes(target))
            elif source is not None:
                if source is not canonical_modal_source(destination):
                    issues.append(("CM046", f"Beat {beat}: stale modal source context"))
                    continue
                expected = set(borrowed_triad_pitch_classes(destination, degree, source))
            elif kind is ChordKind.TRIAD:
                expected = set(destination.triad_pitch_classes(degree))
            else:
                expected = set(destination.seventh_pitch_classes(degree))
            if pcs != expected:
                issues.append(("CM046", f"Beat {beat}: harmony is not destination-key derived"))

    if tuple(result.chord_degrees[-2:]) != (4, 0):
        issues.append(("CM047", "Destination region must close with V-I"))
    if result.key_contexts[-2:] != (destination, destination):
        issues.append(("CM047", "Destination cadence is outside destination context"))
    if result.soprano[-1] % 12 != destination.tonic_pc:
        issues.append(("CM047", "Final soprano is not destination tonic"))
    if result.bass[-1] % 12 != destination.tonic_pc:
        issues.append(("CM047", "Final bass is not destination tonic"))
    if any(target is not None for target in result.tonicization_targets[-2:]):
        issues.append(("CM047", "Destination cadence cannot be tonicization metadata"))
    if any(source is not None for source in result.modal_sources[-2:]):
        issues.append(("CM047", "Destination cadence cannot be borrowed"))
    if result.effective_rhythm[-1] is not RhythmState.ONSET:
        issues.append(("CM047", "Destination tonic must be a newly articulated onset"))
    return tuple(issues)
