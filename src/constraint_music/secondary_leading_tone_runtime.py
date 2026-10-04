from __future__ import annotations

from functools import cache
from itertools import pairwise, product

from ortools.sat.python import cp_model

from .borrowed_seventh_runtime import (
    _source_leading_rows,
    _v29_chord_rows,
    borrowed_seventh_modulation_verification_issues,
    borrowed_seventh_satb_verification_issues,
)
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
    secondary_leading_tone_support_degree,
    secondary_leading_tone_triad_pitch_classes,
    supported_secondary_leading_tone_targets,
)
from .theory import NO_TONICIZATION_TARGET, ChordKind, Key


@cache
def _v210_chord_rows(
    key: Key,
    progression_graph: tuple[tuple[int, ...], ...],
    expanded_harmony: bool,
    tonicization_enabled: bool,
    modal_mixture_enabled: bool,
) -> tuple[tuple[int, int, int, int, int, int, int, int, int], ...]:
    """Extend the verified v2.9 row table with target-bearing diminished triads."""
    if modal_mixture_enabled and expanded_harmony:
        rows = list(_v29_chord_rows(key, tonicization_enabled))
    else:
        rows = list(
            _satb_chord_rows(
                key,
                expanded_harmony,
                tonicization_enabled,
                modal_mixture_enabled,
            )
        )

    for target in supported_secondary_leading_tone_targets(key, progression_graph):
        support = secondary_leading_tone_support_degree(key, target, progression_graph)
        support_triad = key.triad_pitch_classes(support)
        secondary = secondary_leading_tone_triad_pitch_classes(key, target)
        root, third, diminished_fifth = secondary
        for pcs in product(secondary, repeat=4):
            if set(pcs) != set(secondary):
                continue
            if pcs.count(root) != 1 or pcs.count(diminished_fifth) != 1 or pcs.count(third) != 2:
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
    return tuple(rows)


@cache
def _secondary_root_flag_rows(
    key: Key,
    progression_graph: tuple[tuple[int, ...], ...],
) -> tuple[tuple[int, int, int, int, int, int], ...]:
    supported = set(supported_secondary_leading_tone_targets(key, progression_graph))
    rows: list[tuple[int, int, int, int, int, int]] = []
    for degree in range(7):
        for kind in ChordKind:
            for target in range(NO_TONICIZATION_TARGET + 1):
                root_pc: int | None = None
                fifth_pc: int | None = None
                if target in supported and kind is ChordKind.TRIAD:
                    support = secondary_leading_tone_support_degree(
                        key, target, progression_graph
                    )
                    if degree == support:
                        tones = secondary_leading_tone_triad_pitch_classes(key, target)
                        root_pc = tones[0]
                        fifth_pc = tones[2]
                for pc in range(12):
                    rows.append(
                        (
                            degree,
                            int(kind),
                            target,
                            pc,
                            int(root_pc is not None and pc == root_pc),
                            int(fifth_pc is not None and pc == fifth_pc),
                        )
                    )
    return tuple(rows)


