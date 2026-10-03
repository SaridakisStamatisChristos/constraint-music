from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise, product
from typing import Any

from ortools.sat.python import cp_model

from .models import GenerationResult, ValidationReport
from .theory import is_parallel_perfect, midi_note_name

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

    @property
    def soprano_names(self) -> tuple[str, ...]:
        return tuple(midi_note_name(note) for note in self.soprano)

    @property
    def alto_names(self) -> tuple[str, ...]:
        return tuple(midi_note_name(note) for note in self.alto)

    @property
    def tenor_names(self) -> tuple[str, ...]:
        return tuple(midi_note_name(note) for note in self.tenor)

    def to_dict(self) -> dict[str, Any]:
        payload = GenerationResult.to_dict(self)
        music = payload["music"]
        music["soprano_midi"] = list(self.soprano)
        music["soprano_names"] = list(self.soprano_names)
        music["alto_midi"] = list(self.alto)
        music["alto_names"] = list(self.alto_names)
        music["tenor_midi"] = list(self.tenor)
        music["tenor_names"] = list(self.tenor_names)
        return payload


@dataclass(slots=True)
class SatbVariables:
    soprano: list[cp_model.IntVar]
    alto: list[cp_model.IntVar]
    tenor: list[cp_model.IntVar]


def result_from_dict(payload: Mapping[str, Any]) -> GenerationResult:
    base = GenerationResult.from_dict(payload)
    raw_music = payload.get("music")
    if not isinstance(raw_music, Mapping) or "alto_midi" not in raw_music:
        return base

    def notes(key: str) -> tuple[int, ...]:
        value = raw_music.get(key, ())
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
            raise ValueError(f"Result JSON music.{key} must be an array")
        return tuple(int(item) for item in value)

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
    )


def add_satb_constraints(
    model: cp_model.CpModel,
    result_spec: Any,
    chord: list[cp_model.IntVar],
    melody_note: list[cp_model.IntVar],
    bass_note: list[cp_model.IntVar],
) -> SatbVariables:
    spec = result_spec
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
    alto = [model.new_int_var(ALTO_LOW, ALTO_HIGH, f"alto_{beat}") for beat in range(spec.total_beats)]
    tenor = [
        model.new_int_var(TENOR_LOW, TENOR_HIGH, f"tenor_{beat}")
        for beat in range(spec.total_beats)
    ]

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

        pcs = [model.new_int_var(0, 11, f"satb_pc_{beat}_{voice}") for voice in range(4)]
        for pc, voice in zip(pcs, (soprano[beat], alto[beat], tenor[beat], bass_note[beat]), strict=True):
            model.add_modulo_equality(pc, voice, 12)
        model.add_allowed_assignments([chord[beat], *pcs], _satb_chord_rows(key))

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
        for voice, domain in ((alto, alto_domain), (tenor, tenor_domain)):
            allowed = [
                (left, right)
                for left in domain
                for right in domain
                if left % 12 != key.leading_tone_pc or right == left + 1
            ]
            for left, right in pairwise(voice):
                model.add_allowed_assignments([left, right], allowed)

    return SatbVariables(soprano=soprano, alto=alto, tenor=tenor)


def satb_verification_issues(result: GenerationResult) -> tuple[tuple[str, str], ...]:
    if not isinstance(result, SatbGenerationResult):
        return ()
    spec = result.spec
    key = spec.tonal_key
    s, a, t, b = result.soprano, result.alto, result.tenor, result.bass
    issues: list[tuple[str, str]] = []

    if not all(len(voice) == spec.total_beats for voice in (s, a, t)):
        issues.append(("CM027", "SATB voices must contain exactly one note per beat"))
        return tuple(issues)
    for beat, note in enumerate(s):
        strong_step = beat * spec.subdivisions_per_beat
        if strong_step >= len(result.melody) or note != result.melody[strong_step]:
            issues.append(("CM027", f"Beat {beat}: soprano is not anchored to the strong-step melody"))

    for beat, (sv, av, tv, bv) in enumerate(zip(s, a, t, b, strict=True)):
        if not spec.melody_low <= sv <= spec.melody_high:
            issues.append(("CM028", f"Beat {beat}: soprano is outside its configured range"))
        if not ALTO_LOW <= av <= ALTO_HIGH:
            issues.append(("CM028", f"Beat {beat}: alto is outside {ALTO_LOW}..{ALTO_HIGH}"))
        if not TENOR_LOW <= tv <= TENOR_HIGH:
            issues.append(("CM028", f"Beat {beat}: tenor is outside {TENOR_LOW}..{TENOR_HIGH}"))
        if not bv < tv < av < sv:
            issues.append(("CM028", f"Beat {beat}: SATB voice order/crossing invariant is violated"))
        if sv - av > MAX_UPPER_SPACING or av - tv > MAX_UPPER_SPACING:
            issues.append(("CM029", f"Beat {beat}: adjacent upper voices exceed octave spacing"))

        if beat < len(result.chord_degrees) and 0 <= result.chord_degrees[beat] <= 6:
            triad = key.triad_pitch_classes(result.chord_degrees[beat])
            pcs = (sv % 12, av % 12, tv % 12, bv % 12)
            root = triad[0]
            if any(pc not in triad for pc in pcs) or set(pcs) != set(triad) or pcs.count(root) < 2:
                issues.append(("CM030", f"Beat {beat}: SATB chord is incomplete or does not double the root"))

    if spec.avoid_parallel_perfects:
        named = (("S-A", s, a), ("S-T", s, t), ("A-T", a, t), ("A-B", a, b), ("T-B", t, b))
        for label, left_voice, right_voice in named:
            for beat in range(min(len(left_voice), len(right_voice)) - 1):
                if is_parallel_perfect(
                    left_voice[beat], right_voice[beat], left_voice[beat + 1], right_voice[beat + 1]
                ):
                    issues.append(("CM031", f"Beats {beat}->{beat + 1}: parallel perfect in {label}"))

    if spec.resolve_leading_tone:
        for label, voice in (("alto", a), ("tenor", t)):
            for beat, (left, right) in enumerate(pairwise(voice)):
                if left % 12 == key.leading_tone_pc and right != left + 1:
                    issues.append(("CM032", f"{label} beat {beat}: leading tone does not resolve upward"))

    return tuple(issues)


def _satb_chord_rows(key: Any) -> list[tuple[int, int, int, int, int]]:
    rows: list[tuple[int, int, int, int, int]] = []
    for degree in range(7):
        triad = key.triad_pitch_classes(degree)
        root = triad[0]
        for pcs in product(triad, repeat=4):
            if set(pcs) == set(triad) and pcs.count(root) >= 2:
                rows.append((degree, *pcs))
    return rows


def _parallel_rows(
    left_domain: tuple[int, ...], right_domain: tuple[int, ...]
) -> list[tuple[int, int, int, int]]:
    return [
        (left_a, right_a, left_b, right_b)
        for left_a in left_domain
        for right_a in right_domain
        for left_b in left_domain
        for right_b in right_domain
        if is_parallel_perfect(left_a, right_a, left_b, right_b)
    ]
