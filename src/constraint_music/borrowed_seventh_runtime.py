from __future__ import annotations

from functools import cache
from itertools import pairwise, product

from ortools.sat.python import cp_model

from .modal_mixture import (
    NO_MODAL_SOURCE,
    ModalSource,
    borrowed_seventh_pitch_classes,
    borrowed_triad_pitch_classes,
    canonical_modal_source,
    modal_source_leading_tone_pc,
    supported_borrowed_degrees,
    supported_borrowed_seventh_degrees,
)
from .models import GenerationResult, GenerationSpec
from .modulation_runtime import (
    _add_modulated_harmony_motion_constraints,
    modulated_satb_verification_issues,
    modulation_verification_issues,
)
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
    satb_verification_issues,
)
from .theory import NO_TONICIZATION_TARGET, ChordKind, Key


def _feature_enabled(spec: GenerationSpec) -> bool:
    return spec.modal_mixture_enabled and spec.expanded_harmony_enabled


@cache
def _v29_chord_rows(
    key: Key,
    tonicization_enabled: bool,
) -> tuple[tuple[int, int, int, int, int, int, int, int, int], ...]:
    """Extend the verified v2.8 SATB row table with the narrow v2.9 borrowed-seventh set."""
    rows = list(
        _satb_chord_rows(
            key,
            True,
            tonicization_enabled,
            True,
        )
    )
    source = canonical_modal_source(key)
    for degree in supported_borrowed_seventh_degrees(key):
        active_triad = key.triad_pitch_classes(degree)
        borrowed = borrowed_seventh_pitch_classes(key, degree, source)
        for pcs in product(borrowed, repeat=4):
            if len(set(pcs)) != 4:
                continue
            # CM005/CM006 remain unchanged: both outer voices must still belong to the
            # active-key triadic core. The whitelist guarantees two distinct shared tones.
            if pcs[0] not in active_triad or pcs[3] not in active_triad:
                continue
            inversion = borrowed.index(pcs[3])
            if inversion > 2:
                continue
            rows.append(
                (
                    degree,
                    int(ChordKind.SEVENTH),
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
def _source_leading_rows(key: Key) -> tuple[tuple[int, int, int, int, int], ...]:
    """Flag source-derived leading tones that need an explicit upward semitone resolution."""
    source = canonical_modal_source(key)
    leading_pc = modal_source_leading_tone_pc(key, source)
    supported = set(supported_borrowed_seventh_degrees(key))
    rows: list[tuple[int, int, int, int, int]] = []
    max_source = int(ModalSource.PARALLEL_NATURAL_MINOR)
    for degree in range(7):
        borrowed = (
            borrowed_seventh_pitch_classes(key, degree, source)
            if degree in supported
            else ()
        )
        seventh_pc = borrowed[3] if borrowed else None
        for kind in ChordKind:
            for source_value in range(NO_MODAL_SOURCE, max_source + 1):
                for pc in range(12):
                    flag = int(
                        leading_pc is not None
                        and source_value == int(source)
                        and kind is ChordKind.SEVENTH
                        and degree in supported
                        and pc == leading_pc
                        and pc in borrowed
                        and pc != seventh_pc
                    )
                    rows.append((degree, int(kind), source_value, pc, flag))
    return tuple(rows)


def add_borrowed_seventh_satb_constraints(
    model: cp_model.CpModel,
    spec: GenerationSpec,
    chord: list[cp_model.IntVar],
    melody_note: list[cp_model.IntVar],
    bass_note: list[cp_model.IntVar],
) -> SatbVariables:
    """Compile the v2.9 modal-mixture + expanded-harmony SATB boundary."""
    if not _feature_enabled(spec):
        raise ValueError(
            "v2.9 borrowed-seventh runtime requires modal_mixture_enabled=true and "
            "harmony_vocabulary='triads+sevenths'"
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
            for target_degree in key.applied_dominant_targets:
                inner_pitch_classes.update(
                    key.applied_dominant_seventh_pitch_classes(target_degree)
                )
        source = canonical_modal_source(key)
        for degree in supported_borrowed_degrees(key):
            inner_pitch_classes.update(borrowed_triad_pitch_classes(key, degree, source))
        for degree in supported_borrowed_seventh_degrees(key):
            inner_pitch_classes.update(
                borrowed_seventh_pitch_classes(key, degree, source)
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

    if spec.minimum_seventh_chords:
        model.add(sum(chord_kind) >= spec.minimum_seventh_chords)
    model.add(chord_kind[-1] == int(ChordKind.TRIAD))

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
    for beat, source_var in enumerate(modal_source):
        canonical = int(canonical_modal_source(spec.active_key_at_beat(beat)))
        model.add_allowed_assignments([source_var], [(NO_MODAL_SOURCE,), (canonical,)])
        borrowed = model.new_bool_var(f"borrowed_chord_{beat}")
        model.add(source_var == canonical).only_enforce_if(borrowed)
        model.add(source_var == NO_MODAL_SOURCE).only_enforce_if(borrowed.negated())
        borrowed_flags.append(borrowed)
    if spec.minimum_borrowed_chords:
        model.add(sum(borrowed_flags) >= spec.minimum_borrowed_chords)

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
        if spec.require_authentic_cadence and spec.total_beats >= 2:
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
            _v29_chord_rows(
                spec.active_key_at_beat(beat),
                spec.tonicization_enabled,
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

    _add_source_leading_tone_constraints(
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

    return SatbVariables(
        soprano=soprano,
        alto=alto,
        tenor=tenor,
        chord_kind=chord_kind,
        chord_inversion=chord_inversion,
        tonicization_target=tonicization_target,
        modal_source=modal_source,
    )


def _add_source_leading_tone_constraints(
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
        key = spec.active_key_at_beat(beat)
        rows = _source_leading_rows(key)
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


def _candidate_borrowed_seventh_beats(result: GenerationResult) -> set[int]:
    if not isinstance(result, SatbGenerationResult):
        return set()
    spec = result.spec
    if not _feature_enabled(spec):
        return set()
    if not (
        len(result.chord_degrees)
        == len(result.chord_kinds)
        == len(result.tonicization_targets)
        == len(result.modal_sources)
        == spec.total_beats
    ):
        return set()
    beats: set[int] = set()
    for beat, (degree, raw_kind, target, raw_source) in enumerate(
        zip(
            result.chord_degrees,
            result.chord_kinds,
            result.tonicization_targets,
            result.modal_sources,
            strict=True,
        )
    ):
        if raw_source is None or target is not None:
            continue
        try:
            kind = ChordKind.parse(raw_kind)
            source = ModalSource.parse(raw_source)
        except ValueError:
            continue
        key = spec.active_key_at_beat(beat)
        if (
            kind is ChordKind.SEVENTH
            and source is canonical_modal_source(key)
            and degree in supported_borrowed_seventh_degrees(key)
        ):
            beats.add(beat)
    return beats


def _is_legacy_triad_false_positive(
    rule_id: str,
    message: str,
    candidate_beats: set[int],
) -> bool:
    for beat in candidate_beats:
        prefix = f"Beat {beat}:"
        if not message.startswith(prefix):
            continue
        if rule_id == "CM041" and (
            "borrowed harmony must be triadic" in message
            or "v2.7 borrowed harmony must be triadic" in message
        ):
            return True
        if rule_id == "CM042" and (
            "borrowed chord is not the complete source-mode triad" in message
            or "incomplete active-key borrowed triad" in message
        ):
            return True
    return False


def borrowed_seventh_satb_verification_issues(
    result: GenerationResult,
) -> tuple[tuple[str, str], ...]:
    """Preserve legacy SATB checks and independently certify borrowed sevenths."""
    base = (
        modulated_satb_verification_issues(result)
        if result.spec.modulation_enabled
        else satb_verification_issues(result)
    )
    candidate_beats = _candidate_borrowed_seventh_beats(result)
    issues = [
        issue
        for issue in base
        if not _is_legacy_triad_false_positive(issue[0], issue[1], candidate_beats)
    ]
    issues.extend(_borrowed_seventh_verification_issues(result))
    return tuple(issues)


def borrowed_seventh_modulation_verification_issues(
    result: GenerationResult,
) -> tuple[tuple[str, str], ...]:
    """Preserve CM043-CM048 while replacing only the old triad-only CM046 interpretation."""
    base = modulation_verification_issues(result)
    candidate_beats = _candidate_borrowed_seventh_beats(result)
    filtered: list[tuple[str, str]] = []
    for rule_id, message in base:
        if rule_id == "CM046" and any(
            message == f"Beat {beat}: harmony is not destination-key derived"
            for beat in candidate_beats
        ):
            continue
        filtered.append((rule_id, message))
    return tuple(filtered)


def _borrowed_seventh_verification_issues(
    result: GenerationResult,
) -> tuple[tuple[str, str], ...]:
    if not isinstance(result, SatbGenerationResult):
        return ()
    spec = result.spec
    if not _feature_enabled(spec):
        return ()
    if not (
        len(result.chord_degrees)
        == len(result.chord_kinds)
        == len(result.chord_inversions)
        == len(result.tonicization_targets)
        == len(result.modal_sources)
        == spec.total_beats
        and all(
            len(voice) == spec.total_beats
            for voice in (result.soprano, result.alto, result.tenor, result.bass)
        )
    ):
        return ()

    issues: list[tuple[str, str]] = []
    voices = (
        ("soprano", result.soprano),
        ("alto", result.alto),
        ("tenor", result.tenor),
        ("bass", result.bass),
    )
    for beat, raw_source in enumerate(result.modal_sources):
        if raw_source is None:
            continue
        try:
            kind = ChordKind.parse(result.chord_kinds[beat])
            source = ModalSource.parse(raw_source)
        except ValueError:
            continue
        if kind is not ChordKind.SEVENTH:
            continue

        degree = result.chord_degrees[beat]
        key = spec.active_key_at_beat(beat)
        canonical = canonical_modal_source(key)
        context_ok = True
        if source is not canonical:
            issues.append(
                (
                    "CM049",
                    (
                        f"Beat {beat}: borrowed seventh source {source.label} "
                        f"is not canonical for {key}"
                    ),
                )
            )
            context_ok = False
        if degree not in supported_borrowed_seventh_degrees(key):
            issues.append(
                (
                    "CM049",
                    f"Beat {beat}: degree {degree} is not an eligible borrowed seventh in {key}",
                )
            )
            context_ok = False
        if result.tonicization_targets[beat] is not None:
            issues.append(
                ("CM049", f"Beat {beat}: borrowed seventh cannot overlap tonicization")
            )
            context_ok = False

        if spec.modulation_enabled:
            boundary = spec.modulation_boundary_beat
            if boundary is not None:
                reserved = {0, boundary - 1, spec.total_beats - 2, spec.total_beats - 1}
                if beat in reserved:
                    issues.append(
                        (
                            "CM049",
                            f"Beat {beat}: borrowed seventh occupies a certified modulation anchor",
                        )
                    )
                    context_ok = False
        else:
            if beat == spec.total_beats - 1:
                issues.append(("CM049", f"Beat {beat}: final chord cannot be a borrowed seventh"))
                context_ok = False
            if spec.require_authentic_cadence and beat == spec.total_beats - 2:
                issues.append(
                    ("CM049", f"Beat {beat}: cadential dominant cannot be a borrowed seventh")
                )
                context_ok = False

        if not context_ok:
            continue

        expected = borrowed_seventh_pitch_classes(key, degree, source)
        pcs = (
            result.soprano[beat] % 12,
            result.alto[beat] % 12,
            result.tenor[beat] % 12,
            result.bass[beat] % 12,
        )
        if set(pcs) != set(expected) or len(set(pcs)) != 4:
            issues.append(
                (
                    "CM050",
                    (
                        f"Beat {beat}: borrowed seventh is not the complete "
                        "source-derived four-tone chord"
                    ),
                )
            )
        inversion = result.chord_inversions[beat]
        if not 0 <= inversion <= 2:
            issues.append(("CM050", f"Beat {beat}: borrowed-seventh inversion is outside 0..2"))
        elif result.bass[beat] % 12 != expected[inversion]:
            issues.append(
                ("CM050", f"Beat {beat}: borrowed-seventh inversion does not match the bass")
            )

        if beat + 1 >= spec.total_beats:
            issues.append(("CM051", f"Beat {beat}: borrowed seventh has no following resolution"))
            continue

        seventh_pc = expected[3]
        for label, voice in voices:
            if voice[beat] % 12 == seventh_pc:
                delta = voice[beat + 1] - voice[beat]
                if delta not in {-1, -2}:
                    issues.append(
                        (
                            "CM051",
                            (
                                f"{label} beat {beat}: borrowed chordal seventh "
                                "does not resolve down by step"
                            ),
                        )
                    )

        source_leading = modal_source_leading_tone_pc(key, source)
        if (
            source_leading is not None
            and source_leading != seventh_pc
            and source_leading in expected
        ):
            for label, voice in voices:
                if (
                    voice[beat] % 12 == source_leading
                    and voice[beat + 1] != voice[beat] + 1
                ):
                    issues.append(
                        (
                            "CM051",
                            (
                                f"{label} beat {beat}: borrowed source leading tone "
                                "does not resolve upward"
                            ),
                        )
                    )

    return tuple(issues)