def add_secondary_leading_tone_satb_constraints(
    model: cp_model.CpModel,
    spec: GenerationSpec,
    chord: list[cp_model.IntVar],
    melody_note: list[cp_model.IntVar],
    bass_note: list[cp_model.IntVar],
) -> SatbVariables:
    """Compile v2.10 while preserving every earlier SATB/chromatic feature boundary."""
    if not spec.secondary_leading_tone_enabled:
        raise ValueError("v2.10 runtime requires secondary_leading_tone_enabled=true")

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
                inner_pitch_classes.update(key.applied_dominant_seventh_pitch_classes(target))
        if spec.modal_mixture_enabled:
            source = canonical_modal_source(key)
            for degree in supported_borrowed_degrees(key):
                inner_pitch_classes.update(borrowed_triad_pitch_classes(key, degree, source))
            if spec.expanded_harmony_enabled:
                for degree in supported_borrowed_seventh_degrees(key):
                    inner_pitch_classes.update(
                        borrowed_seventh_pitch_classes(key, degree, source)
                    )
        for target in supported_secondary_leading_tone_targets(
            key, spec.progression_graph
        ):
            inner_pitch_classes.update(
                secondary_leading_tone_triad_pitch_classes(key, target)
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

    applied_flags: list[cp_model.IntVar] = []
    secondary_flags: list[cp_model.IntVar] = []
    for beat, target in enumerate(tonicization_target):
        has_target = model.new_bool_var(f"local_target_{beat}")
        model.add(target != NO_TONICIZATION_TARGET).only_enforce_if(has_target)
        model.add(target == NO_TONICIZATION_TARGET).only_enforce_if(has_target.negated())

        applied = model.new_bool_var(f"applied_dominant_{beat}")
        model.add(applied <= has_target)
        model.add(applied <= chord_kind[beat])
        model.add(applied >= has_target + chord_kind[beat] - 1)
        applied_flags.append(applied)

        secondary = model.new_bool_var(f"secondary_leading_tone_{beat}")
        model.add(secondary <= has_target)
        model.add(secondary + chord_kind[beat] <= 1)
        model.add(secondary >= has_target - chord_kind[beat])
        secondary_flags.append(secondary)

        if not spec.tonicization_enabled:
            model.add(applied == 0)

    if spec.minimum_applied_dominants:
        model.add(sum(applied_flags) >= spec.minimum_applied_dominants)
    if spec.minimum_secondary_leading_tone_chords:
        model.add(sum(secondary_flags) >= spec.minimum_secondary_leading_tone_chords)
    model.add(tonicization_target[-1] == NO_TONICIZATION_TARGET)

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
            _v210_chord_rows(
                spec.active_key_at_beat(beat),
                spec.progression_graph,
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

    return SatbVariables(
        soprano=soprano,
        alto=alto,
        tenor=tenor,
        chord_kind=chord_kind,
        chord_inversion=chord_inversion,
        tonicization_target=tonicization_target,
        modal_source=modal_source,
    )


def _add_borrowed_source_leading_constraints(
    model: cp_model.CpModel,
    spec: GenerationSpec,
    chord: list[cp_model.IntVar],
    chord_kind: list[cp_model.IntVar],
    modal_source: list[cp_model.IntVar],
    pitch_classes: list[list[cp_model.IntVar]],
    soprano: list[cp_model.IntVar],
    alto: list[cp_model.IntVar],
    tenor: list[cp_model.IntVar],
    bass: list[cp_model.IntVar],
) -> None:
    voices = (soprano, alto, tenor, bass)
    for beat in range(spec.total_beats - 1):
        rows = _source_leading_rows(spec.active_key_at_beat(beat))
        for voice_index, voice in enumerate(voices):
            carries = model.new_bool_var(f"borrowed_source_leading_{beat}_{voice_index}")
            model.add_allowed_assignments(
                [
                    chord[beat],
                    chord_kind[beat],
                    modal_source[beat],
                    pitch_classes[beat][voice_index],
                    carries,
                ],
                rows,
            )
            model.add(voice[beat + 1] == voice[beat] + 1).only_enforce_if(carries)


def _add_secondary_tendency_constraints(
    model: cp_model.CpModel,
    spec: GenerationSpec,
    chord: list[cp_model.IntVar],
    chord_kind: list[cp_model.IntVar],
    tonicization_target: list[cp_model.IntVar],
    modal_source: list[cp_model.IntVar],
    pitch_classes: list[list[cp_model.IntVar]],
    soprano: list[cp_model.IntVar],
    alto: list[cp_model.IntVar],
    tenor: list[cp_model.IntVar],
    bass: list[cp_model.IntVar],
) -> None:
    voices = (soprano, alto, tenor, bass)
    for beat in range(spec.total_beats - 1):
        key = spec.active_key_at_beat(beat)
        rows = _secondary_root_flag_rows(key, spec.progression_graph)
        is_secondary = model.new_bool_var(f"secondary_resolution_{beat}")
        model.add(tonicization_target[beat] != NO_TONICIZATION_TARGET).only_enforce_if(
            is_secondary
        )
        model.add(chord_kind[beat] == int(ChordKind.TRIAD)).only_enforce_if(is_secondary)
        model.add(tonicization_target[beat] == NO_TONICIZATION_TARGET).only_enforce_if(
            is_secondary.negated(), chord_kind[beat].negated()
        )
        model.add(chord_kind[beat + 1] == int(ChordKind.TRIAD)).only_enforce_if(is_secondary)
        model.add(modal_source[beat + 1] == NO_MODAL_SOURCE).only_enforce_if(is_secondary)

        for voice_index, voice in enumerate(voices):
            root_flag = model.new_bool_var(f"secondary_root_{beat}_{voice_index}")
            fifth_flag = model.new_bool_var(f"secondary_dim5_{beat}_{voice_index}")
            model.add_allowed_assignments(
                [
                    chord[beat],
                    chord_kind[beat],
                    tonicization_target[beat],
                    pitch_classes[beat][voice_index],
                    root_flag,
                    fifth_flag,
                ],
                rows,
            )
            model.add(voice[beat + 1] == voice[beat] + 1).only_enforce_if(root_flag)
            model.add(voice[beat + 1] <= voice[beat] - 1).only_enforce_if(fifth_flag)
            model.add(voice[beat + 1] >= voice[beat] - 2).only_enforce_if(fifth_flag)


def _secondary_candidate_beats(result: GenerationResult) -> set[int]:
    if not isinstance(result, SatbGenerationResult):
        return set()
    spec = result.spec
    if not result.tonicization_targets or not result.chord_kinds:
        return set()
    if not (
        len(result.tonicization_targets) == len(result.chord_kinds) == spec.total_beats
    ):
        return set()
    beats: set[int] = set()
    for beat, (target, raw_kind) in enumerate(
        zip(result.tonicization_targets, result.chord_kinds, strict=True)
    ):
        if target is None:
            continue
        try:
            parsed_kind = ChordKind.parse(raw_kind)
        except ValueError:
            continue
        if parsed_kind is ChordKind.TRIAD:
            beats.add(beat)
    return beats


def _is_applied_false_positive(
    rule_id: str,
    message: str,
    secondary_beats: set[int],
) -> bool:
    if rule_id not in {"CM037", "CM038"}:
        return False
    return any(message.startswith(f"Beat {beat}:") for beat in secondary_beats)


def secondary_leading_tone_satb_verification_issues(
    result: GenerationResult,
) -> tuple[tuple[str, str], ...]:
    base = borrowed_seventh_satb_verification_issues(result)
    candidate_beats = _secondary_candidate_beats(result)
    issues = [
        issue
        for issue in base
        if not _is_applied_false_positive(issue[0], issue[1], candidate_beats)
    ]
    issues.extend(_secondary_leading_tone_verification_issues(result))
    return tuple(issues)


def secondary_leading_tone_modulation_verification_issues(
    result: GenerationResult,
) -> tuple[tuple[str, str], ...]:
    base = borrowed_seventh_modulation_verification_issues(result)
    candidate_beats = _secondary_candidate_beats(result)
    filtered: list[tuple[str, str]] = []
    for rule_id, message in base:
        if rule_id == "CM046" and any(
            message.startswith(f"Beat {beat}:") for beat in candidate_beats
        ):
            continue
        filtered.append((rule_id, message))
    return tuple(filtered)


def _secondary_leading_tone_verification_issues(
    result: GenerationResult,
) -> tuple[tuple[str, str], ...]:
    if not isinstance(result, SatbGenerationResult):
        return ()
    spec = result.spec
    if not spec.secondary_leading_tone_enabled:
        return ()
    issues: list[tuple[str, str]] = []

    if not result.tonicization_targets:
        return (("CM052", "Enabled secondary leading-tone harmony requires target metadata"),)
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
        return (("CM052", "Secondary leading-tone metadata/voices must match total_beats"),)

    try:
        kinds = tuple(ChordKind.parse(item) for item in result.chord_kinds)
    except ValueError:
        return ()

    applied_count = sum(
        target is not None and chord_kind_value is ChordKind.SEVENTH
        for target, chord_kind_value in zip(result.tonicization_targets, kinds, strict=True)
    )
    if applied_count < spec.minimum_applied_dominants:
        issues.append(("CM037", "Serialized harmony misses minimum_applied_dominants"))

    secondary_beats = [
        beat
        for beat, (target, chord_kind_value) in enumerate(
            zip(result.tonicization_targets, kinds, strict=True)
        )
        if target is not None and chord_kind_value is ChordKind.TRIAD
    ]
    if len(secondary_beats) < spec.minimum_secondary_leading_tone_chords:
        issues.append(
            (
                "CM052",
                "Serialized harmony does not meet minimum_secondary_leading_tone_chords",
            )
        )

    voices = (
        ("soprano", result.soprano),
        ("alto", result.alto),
        ("tenor", result.tenor),
        ("bass", result.bass),
    )
    for beat in secondary_beats:
        target = result.tonicization_targets[beat]
        if target is None:
            continue
        key = spec.active_key_at_beat(beat)
        supported = set(supported_secondary_leading_tone_targets(key, spec.progression_graph))
        context_ok = True
        if target not in supported:
            issues.append(
                (
                    "CM052",
                    (
                        f"Beat {beat}: target {target} is not a supported "
                        "secondary leading-tone target"
                    ),
                )
            )
            context_ok = False
        if beat == spec.total_beats - 1:
            issues.append(("CM052", f"Beat {beat}: secondary leading-tone chord cannot be final"))
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
                        "CM052",
                        f"Beat {beat}: secondary leading-tone chord occupies a certified anchor",
                    )
                )
                context_ok = False
        elif spec.require_authentic_cadence and beat in {0, spec.total_beats - 2}:
            issues.append(
                ("CM052", f"Beat {beat}: secondary leading-tone chord occupies a cadence anchor")
            )
            context_ok = False
        if result.modal_sources and result.modal_sources[beat] is not None:
            issues.append(
                ("CM052", f"Beat {beat}: secondary leading-tone and modal borrowing overlap")
            )
            context_ok = False
        if not context_ok:
            continue

        support = secondary_leading_tone_support_degree(key, target, spec.progression_graph)
        if result.chord_degrees[beat] != support:
            issues.append(
                (
                    "CM052",
                    f"Beat {beat}: support degree does not match target {target} in {key}",
                )
            )

        expected = secondary_leading_tone_triad_pitch_classes(key, target)
        pcs = (
            result.soprano[beat] % 12,
            result.alto[beat] % 12,
            result.tenor[beat] % 12,
            result.bass[beat] % 12,
        )
        root, third, diminished_fifth = expected
        if (
            set(pcs) != set(expected)
            or pcs.count(root) != 1
            or pcs.count(diminished_fifth) != 1
            or pcs.count(third) != 2
        ):
            issues.append(
                (
                    "CM053",
                    (
                        f"Beat {beat}: secondary leading-tone triad is incomplete or "
                        "doubles a tendency tone"
                    ),
                )
            )
        inversion = result.chord_inversions[beat]
        if not 0 <= inversion <= 2:
            issues.append(("CM053", f"Beat {beat}: secondary inversion is outside 0..2"))
        elif result.bass[beat] % 12 != expected[inversion]:
            issues.append(
                ("CM053", f"Beat {beat}: secondary leading-tone inversion mismatches bass")
            )

        if beat + 1 >= spec.total_beats:
            issues.append(("CM054", f"Beat {beat}: secondary leading-tone chord has no resolution"))
            continue
        if result.chord_degrees[beat + 1] != target:
            issues.append(
                ("CM054", f"Beat {beat}: secondary leading-tone chord misses declared target")
            )
        if result.tonicization_targets[beat + 1] is not None:
            issues.append(
                (
                    "CM054",
                    f"Beat {beat}: target chord cannot carry tonicization metadata",
                )
            )
        if kinds[beat + 1] is not ChordKind.TRIAD:
            issues.append(("CM054", f"Beat {beat}: target chord must be triadic"))
        if result.modal_sources and result.modal_sources[beat + 1] is not None:
            issues.append(("CM054", f"Beat {beat}: target chord must be unborrowed"))

        for label, voice in voices:
            if voice[beat] % 12 == root and voice[beat + 1] != voice[beat] + 1:
                issues.append(
                    (
                        "CM054",
                        (
                            f"{label} beat {beat}: local leading tone does not resolve "
                            "upward by semitone"
                        ),
                    )
                )
            if voice[beat] % 12 == diminished_fifth:
                delta = voice[beat + 1] - voice[beat]
                if delta not in {-1, -2}:
                    issues.append(
                        (
                            "CM054",
                            (
                                f"{label} beat {beat}: diminished fifth does not resolve "
                                "downward by step"
                            ),
                        )
                    )

    return tuple(issues)
