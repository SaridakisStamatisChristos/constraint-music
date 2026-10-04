from __future__ import annotations

from functools import cache
from itertools import pairwise, product

from ortools.sat.python import cp_model

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
    secondary_leading_tone_seventh_pitch_classes,
    secondary_leading_tone_seventh_support_degree,
    secondary_leading_tone_support_degree,
    secondary_leading_tone_triad_pitch_classes,
    supported_secondary_leading_tone_seventh_targets,
    supported_secondary_leading_tone_targets,
)
from .secondary_leading_tone_runtime import (
    _add_borrowed_source_leading_constraints,
    _add_secondary_tendency_constraints,
    secondary_leading_tone_modulation_verification_issues,
    secondary_leading_tone_satb_verification_issues,
)
from .theory import NO_TONICIZATION_TARGET, ChordKind, Key


ChordRow = tuple[int, int, int, int, int, int, int, int, int]
FunctionRow = tuple[int, int, int, int, int, int, int, int, int, int, int, int]


@cache
def _v211_chord_rows(
    key: Key,
    progression_graph: tuple[tuple[int, ...], ...],
    expanded_harmony: bool,
    tonicization_enabled: bool,
    modal_mixture_enabled: bool,
    secondary_triads_enabled: bool,
    secondary_sevenths_enabled: bool,
) -> tuple[ChordRow, ...]:
    """Extend the verified v2.10 row model with fully diminished vii°7/x rows."""
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
            support = secondary_leading_tone_seventh_support_degree(
                key,
                target,
                progression_graph,
            )
            support_triad = key.triad_pitch_classes(support)
            secondary = secondary_leading_tone_seventh_pitch_classes(key, target)
            for pcs in product(secondary, repeat=4):
                if len(set(pcs)) != 4:
                    continue
                if pcs[0] not in support_triad or pcs[3] not in support_triad:
                    continue
                inversion = secondary.index(pcs[3])
                if inversion > 2:
                    continue
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
def _v211_function_rows(
    key: Key,
    progression_graph: tuple[tuple[int, ...], ...],
    expanded_harmony: bool,
    tonicization_enabled: bool,
    modal_mixture_enabled: bool,
    secondary_triads_enabled: bool,
    secondary_sevenths_enabled: bool,
) -> tuple[FunctionRow, ...]:
    """Attach exact functional flags without adding a serialized function-state axis."""
    output: list[FunctionRow] = []
    triad_targets = set(supported_secondary_leading_tone_targets(key, progression_graph))
    seventh_targets = set(
        supported_secondary_leading_tone_seventh_targets(key, progression_graph)
    )
    for row in _v211_chord_rows(
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
            ):
                expected_seventh = secondary_leading_tone_seventh_pitch_classes(key, target)
                secondary_seventh = (
                    degree
                    == secondary_leading_tone_seventh_support_degree(
                        key,
                        target,
                        progression_graph,
                    )
                    and set(pcs) == set(expected_seventh)
                    and len(set(pcs)) == 4
                )
        output.append(
            (*row, int(applied), int(secondary_triad), int(secondary_seventh))
        )
    return tuple(output)


