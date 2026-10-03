from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import cache
from itertools import pairwise, product
from typing import Any

from ortools.sat.python import cp_model

from .models import GenerationResult, GenerationSpec
from .theory import ChordKind, Key, is_parallel_perfect, midi_note_name

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
        if not (
            len(self.chord_kinds)
            == len(self.chord_inversions)
            == len(self.chord_degrees)
        ):
            return ()
        key = self.spec.tonal_key
        names: list[str] = []
        try:
            for degree, raw_kind, inversion in zip(
                self.chord_degrees,
                self.chord_kinds,
                self.chord_inversions,
                strict=True,
            ):
                names.append(key.chord_form_name(degree, ChordKind.parse(raw_kind), inversion))
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
        if self.chord_kinds:
            music["chord_kinds"] = [ChordKind.parse(kind).label for kind in self.chord_kinds]
        if self.chord_inversions:
            music["chord_inversions"] = list(self.chord_inversions)
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

    def notes(key: str) -> tuple[int, ...]:
        return tuple(int(item) for item in values(key))

    raw_kinds = values("chord_kinds") if "chord_kinds" in raw_music else ()
    raw_inversions = values("chord_inversions") if "chord_inversions" in raw_music else ()
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
        soprano=notes("soprano_midi"),
        alto=notes("alto_midi"),
        tenor=notes("tenor_midi"),
        chord_kinds=tuple(ChordKind.parse(item) for item in raw_kinds),
        chord_inversions=tuple(int(item) for item in raw_inversions),
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
    alto_domain = key.pitches_in_range(ALTO_LOW, ALTO_HIGH)
    tenor_domain = key.pitches_in_range(TENOR_LOW, TENOR_HIGH)
    bass_domain = key.pitches_in_range(spec.bass_low, spec.bass_high)

    if not alto_domain or not tenor_domain:
        raise ValueError("SATB inner-voice ranges contain no pitches in the selected key")

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

    if spec.expanded_harmony_enabled:
        if spec.minimum_seventh_chords:
            model.add(sum(chord_kind) >= spec.minimum_seventh_chords)
        # A chordal seventh must always have a following sonority in which to resolve.
        model.add(chord_kind[-1] == int(ChordKind.TRIAD))
    else:
        for kind in chord_kind:
            model.add(kind == int(ChordKind.TRIAD))

    chord_rows = _satb_chord_rows(key, spec.expanded_harmony_enabled)
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
            [chord[beat], chord_kind[beat], chord_inversion[beat], *pcs],
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
            chord,
            chord_kind,
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
    )


def _add_expanded_harmony_motion_constraints(
    model: cp_model.CpModel,
    key: Key,
    chord: list[cp_model.IntVar],
    chord_kind: list[cp_model.IntVar],
    pitch_classes: list[list[cp_model.IntVar]],
    soprano: list[cp_model.IntVar],
    alto: list[cp_model.IntVar],
    tenor: list[cp_model.IntVar],
    bass: list[cp_model.IntVar],
) -> None:
    seventh_rows = _chordal_seventh_flag_rows(key)
    dominant_rows = _dominant_seventh_flag_rows()
    leading_rows = _dominant_leading_flag_rows(key)
    voices = (soprano, alto, tenor, bass)

    for beat in range(len(chord) - 1):
        dominant = model.new_bool_var(f"dominant_seventh_{beat}")
        model.add_allowed_assignments(
            [chord[beat], chord_kind[beat], dominant],
            dominant_rows,
        )
        model.add(chord[beat + 1] == 0).only_enforce_if(dominant)

        for voice_index, voice in enumerate(voices):
            current_pc = pitch_classes[beat][voice_index]
            carries_seventh = model.new_bool_var(f"chordal_seventh_{beat}_{voice_index}")
            model.add_allowed_assignments(
                [chord[beat], chord_kind[beat], current_pc, carries_seventh],
                seventh_rows,
            )
            model.add(voice[beat + 1] <= voice[beat] - 1).only_enforce_if(carries_seventh)
            model.add(voice[beat + 1] >= voice[beat] - 2).only_enforce_if(carries_seventh)

            carries_dominant_leading = model.new_bool_var(
                f"dominant_leading_{beat}_{voice_index}"
            )
            model.add_allowed_assignments(
                [chord[beat], chord_kind[beat], current_pc, carries_dominant_leading],
                leading_rows,
            )
            model.add(voice[beat + 1] == voice[beat] + 1).only_enforce_if(
                carries_dominant_leading
            )


