from __future__ import annotations

from collections.abc import Container
from functools import cache
from itertools import pairwise, product

from ._optional_cp import cp_model
from .borrowed_seventh_runtime import _v29_chord_rows
from .modal_mixture import (
    NO_MODAL_SOURCE,
    ModalSource,
    borrowed_seventh_pitch_classes,
    borrowed_triad_pitch_classes,
    canonical_modal_source,
    supported_borrowed_degrees,
    supported_borrowed_seventh_degrees,
)
from .models import GenerationResult, GenerationSpec
from .modulation_runtime import _add_modulated_harmony_motion_constraints
from .satb import (
    ALTO_HIGH,
    ALTO_LOW,
    MAX_UPPER_SPACING,
    TENOR_HIGH,
    TENOR_LOW,
    SatbGenerationResult,
    SatbVariables,
    _add_expanded_harmony_motion_constraints,
    _parallel_rows,
    _pitches_for_pitch_classes,
    _satb_chord_rows,
)
from .secondary_leading_tone import (
    SecondaryLeadingToneSeventhQuality,
    secondary_leading_tone_seventh_pitch_class_variants,
    secondary_leading_tone_seventh_pitch_classes,
    secondary_leading_tone_seventh_qualities,
    secondary_leading_tone_seventh_support_degree,
    secondary_leading_tone_support_degree,
    secondary_leading_tone_triad_pitch_classes,
    supported_secondary_leading_tone_seventh_targets,
    supported_secondary_leading_tone_targets,
)
from .secondary_leading_tone_complete_compiler import (
    secondary_seventh_outer_pitches_in_range,
)
from .secondary_leading_tone_runtime import (
    _add_borrowed_source_leading_constraints,
    _add_secondary_tendency_constraints,
    secondary_leading_tone_modulation_verification_issues,
    secondary_leading_tone_satb_verification_issues,
)
from .semantic_dispatch import (
    ContextualHarmony,
    ContextualHarmonyFamily,
    SemanticDispatch,
    merge_semantic_dispatch,
)
from .theory import NO_TONICIZATION_TARGET, ChordKind, Key

ChordRow = tuple[int, int, int, int, int, int, int, int, int]
FunctionRow = tuple[int, int, int, int, int, int, int, int, int, int, int, int, int]

QUALITY_NONE = 0
QUALITY_FULLY_DIMINISHED = 1
QUALITY_HALF_DIMINISHED = 2


def _quality_code(quality: SecondaryLeadingToneSeventhQuality) -> int:
    return (
        QUALITY_FULLY_DIMINISHED
        if quality is SecondaryLeadingToneSeventhQuality.FULLY_DIMINISHED
        else QUALITY_HALF_DIMINISHED
    )


def _quality_from_code(code: int) -> SecondaryLeadingToneSeventhQuality | None:
    if code == QUALITY_FULLY_DIMINISHED:
        return SecondaryLeadingToneSeventhQuality.FULLY_DIMINISHED
    if code == QUALITY_HALF_DIMINISHED:
        return SecondaryLeadingToneSeventhQuality.HALF_DIMINISHED
    return None