@cache
def _secondary_seventh_role_rows(
    key: Key,
    progression_graph: tuple[tuple[int, ...], ...],
) -> tuple[tuple[int, int, int, int, int, int], ...]:
    supported = set(
        supported_secondary_leading_tone_seventh_targets(key, progression_graph)
    )
    rows: list[tuple[int, int, int, int, int, int]] = []
    for degree in range(7):
        for target in range(NO_TONICIZATION_TARGET + 1):
            root_pc: int | None = None
            fifth_pc: int | None = None
            seventh_pc: int | None = None
            if target in supported:
                support = secondary_leading_tone_seventh_support_degree(
                    key,
                    target,
                    progression_graph,
                )
                if degree == support:
                    tones = secondary_leading_tone_seventh_pitch_classes(key, target)
                    root_pc = tones[0]
                    fifth_pc = tones[2]
                    seventh_pc = tones[3]
            for pc in range(12):
                rows.append(
                    (
                        degree,
                        target,
                        pc,
                        int(root_pc is not None and pc == root_pc),
                        int(fifth_pc is not None and pc == fifth_pc),
                        int(seventh_pc is not None and pc == seventh_pc),
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
    """Compile v2.11 secondary leading-tone sevenths with exact functional counting."""
    if not (
        spec.secondary_leading_tone_enabled
        or spec.secondary_leading_tone_seventh_enabled
    ):
        raise ValueError("v2.11 runtime requires a secondary leading-tone feature")
    if spec.secondary_leading_tone_seventh_enabled and not spec.expanded_harmony_enabled:
        raise ValueError(
            "v2.11 secondary leading-tone sevenths require expanded harmony"
        )

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
                inner_pitch_classes.update(
                    secondary_leading_tone_seventh_pitch_classes(key, target)
                )

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

        applied = model.new_bool_var(f"applied_dominant_{beat}")
        secondary_triad = model.new_bool_var(f"secondary_leading_tone_{beat}")
        secondary_seventh = model.new_bool_var(
            f"secondary_leading_tone_seventh_{beat}"
        )
        applied_flags.append(applied)
        secondary_triad_flags.append(secondary_triad)
        secondary_seventh_flags.append(secondary_seventh)
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
            ],
            _v211_function_rows(
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
            seventh_flag = model.new_bool_var(
                f"secondary_seventh_dim7_{beat}_{voice_index}"
            )
            model.add_allowed_assignments(
                [
                    chord[beat],
                    tonicization_target[beat],
                    pitch_classes[beat][voice_index],
                    root_flag,
                    fifth_flag,
                    seventh_flag,
                ],
                rows,
            )
            model.add(voice[beat + 1] == voice[beat] + 1).only_enforce_if(
                [is_secondary, root_flag]
            )
            model.add(voice[beat + 1] <= voice[beat] - 1).only_enforce_if(
                [is_secondary, fifth_flag]
            )
            model.add(voice[beat + 1] >= voice[beat] - 2).only_enforce_if(
                [is_secondary, fifth_flag]
            )
            model.add(voice[beat + 1] <= voice[beat] - 1).only_enforce_if(
                [is_secondary, seventh_flag]
            )
            model.add(voice[beat + 1] >= voice[beat] - 2).only_enforce_if(
                [is_secondary, seventh_flag]
            )


def _voice_pitch_classes(result: SatbGenerationResult, beat: int) -> tuple[int, int, int, int]:
    return (
        result.soprano[beat] % 12,
        result.alto[beat] % 12,
        result.tenor[beat] % 12,
        result.bass[beat] % 12,
    )


def _exact_applied_dominant(result: SatbGenerationResult, beat: int) -> bool:
    spec = result.spec
    if not spec.tonicization_enabled or beat >= spec.total_beats:
        return False
    if not result.tonicization_targets or not result.chord_kinds:
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
    if not result.chord_inversions or not 0 <= result.chord_inversions[beat] <= 2:
        return False
    return result.bass[beat] % 12 == expected[result.chord_inversions[beat]]


def _secondary_seventh_candidate_beats(result: GenerationResult) -> set[int]:
    if not isinstance(result, SatbGenerationResult):
        return set()
    spec = result.spec
    if not spec.secondary_leading_tone_seventh_enabled:
        return set()
    if not result.tonicization_targets or not result.chord_kinds:
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


def secondary_leading_tone_seventh_satb_verification_issues(
    result: GenerationResult,
) -> tuple[tuple[str, str], ...]:
    base = secondary_leading_tone_satb_verification_issues(result)
    if not isinstance(result, SatbGenerationResult):
        return base
    spec = result.spec
    if not spec.secondary_leading_tone_seventh_enabled:
        return base

    candidates = _secondary_seventh_candidate_beats(result)
    issues: list[tuple[str, str]] = []
    for rule_id, message in base:
        if rule_id in {"CM037", "CM038", "CM039", "CM040"} and any(
            message.startswith(f"Beat {beat}:")
            or message.startswith(f"soprano beat {beat}:")
            or message.startswith(f"alto beat {beat}:")
            or message.startswith(f"tenor beat {beat}:")
            or message.startswith(f"bass beat {beat}:")
            for beat in candidates
        ):
            continue
        issues.append((rule_id, message))

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
    voices = (
        ("soprano", result.soprano),
        ("alto", result.alto),
        ("tenor", result.tenor),
        ("bass", result.bass),
    )
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
        context_ok = True
        if target not in supported:
            issues.append(
                (
                    "CM055",
                    f"Beat {beat}: target {target} is not a supported secondary leading-tone "
                    "seventh target",
                )
            )
            context_ok = False
        if beat == spec.total_beats - 1:
            issues.append(
                ("CM055", f"Beat {beat}: secondary leading-tone seventh cannot be final")
            )
            context_ok = False
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
                context_ok = False
        elif spec.require_authentic_cadence and beat in {0, spec.total_beats - 2}:
            issues.append(
                (
                    "CM055",
                    f"Beat {beat}: secondary leading-tone seventh occupies a cadence anchor",
                )
            )
            context_ok = False
        if result.modal_sources and result.modal_sources[beat] is not None:
            issues.append(
                (
                    "CM055",
                    f"Beat {beat}: secondary leading-tone seventh and modal borrowing overlap",
                )
            )
            context_ok = False

        expected: tuple[int, int, int, int] | None = None
        if target in supported:
            support = secondary_leading_tone_seventh_support_degree(
                key,
                target,
                spec.progression_graph,
            )
            if result.chord_degrees[beat] != support:
                issues.append(
                    (
                        "CM055",
                        f"Beat {beat}: seventh support degree does not match target {target} in {key}",
                    )
                )
                context_ok = False
            expected = secondary_leading_tone_seventh_pitch_classes(key, target)

        pcs = _voice_pitch_classes(result, beat)
        realization_ok = expected is not None and set(pcs) == set(expected) and len(set(pcs)) == 4
        if not realization_ok:
            issues.append(
                (
                    "CM056",
                    f"Beat {beat}: secondary leading-tone seventh is not the complete fully "
                    "diminished seventh",
                )
            )
        inversion = result.chord_inversions[beat]
        inversion_ok = 0 <= inversion <= 2
        if not inversion_ok:
            issues.append(
                ("CM056", f"Beat {beat}: secondary seventh inversion is outside 0..2")
            )
        elif expected is not None and result.bass[beat] % 12 != expected[inversion]:
            issues.append(
                (
                    "CM056",
                    f"Beat {beat}: secondary leading-tone seventh inversion mismatches bass",
                )
            )
            inversion_ok = False

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

        if expected is None:
            continue
        root, _third, diminished_fifth, diminished_seventh = expected
        for label, voice in voices:
            if voice[beat] % 12 == root and voice[beat + 1] != voice[beat] + 1:
                issues.append(
                    (
                        "CM057",
                        f"{label} beat {beat}: local leading tone does not resolve upward by "
                        "semitone",
                    )
                )
            if voice[beat] % 12 == diminished_fifth:
                delta = voice[beat + 1] - voice[beat]
                if delta not in {-1, -2}:
                    issues.append(
                        (
                            "CM057",
                            f"{label} beat {beat}: diminished fifth does not resolve downward "
                            "by step",
                        )
                    )
            if voice[beat] % 12 == diminished_seventh:
                delta = voice[beat + 1] - voice[beat]
                if delta not in {-1, -2}:
                    issues.append(
                        (
                            "CM057",
                            f"{label} beat {beat}: chordal diminished seventh does not resolve "
                            "downward by step",
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


def secondary_leading_tone_seventh_modulation_verification_issues(
    result: GenerationResult,
) -> tuple[tuple[str, str], ...]:
    base = secondary_leading_tone_modulation_verification_issues(result)
    candidates = _secondary_seventh_candidate_beats(result)
    filtered: list[tuple[str, str]] = []
    for rule_id, message in base:
        if rule_id == "CM046" and any(
            message.startswith(f"Beat {beat}:") for beat in candidates
        ):
            continue
        filtered.append((rule_id, message))
    return tuple(filtered)