def satb_verification_issues(result: GenerationResult) -> tuple[tuple[str, str], ...]:
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
                if any(not 0 <= inversion <= 2 for inversion in inversions):
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

    for beat, (sv, av, tv, bv) in enumerate(
        zip(soprano, alto, tenor, bass, strict=True)
    ):
        if not spec.melody_low <= sv <= spec.melody_high:
            issues.append(("CM028", f"Beat {beat}: soprano is outside its configured range"))
        if not ALTO_LOW <= av <= ALTO_HIGH:
            issues.append(("CM028", f"Beat {beat}: alto is outside {ALTO_LOW}..{ALTO_HIGH}"))
        if not TENOR_LOW <= tv <= TENOR_HIGH:
            issues.append(("CM028", f"Beat {beat}: tenor is outside {TENOR_LOW}..{TENOR_HIGH}"))
        if not bv < tv < av < sv:
            issues.append(
                ("CM028", f"Beat {beat}: SATB voice order/crossing invariant is violated")
            )
        if sv - av > MAX_UPPER_SPACING or av - tv > MAX_UPPER_SPACING:
            issues.append(("CM029", f"Beat {beat}: adjacent upper voices exceed octave spacing"))

        if beat < len(result.chord_degrees) and 0 <= result.chord_degrees[beat] <= 6:
            degree = result.chord_degrees[beat]
            pcs = (sv % 12, av % 12, tv % 12, bv % 12)
            kind = kinds[beat] if metadata_valid else ChordKind.TRIAD
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

    if metadata_valid:
        _verify_expanded_harmony_motion(result, kinds, issues)

    return tuple(issues)


def _verify_expanded_harmony_motion(
    result: SatbGenerationResult,
    kinds: tuple[ChordKind, ...],
    issues: list[tuple[str, str]],
) -> None:
    key = result.spec.tonal_key
    voices = (
        ("soprano", result.soprano),
        ("alto", result.alto),
        ("tenor", result.tenor),
        ("bass", result.bass),
    )
    beats = min(len(result.chord_degrees), len(kinds))
    for beat in range(beats):
        if kinds[beat] is not ChordKind.SEVENTH:
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
) -> tuple[tuple[int, int, int, int, int, int, int], ...]:
    rows: list[tuple[int, int, int, int, int, int, int]] = []
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
            # CM005/CM006 retain their v2.4 meanings: outer voices use the triadic core.
            # The new seventh therefore enters through alto or tenor in v2.5.
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
                    pcs[0],
                    pcs[1],
                    pcs[2],
                    pcs[3],
                )
            )
    return tuple(rows)


@cache
def _chordal_seventh_flag_rows(key: Key) -> tuple[tuple[int, int, int, int], ...]:
    rows: list[tuple[int, int, int, int]] = []
    for degree in range(7):
        seventh_pc = key.seventh_pitch_classes(degree)[3]
        for kind in ChordKind:
            for pc in range(12):
                flag = int(kind is ChordKind.SEVENTH and pc == seventh_pc)
                rows.append((degree, int(kind), pc, flag))
    return tuple(rows)


@cache
def _dominant_seventh_flag_rows() -> tuple[tuple[int, int, int], ...]:
    return tuple(
        (degree, int(kind), int(degree == 4 and kind is ChordKind.SEVENTH))
        for degree in range(7)
        for kind in ChordKind
    )


@cache
def _dominant_leading_flag_rows(key: Key) -> tuple[tuple[int, int, int, int], ...]:
    return tuple(
        (
            degree,
            int(kind),
            pc,
            int(
                degree == 4
                and kind is ChordKind.SEVENTH
                and pc == key.leading_tone_pc
            ),
        )
        for degree in range(7)
        for kind in ChordKind
        for pc in range(12)
    )


@cache
def _parallel_rows(
    left_domain: tuple[int, ...], right_domain: tuple[int, ...]
) -> tuple[tuple[int, int, int, int], ...]:
    return tuple(
        (left_a, right_a, left_b, right_b)
        for left_a in left_domain
        for right_a in right_domain
        for left_b in left_domain
        for right_b in right_domain
        if is_parallel_perfect(left_a, right_a, left_b, right_b)
    )