@cache
def _v212_chord_rows(
    key: Key,
    progression_graph: tuple[tuple[int, ...], ...],
    expanded_harmony: bool,
    tonicization_enabled: bool,
    modal_mixture_enabled: bool,
    secondary_triads_enabled: bool,
    secondary_sevenths_enabled: bool,
) -> tuple[ChordRow, ...]:
    """Extend v2.11 with both certified qualities and all seventh inversions."""
    if modal_mixture_enabled and expanded_harmony:
        rows: list[ChordRow] = list(_v29_chord_rows(key, tonicization_enabled))
    else:
        rows = list(
            _satb_chord_rows(
                key,
                expanded_harmony,
                tonicization_enabled,
                modal_mixture_enabled,
            )
        )

    if secondary_triads_enabled:
        for target in supported_secondary_leading_tone_targets(key, progression_graph):
            support = secondary_leading_tone_support_degree(key, target, progression_graph)
            support_triad = key.triad_pitch_classes(support)
            secondary = secondary_leading_tone_triad_pitch_classes(key, target)
            root, third, diminished_fifth = secondary
            for pcs in product(secondary, repeat=4):
                if set(pcs) != set(secondary):
                    continue
                if (
                    pcs.count(root) != 1
                    or pcs.count(diminished_fifth) != 1
                    or pcs.count(third) != 2
                ):
                    continue
                if pcs[0] not in support_triad or pcs[3] not in support_triad:
                    continue
                inversion = secondary.index(pcs[3])
                rows.append(
                    (
                        support,
                        int(ChordKind.TRIAD),
                        inversion,
                        target,
                        NO_MODAL_SOURCE,
                        pcs[0],
                        pcs[1],
                        pcs[2],
                        pcs[3],
                    )
                )

    if secondary_sevenths_enabled:
        for target in supported_secondary_leading_tone_seventh_targets(
            key,
            progression_graph,
        ):
            for quality, secondary in secondary_leading_tone_seventh_pitch_class_variants(
                key,
                target,
            ):
                try:
                    support = secondary_leading_tone_seventh_support_degree(
                        key,
                        target,
                        progression_graph,
                        quality,
                    )
                except ValueError:
                    continue
                for pcs in product(secondary, repeat=4):
                    if set(pcs) != set(secondary) or len(set(pcs)) != 4:
                        continue
                    inversion = secondary.index(pcs[3])
                    rows.append(
                        (
                            support,
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
    return tuple(rows)


@cache
def _v212_function_rows(
    key: Key,
    progression_graph: tuple[tuple[int, ...], ...],
    expanded_harmony: bool,
    tonicization_enabled: bool,
    modal_mixture_enabled: bool,
    secondary_triads_enabled: bool,
    secondary_sevenths_enabled: bool,
) -> tuple[FunctionRow, ...]:
    """Attach exact function and quality flags without trusting serialized labels."""
    output: list[FunctionRow] = []
    triad_targets = set(supported_secondary_leading_tone_targets(key, progression_graph))
    seventh_targets = set(
        supported_secondary_leading_tone_seventh_targets(key, progression_graph)
    )
    for row in _v212_chord_rows(
        key,
        progression_graph,
        expanded_harmony,
        tonicization_enabled,
        modal_mixture_enabled,
        secondary_triads_enabled,
        secondary_sevenths_enabled,
    ):
        degree, raw_kind, _inversion, target, source, *pcs = row
        kind = ChordKind(raw_kind)
        applied = False
        secondary_triad = False
        secondary_seventh = False
        quality_code = QUALITY_NONE
        if target != NO_TONICIZATION_TARGET and source == NO_MODAL_SOURCE:
            if (
                tonicization_enabled
                and kind is ChordKind.SEVENTH
                and target in key.applied_dominant_targets
            ):
                expected = key.applied_dominant_seventh_pitch_classes(target)
                applied = (
                    degree == key.applied_dominant_root_degree(target)
                    and set(pcs) == set(expected)
                    and len(set(pcs)) == 4
                )
            if (
                secondary_triads_enabled
                and kind is ChordKind.TRIAD
                and target in triad_targets
            ):
                expected_triad = secondary_leading_tone_triad_pitch_classes(key, target)
                secondary_triad = (
                    degree
                    == secondary_leading_tone_support_degree(
                        key,
                        target,
                        progression_graph,
                    )
                    and set(pcs) == set(expected_triad)
                )
            if (
                secondary_sevenths_enabled
                and kind is ChordKind.SEVENTH
                and target in seventh_targets
                and not applied
            ):
                for quality, expected_seventh in (
                    secondary_leading_tone_seventh_pitch_class_variants(key, target)
                ):
                    try:
                        expected_support = secondary_leading_tone_seventh_support_degree(
                            key,
                            target,
                            progression_graph,
                            quality,
                        )
                    except ValueError:
                        continue
                    if (
                        degree == expected_support
                        and set(pcs) == set(expected_seventh)
                        and len(set(pcs)) == 4
                    ):
                        secondary_seventh = True
                        quality_code = _quality_code(quality)
                        break
        output.append(
            (
                *row,
                int(applied),
                int(secondary_triad),
                int(secondary_seventh),
                quality_code,
            )
        )
    return tuple(output)


@cache
def _secondary_seventh_role_rows(
    key: Key,
    progression_graph: tuple[tuple[int, ...], ...],
) -> tuple[tuple[int, int, int, int, int, int, int, int, int], ...]:
    """Map exact quality/target identity to role flags and exact resolution deltas."""
    rows: list[tuple[int, int, int, int, int, int, int, int, int]] = []
    supported = set(
        supported_secondary_leading_tone_seventh_targets(key, progression_graph)
    )
    for degree in range(7):
        for target in range(NO_TONICIZATION_TARGET + 1):
            for quality_code in (
                QUALITY_NONE,
                QUALITY_FULLY_DIMINISHED,
                QUALITY_HALF_DIMINISHED,
            ):
                root_pc: int | None = None
                fifth_pc: int | None = None
                seventh_pc: int | None = None
                fifth_delta = 0
                seventh_delta = 0
                quality = _quality_from_code(quality_code)
                if quality is not None and target in supported:
                    if quality in secondary_leading_tone_seventh_qualities(key, target):
                        try:
                            support = secondary_leading_tone_seventh_support_degree(
                                key,
                                target,
                                progression_graph,
                                quality,
                            )
                        except ValueError:
                            support = -1
                        if degree == support:
                            tones = secondary_leading_tone_seventh_pitch_classes(
                                key,
                                target,
                                quality,
                            )
                            root_pc = tones[0]
                            fifth_pc = tones[2]
                            seventh_pc = tones[3]
                            fifth_delta = -1 if key.triad_quality(target) == "major" else -2
                            seventh_delta = (
                                -1
                                if quality
                                is SecondaryLeadingToneSeventhQuality.FULLY_DIMINISHED
                                else -2
                            )
                for pc in range(12):
                    root_flag = int(root_pc is not None and pc == root_pc)
                    fifth_flag = int(fifth_pc is not None and pc == fifth_pc)
                    seventh_flag = int(seventh_pc is not None and pc == seventh_pc)
                    rows.append(
                        (
                            degree,
                            target,
                            quality_code,
                            pc,
                            root_flag,
                            fifth_flag,
                            fifth_delta if fifth_flag else 0,
                            seventh_flag,
                            seventh_delta if seventh_flag else 0,
                        )
                    )
    return tuple(rows)


def add_secondary_leading_tone_seventh_satb_constraints(
    model: cp_model.CpModel,
    spec: GenerationSpec,
    chord: list[cp_model.IntVar],
    melody_note: list[cp_model.IntVar],
    bass_note: list[cp_model.IntVar],
) -> SatbVariables:
    """Compile the v2.12 complete secondary leading-tone seventh vocabulary."""
    if not (
        spec.secondary_leading_tone_enabled
        or spec.secondary_leading_tone_seventh_enabled
    ):
        raise ValueError("v2.12 runtime requires a secondary leading-tone feature")
    if spec.secondary_leading_tone_seventh_enabled and not spec.expanded_harmony_enabled:
        raise ValueError(
            "v2.12 secondary leading-tone sevenths require expanded harmony"
        )

    if spec.secondary_leading_tone_seventh_enabled:
        soprano_domain = secondary_seventh_outer_pitches_in_range(
            spec,
            spec.melody_low,
            spec.melody_high,
        )
        bass_domain = secondary_seventh_outer_pitches_in_range(
            spec,
            spec.bass_low,
            spec.bass_high,
        )
    else:
        soprano_domain = (
            spec.context_pitches_in_range(spec.melody_low, spec.melody_high)
            if spec.modulation_enabled
            else spec.tonal_key.pitches_in_range(spec.melody_low, spec.melody_high)
        )
        bass_domain = (
            spec.context_pitches_in_range(spec.bass_low, spec.bass_high)
            if spec.modulation_enabled
            else spec.tonal_key.pitches_in_range(spec.bass_low, spec.bass_high)
        )

    inner_pitch_classes: set[int] = set()
    for key in spec.context_keys:
        inner_pitch_classes.update(key.pitch_classes)
        if spec.tonicization_enabled:
            for target in key.applied_dominant_targets:
                inner_pitch_classes.update(
                    key.applied_dominant_seventh_pitch_classes(target)
                )
        if spec.modal_mixture_enabled:
            source = canonical_modal_source(key)
            for degree in supported_borrowed_degrees(key):
                inner_pitch_classes.update(
                    borrowed_triad_pitch_classes(key, degree, source)
                )
            if spec.expanded_harmony_enabled:
                for degree in supported_borrowed_seventh_degrees(key):
                    inner_pitch_classes.update(
                        borrowed_seventh_pitch_classes(key, degree, source)
                    )
        if spec.secondary_leading_tone_enabled:
            for target in supported_secondary_leading_tone_targets(
                key,
                spec.progression_graph,
            ):
                inner_pitch_classes.update(
                    secondary_leading_tone_triad_pitch_classes(key, target)
                )
        if spec.secondary_leading_tone_seventh_enabled:
            for target in supported_secondary_leading_tone_seventh_targets(
                key,
                spec.progression_graph,
            ):
                for _quality, tones in secondary_leading_tone_seventh_pitch_class_variants(
                    key,
                    target,
                ):
                    inner_pitch_classes.update(tones)

    alto_domain = _pitches_for_pitch_classes(ALTO_LOW, ALTO_HIGH, inner_pitch_classes)
    tenor_domain = _pitches_for_pitch_classes(TENOR_LOW, TENOR_HIGH, inner_pitch_classes)
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
        model.new_int_var(0, 3, f"chord_inversion_{beat}")
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
        for kind_var in chord_kind:
            model.add(kind_var == int(ChordKind.TRIAD))

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

    if spec.modulation_enabled:
        boundary = spec.modulation_boundary_beat
        if boundary is None:
            raise ValueError("Validated modulation spec lost modulation_boundary_beat")
        reserved = {0, boundary - 1, spec.total_beats - 2, spec.total_beats - 1}
        for beat in reserved:
            model.add(tonicization_target[beat] == NO_TONICIZATION_TARGET)
            model.add(modal_source[beat] == NO_MODAL_SOURCE)
        model.add(chord_kind[0] == int(ChordKind.TRIAD))
        model.add(chord_kind[boundary - 1] == int(ChordKind.TRIAD))
    else:
        model.add(modal_source[-1] == NO_MODAL_SOURCE)
        if spec.require_authentic_cadence:
            model.add(tonicization_target[0] == NO_TONICIZATION_TARGET)
            if spec.total_beats >= 2:
                model.add(tonicization_target[-2] == NO_TONICIZATION_TARGET)
                model.add(modal_source[-2] == NO_MODAL_SOURCE)

    applied_flags: list[cp_model.IntVar] = []
    secondary_triad_flags: list[cp_model.IntVar] = []
    secondary_seventh_flags: list[cp_model.IntVar] = []
    secondary_quality: list[cp_model.IntVar] = []
    pitch_classes: list[list[cp_model.IntVar]] = []
    for beat in range(spec.total_beats):
        strong_step = beat * spec.subdivisions_per_beat
        model.add(soprano[beat] == melody_note[strong_step])
        model.add_allowed_assignments([soprano[beat]], [(note,) for note in soprano_domain])
        model.add_allowed_assignments([bass_note[beat]], [(note,) for note in bass_domain])
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

        applied = model.new_bool_var(f"applied_dominant_{beat}")
        secondary_triad = model.new_bool_var(f"secondary_leading_tone_{beat}")
        secondary_seventh = model.new_bool_var(
            f"secondary_leading_tone_seventh_{beat}"
        )
        quality = model.new_int_var(
            QUALITY_NONE,
            QUALITY_HALF_DIMINISHED,
            f"secondary_leading_tone_seventh_quality_{beat}",
        )
        applied_flags.append(applied)
        secondary_triad_flags.append(secondary_triad)
        secondary_seventh_flags.append(secondary_seventh)
        secondary_quality.append(quality)
        model.add_allowed_assignments(
            [
                chord[beat],
                chord_kind[beat],
                chord_inversion[beat],
                tonicization_target[beat],
                modal_source[beat],
                *pcs,
                applied,
                secondary_triad,
                secondary_seventh,
                quality,
            ],
            _v212_function_rows(
                spec.active_key_at_beat(beat),
                spec.progression_graph,
                spec.expanded_harmony_enabled,
                spec.tonicization_enabled,
                spec.modal_mixture_enabled,
                spec.secondary_leading_tone_enabled,
                spec.secondary_leading_tone_seventh_enabled,
            ),
        )

    if spec.minimum_applied_dominants:
        model.add(sum(applied_flags) >= spec.minimum_applied_dominants)
    if spec.minimum_secondary_leading_tone_chords:
        model.add(
            sum(secondary_triad_flags) >= spec.minimum_secondary_leading_tone_chords
        )
    if spec.minimum_secondary_leading_tone_seventh_chords:
        model.add(
            sum(secondary_seventh_flags)
            >= spec.minimum_secondary_leading_tone_seventh_chords
        )
    model.add(tonicization_target[-1] == NO_TONICIZATION_TARGET)

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
                    if left_note % 12 != key.leading_tone_pc or right_note == left_note + 1
                ]
                model.add_allowed_assignments([left_var, right_var], allowed)

        if spec.modulation_enabled:
            destination = spec.modulation_destination
            if destination is None:
                raise ValueError("Validated modulation spec lost destination identity")
            cadence_beat = spec.total_beats - 2
            for voice_vars, domain in (
                (soprano, soprano_domain),
                (alto, alto_domain),
                (tenor, tenor_domain),
                (bass_note, bass_domain),
            ):
                terminal_rows = [
                    (left_note, right_note)
                    for left_note in domain
                    for right_note in domain
                    if left_note % 12 != destination.leading_tone_pc
                    or right_note == left_note + 1
                ]
                model.add_allowed_assignments(
                    [voice_vars[cadence_beat], voice_vars[cadence_beat + 1]],
                    terminal_rows,
                )

    if spec.modulation_enabled:
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
    else:
        _add_expanded_harmony_motion_constraints(
            model,
            spec.tonal_key,
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

    if spec.modal_mixture_enabled and spec.expanded_harmony_enabled:
        _add_borrowed_source_leading_constraints(
            model,
            spec,
            chord,
            chord_kind,
            modal_source,
            pitch_classes,
            soprano,
            alto,
            tenor,
            bass_note,
        )

    if spec.secondary_leading_tone_enabled:
        _add_secondary_tendency_constraints(
            model,
            spec,
            chord,
            chord_kind,
            tonicization_target,
            modal_source,
            pitch_classes,
            soprano,
            alto,
            tenor,
            bass_note,
        )
    if spec.secondary_leading_tone_seventh_enabled:
        _add_secondary_seventh_tendency_constraints(
            model,
            spec,
            chord,
            chord_kind,
            tonicization_target,
            modal_source,
            pitch_classes,
            secondary_seventh_flags,
            secondary_quality,
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


def _add_secondary_seventh_tendency_constraints(
    model: cp_model.CpModel,
    spec: GenerationSpec,
    chord: list[cp_model.IntVar],
    chord_kind: list[cp_model.IntVar],
    tonicization_target: list[cp_model.IntVar],
    modal_source: list[cp_model.IntVar],
    pitch_classes: list[list[cp_model.IntVar]],
    secondary_seventh_flags: list[cp_model.IntVar],
    secondary_quality: list[cp_model.IntVar],
    soprano: list[cp_model.IntVar],
    alto: list[cp_model.IntVar],
    tenor: list[cp_model.IntVar],
    bass: list[cp_model.IntVar],
) -> None:
    voices = (soprano, alto, tenor, bass)
    for beat in range(spec.total_beats - 1):
        key = spec.active_key_at_beat(beat)
        rows = _secondary_seventh_role_rows(key, spec.progression_graph)
        is_secondary = secondary_seventh_flags[beat]
        model.add(chord_kind[beat] == int(ChordKind.SEVENTH)).only_enforce_if(
            is_secondary
        )
        model.add(chord[beat + 1] == tonicization_target[beat]).only_enforce_if(
            is_secondary
        )
        model.add(
            tonicization_target[beat + 1] == NO_TONICIZATION_TARGET
        ).only_enforce_if(is_secondary)
        model.add(chord_kind[beat + 1] == int(ChordKind.TRIAD)).only_enforce_if(
            is_secondary
        )
        model.add(modal_source[beat + 1] == NO_MODAL_SOURCE).only_enforce_if(
            is_secondary
        )

        for voice_index, voice in enumerate(voices):
            root_flag = model.new_bool_var(
                f"secondary_seventh_root_{beat}_{voice_index}"
            )
            fifth_flag = model.new_bool_var(
                f"secondary_seventh_dim5_{beat}_{voice_index}"
            )
            fifth_delta = model.new_int_var(
                -2,
                0,
                f"secondary_seventh_dim5_delta_{beat}_{voice_index}",
            )
            seventh_flag = model.new_bool_var(
                f"secondary_seventh_chordal7_{beat}_{voice_index}"
            )
            seventh_delta = model.new_int_var(
                -2,
                0,
                f"secondary_seventh_chordal7_delta_{beat}_{voice_index}",
            )
            model.add_allowed_assignments(
                [
                    chord[beat],
                    tonicization_target[beat],
                    secondary_quality[beat],
                    pitch_classes[beat][voice_index],
                    root_flag,
                    fifth_flag,
                    fifth_delta,
                    seventh_flag,
                    seventh_delta,
                ],
                rows,
            )
            root_resolution = model.add(voice[beat + 1] == voice[beat] + 1)
            root_resolution.only_enforce_if([is_secondary, root_flag])
            root_resolution.with_name(f"CM057.root.beat-{beat}.voice-{voice_index}")

            fifth_resolution = model.add(
                voice[beat + 1] == voice[beat] + fifth_delta
            )
            fifth_resolution.only_enforce_if([is_secondary, fifth_flag])
            fifth_resolution.with_name(
                f"CM057.diminished-fifth.beat-{beat}.voice-{voice_index}"
            )

            seventh_resolution = model.add(
                voice[beat + 1] == voice[beat] + seventh_delta
            )
            seventh_resolution.only_enforce_if([is_secondary, seventh_flag])
            seventh_resolution.with_name(
                f"CM057.chordal-seventh.beat-{beat}.voice-{voice_index}"
            )


def _voice_pitch_classes(
    result: SatbGenerationResult,
    beat: int,
) -> tuple[int, int, int, int]:
    return (
        result.soprano[beat] % 12,
        result.alto[beat] % 12,
        result.tenor[beat] % 12,
        result.bass[beat] % 12,
    )


def _exact_applied_dominant(result: SatbGenerationResult, beat: int) -> bool:
    spec = result.spec
    if not spec.tonicization_enabled or not 0 <= beat < spec.total_beats:
        return False
    if not (
        len(result.tonicization_targets) > beat
        and len(result.chord_kinds) > beat
        and len(result.chord_degrees) > beat
        and len(result.chord_inversions) > beat
        and len(result.soprano) > beat
        and len(result.alto) > beat
        and len(result.tenor) > beat
        and len(result.bass) > beat
    ):
        return False
    target = result.tonicization_targets[beat]
    if target is None:
        return False
    try:
        kind = ChordKind.parse(result.chord_kinds[beat])
    except ValueError:
        return False
    if kind is not ChordKind.SEVENTH:
        return False
    key = spec.active_key_at_beat(beat)
    if target not in key.applied_dominant_targets:
        return False
    if result.chord_degrees[beat] != key.applied_dominant_root_degree(target):
        return False
    expected = key.applied_dominant_seventh_pitch_classes(target)
    pcs = _voice_pitch_classes(result, beat)
    if set(pcs) != set(expected) or len(set(pcs)) != 4:
        return False
    inversion = result.chord_inversions[beat]
    if not 0 <= inversion <= 2:
        return False
    return result.bass[beat] % 12 == expected[inversion]


def _secondary_seventh_candidate_beats(result: GenerationResult) -> set[int]:
    if not isinstance(result, SatbGenerationResult):
        return set()
    spec = result.spec
    if not spec.secondary_leading_tone_seventh_enabled:
        return set()
    if not (
        len(result.tonicization_targets)
        == len(result.chord_kinds)
        == spec.total_beats
    ):
        return set()
    beats: set[int] = set()
    for beat, (target, raw_kind) in enumerate(
        zip(result.tonicization_targets, result.chord_kinds, strict=True)
    ):
        if target is None:
            continue
        try:
            kind = ChordKind.parse(raw_kind)
        except ValueError:
            continue
        if kind is ChordKind.SEVENTH and not _exact_applied_dominant(result, beat):
            beats.add(beat)
    return beats


def reconstruct_secondary_leading_tone_seventh(
    result: GenerationResult,
    beat: int,
) -> tuple[SecondaryLeadingToneSeventhQuality, tuple[int, int, int, int]] | None:
    """Independently reconstruct exact v2.12 secondary-seventh identity from artifact data."""
    if not isinstance(result, SatbGenerationResult):
        return None
    spec = result.spec
    if not spec.secondary_leading_tone_seventh_enabled or not 0 <= beat < spec.total_beats:
        return None
    if not (
        len(result.tonicization_targets) > beat
        and len(result.chord_kinds) > beat
        and len(result.chord_degrees) > beat
        and len(result.chord_inversions) > beat
        and len(result.soprano) > beat
        and len(result.alto) > beat
        and len(result.tenor) > beat
        and len(result.bass) > beat
    ):
        return None
    target = result.tonicization_targets[beat]
    if target is None:
        return None
    try:
        kind = ChordKind.parse(result.chord_kinds[beat])
    except ValueError:
        return None
    if kind is not ChordKind.SEVENTH or _exact_applied_dominant(result, beat):
        return None
    if result.modal_sources and (
        len(result.modal_sources) <= beat or result.modal_sources[beat] is not None
    ):
        return None
    key = spec.active_key_at_beat(beat)
    if target not in supported_secondary_leading_tone_seventh_targets(
        key,
        spec.progression_graph,
    ):
        return None
    pcs = _voice_pitch_classes(result, beat)
    if len(set(pcs)) != 4:
        return None
    inversion = result.chord_inversions[beat]
    if not 0 <= inversion <= 3:
        return None
    for quality, expected in secondary_leading_tone_seventh_pitch_class_variants(
        key,
        target,
    ):
        try:
            support = secondary_leading_tone_seventh_support_degree(
                key,
                target,
                spec.progression_graph,
                quality,
            )
        except ValueError:
            continue
        if result.chord_degrees[beat] != support:
            continue
        if set(pcs) != set(expected):
            continue
        if result.bass[beat] % 12 != expected[inversion]:
            continue
        return quality, expected
    return None


def _secondary_seventh_interpretation(
    result: GenerationResult,
    beat: int,
) -> ContextualHarmony | None:
    reconstruction = reconstruct_secondary_leading_tone_seventh(result, beat)
    if reconstruction is None or not isinstance(result, SatbGenerationResult):
        return None
    _quality, expected = reconstruction
    target = result.tonicization_targets[beat]
    if target is None:
        return None
    key = result.spec.active_key_at_beat(beat)
    qualities: set[str] = set()
    for quality, candidate in secondary_leading_tone_seventh_pitch_class_variants(
        key,
        target,
    ):
        try:
            support = secondary_leading_tone_seventh_support_degree(
                key,
                target,
                result.spec.progression_graph,
                quality,
            )
        except ValueError:
            continue
        if support == result.chord_degrees[beat] and set(candidate) == set(expected):
            qualities.add(quality.value)
    return ContextualHarmony(
        beat=beat,
        family=ContextualHarmonyFamily.SECONDARY_LEADING_TONE_SEVENTH,
        active_key=key,
        support_degree=result.chord_degrees[beat],
        pitch_classes=expected,
        inversion=result.chord_inversions[beat],
        target_degree=target,
        qualities=frozenset(qualities),
    )


def _secondary_seventh_dispatch(
    result: GenerationResult,
    inherited: SemanticDispatch | None,
) -> SemanticDispatch:
    interpretations = (
        interpretation
        for beat in range(result.spec.total_beats)
        if (interpretation := _secondary_seventh_interpretation(result, beat)) is not None
    )
    return merge_semantic_dispatch(inherited, interpretations)


def secondary_seventh_context_verification_issues(
    spec: GenerationSpec,
    beat: int,
    *,
    target: int,
    supported_targets: Container[int],
    modal_overlap: bool,
) -> tuple[tuple[str, str], ...]:
    """Check only CM055 placement and contextual eligibility for one candidate beat."""

    if not 0 <= beat < spec.total_beats:
        raise ValueError(f"Beat {beat} is outside 0..{spec.total_beats - 1}")

    issues: list[tuple[str, str]] = []
    if target not in supported_targets:
        issues.append(
            (
                "CM055",
                f"Beat {beat}: target {target} is not a supported secondary leading-tone "
                "seventh target",
            )
        )
    if beat == spec.total_beats - 1:
        issues.append(
            ("CM055", f"Beat {beat}: secondary leading-tone seventh cannot be final")
        )
    if spec.modulation_enabled:
        boundary = spec.modulation_boundary_beat
        if boundary is not None and beat in {
            0,
            boundary - 1,
            spec.total_beats - 2,
            spec.total_beats - 1,
        }:
            issues.append(
                (
                    "CM055",
                    f"Beat {beat}: secondary leading-tone seventh occupies a certified anchor",
                )
            )
    elif spec.require_authentic_cadence and beat in {0, spec.total_beats - 2}:
        issues.append(
            (
                "CM055",
                f"Beat {beat}: secondary leading-tone seventh occupies a cadence anchor",
            )
        )
    if modal_overlap:
        issues.append(
            (
                "CM055",
                f"Beat {beat}: secondary leading-tone seventh and modal borrowing overlap",
            )
        )
    return tuple(issues)


def secondary_leading_tone_seventh_satb_verification_issues(
    result: GenerationResult,
    *,
    semantic_dispatch: SemanticDispatch | None = None,
) -> tuple[tuple[str, str], ...]:
    dispatch = _secondary_seventh_dispatch(result, semantic_dispatch)
    base = secondary_leading_tone_satb_verification_issues(
        result,
        semantic_dispatch=dispatch,
    )
    if not isinstance(result, SatbGenerationResult):
        return base
    spec = result.spec
    if not spec.secondary_leading_tone_seventh_enabled:
        return base

    candidates = _secondary_seventh_candidate_beats(result)
    issues = list(base)

    if not result.tonicization_targets:
        issues.append(
            ("CM055", "Enabled secondary leading-tone sevenths require target metadata")
        )
        return tuple(issues)
    if not (
        len(result.tonicization_targets)
        == len(result.chord_degrees)
        == len(result.chord_kinds)
        == len(result.chord_inversions)
        == spec.total_beats
        and all(
            len(voice) == spec.total_beats
            for voice in (result.soprano, result.alto, result.tenor, result.bass)
        )
    ):
        issues.append(
            ("CM055", "Secondary leading-tone seventh metadata/voices must match total_beats")
        )
        return tuple(issues)

    try:
        kinds = tuple(ChordKind.parse(item) for item in result.chord_kinds)
    except ValueError:
        return tuple(issues)

    applied_count = sum(
        _exact_applied_dominant(result, beat) for beat in range(spec.total_beats)
    )
    if applied_count < spec.minimum_applied_dominants:
        issues.append(("CM037", "Serialized harmony misses minimum_applied_dominants"))

    exact_secondary_count = 0
    for beat in sorted(candidates):
        target = result.tonicization_targets[beat]
        if target is None:
            continue
        key = spec.active_key_at_beat(beat)
        supported = set(
            supported_secondary_leading_tone_seventh_targets(
                key,
                spec.progression_graph,
            )
        )
        context_issues = secondary_seventh_context_verification_issues(
            spec,
            beat,
            target=target,
            supported_targets=supported,
            modal_overlap=bool(
                result.modal_sources and result.modal_sources[beat] is not None
            ),
        )
        issues.extend(context_issues)
        context_ok = not context_issues

        pcs = _voice_pitch_classes(result, beat)
        matched_quality: SecondaryLeadingToneSeventhQuality | None = None
        expected: tuple[int, int, int, int] | None = None
        if target in supported:
            for quality, candidate_pcs in secondary_leading_tone_seventh_pitch_class_variants(
                key,
                target,
            ):
                try:
                    support = secondary_leading_tone_seventh_support_degree(
                        key,
                        target,
                        spec.progression_graph,
                        quality,
                    )
                except ValueError:
                    continue
                if result.chord_degrees[beat] != support:
                    continue
                if set(pcs) == set(candidate_pcs) and len(set(pcs)) == 4:
                    matched_quality = quality
                    expected = candidate_pcs
                    break

            if matched_quality is None:
                root, third, fifth = secondary_leading_tone_triad_pitch_classes(key, target)
                raw_half = (root, third, fifth, (root + 10) % 12)
                if (
                    set(pcs) == set(raw_half)
                    and SecondaryLeadingToneSeventhQuality.HALF_DIMINISHED
                    not in secondary_leading_tone_seventh_qualities(key, target)
                ):
                    issues.append(
                        (
                            "CM055",
                            f"Beat {beat}: half-diminished quality is not eligible for minor "
                            f"target {target} in {key}",
                        )
                    )
                    context_ok = False

        if matched_quality is None or expected is None:
            issues.append(
                (
                    "CM056",
                    f"Beat {beat}: secondary leading-tone seventh is not an exact certified "
                    "fully- or half-diminished target-derived sonority",
                )
            )
        else:
            support = secondary_leading_tone_seventh_support_degree(
                key,
                target,
                spec.progression_graph,
                matched_quality,
            )
            if result.chord_degrees[beat] != support:
                issues.append(
                    (
                        "CM055",
                        f"Beat {beat}: seventh support degree does not match target "
                        f"{target} in {key}",
                    )
                )
                context_ok = False

        inversion = result.chord_inversions[beat]
        inversion_ok = 0 <= inversion <= 3
        if not inversion_ok:
            issues.append(
                ("CM056", f"Beat {beat}: secondary seventh inversion is outside 0..3")
            )
        elif expected is not None and result.bass[beat] % 12 != expected[inversion]:
            issues.append(
                (
                    "CM056",
                    f"Beat {beat}: secondary leading-tone seventh inversion mismatches bass",
                )
            )
            inversion_ok = False

        realization_ok = matched_quality is not None and expected is not None
        if context_ok and realization_ok and inversion_ok:
            exact_secondary_count += 1

        if beat + 1 >= spec.total_beats:
            issues.append(
                ("CM057", f"Beat {beat}: secondary leading-tone seventh has no resolution")
            )
            continue
        if result.chord_degrees[beat + 1] != target:
            issues.append(
                (
                    "CM057",
                    f"Beat {beat}: secondary leading-tone seventh misses declared target",
                )
            )
        if result.tonicization_targets[beat + 1] is not None:
            issues.append(
                ("CM057", f"Beat {beat}: target chord cannot carry local-target metadata")
            )
        if kinds[beat + 1] is not ChordKind.TRIAD:
            issues.append(("CM057", f"Beat {beat}: target chord must be triadic"))
        if result.modal_sources and result.modal_sources[beat + 1] is not None:
            issues.append(("CM057", f"Beat {beat}: target chord must be unborrowed"))

        if expected is None or matched_quality is None:
            continue
        source_voices = (
            result.soprano[beat],
            result.alto[beat],
            result.tenor[beat],
            result.bass[beat],
        )
        destination_voices = (
            result.soprano[beat + 1],
            result.alto[beat + 1],
            result.tenor[beat + 1],
            result.bass[beat + 1],
        )
        issues.extend(
            secondary_seventh_resolution_verification_issues(
                source_voices,
                destination_voices,
                expected=expected,
                quality=matched_quality,
                target_is_major=key.triad_quality(target) == "major",
                beat=beat,
            )
        )

    if exact_secondary_count < spec.minimum_secondary_leading_tone_seventh_chords:
        issues.append(
            (
                "CM055",
                "Serialized harmony does not meet "
                "minimum_secondary_leading_tone_seventh_chords",
            )
        )
    return tuple(issues)


def secondary_seventh_resolution_verification_issues(
    source: tuple[int, int, int, int],
    destination: tuple[int, int, int, int],
    *,
    expected: tuple[int, int, int, int],
    quality: SecondaryLeadingToneSeventhQuality,
    target_is_major: bool,
    beat: int | None = None,
) -> tuple[tuple[str, str], ...]:
    """Classify the three voice-specific secondary-seventh tendency motions."""

    root, _third, diminished_fifth, chordal_seventh = expected
    fifth_delta = -1 if target_is_major else -2
    seventh_delta = (
        -1
        if quality is SecondaryLeadingToneSeventhQuality.FULLY_DIMINISHED
        else -2
    )
    prefix = "" if beat is None else f" beat {beat}"
    issues: list[tuple[str, str]] = []
    for label, before, after in zip(
        ("soprano", "alto", "tenor", "bass"),
        source,
        destination,
        strict=True,
    ):
        if before % 12 == root and after != before + 1:
            issues.append(
                (
                    "CM057",
                    f"{label}{prefix}: local leading tone does not resolve upward by semitone",
                )
            )
        if before % 12 == diminished_fifth and after - before != fifth_delta:
            issues.append(
                (
                    "CM057",
                    f"{label}{prefix}: diminished fifth does not resolve by its exact "
                    "target-dependent downward step",
                )
            )
        if before % 12 == chordal_seventh and after - before != seventh_delta:
            issues.append(
                (
                    "CM057",
                    f"{label}{prefix}: chordal seventh does not resolve by its exact "
                    "quality-dependent downward step",
                )
            )
    return tuple(issues)


def secondary_leading_tone_seventh_modulation_verification_issues(
    result: GenerationResult,
    *,
    semantic_dispatch: SemanticDispatch | None = None,
) -> tuple[tuple[str, str], ...]:
    dispatch = _secondary_seventh_dispatch(result, semantic_dispatch)
    return secondary_leading_tone_modulation_verification_issues(
        result,
        semantic_dispatch=dispatch,
    )
