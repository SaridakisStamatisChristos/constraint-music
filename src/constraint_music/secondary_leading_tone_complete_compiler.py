from __future__ import annotations

from itertools import pairwise

from ortools.sat.python import cp_model

from .models import GenerationSpec
from .secondary_leading_tone import (
    secondary_leading_tone_seventh_pitch_class_variants,
    secondary_leading_tone_seventh_support_degree,
    supported_secondary_leading_tone_seventh_targets,
)


def secondary_seventh_outer_pitch_classes(
    spec: GenerationSpec,
    beat: int,
) -> frozenset[int]:
    """Pitch classes admitted at a strong outer-voice position in v2.12.

    Ordinary beats are still narrowed by the SATB row table. This union exists only
    so a solver variable can represent chromatic secondary-leading-tone members before
    the target/function row is selected.
    """
    key = spec.active_key_at_beat(beat)
    pitch_classes = set(key.pitch_classes)
    if not spec.secondary_leading_tone_seventh_enabled:
        return frozenset(pitch_classes)
    for target in supported_secondary_leading_tone_seventh_targets(
        key,
        spec.progression_graph,
    ):
        for _quality, tones in secondary_leading_tone_seventh_pitch_class_variants(
            key,
            target,
        ):
            pitch_classes.update(tones)
    return frozenset(pitch_classes)


def secondary_seventh_outer_pitches_in_range(
    spec: GenerationSpec,
    low: int,
    high: int,
) -> tuple[int, ...]:
    pitch_classes: set[int] = set()
    for beat in range(spec.total_beats):
        pitch_classes.update(secondary_seventh_outer_pitch_classes(spec, beat))
    return tuple(note for note in range(low, high + 1) if note % 12 in pitch_classes)


def _support_tones_for_degree(
    spec: GenerationSpec,
    beat: int,
    degree: int,
) -> frozenset[int]:
    key = spec.active_key_at_beat(beat)
    pitch_classes = set(key.triad_pitch_classes(degree))
    if not spec.secondary_leading_tone_seventh_enabled:
        return frozenset(pitch_classes)
    for target in supported_secondary_leading_tone_seventh_targets(
        key,
        spec.progression_graph,
    ):
        for quality, tones in secondary_leading_tone_seventh_pitch_class_variants(
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
            if support == degree:
                pitch_classes.update(tones)
    return frozenset(pitch_classes)


def add_complete_secondary_harmony_constraints(
    model: cp_model.CpModel,
    spec: GenerationSpec,
    chord: list[cp_model.IntVar],
    melody_choice: list[cp_model.IntVar],
    bass_choice: list[cp_model.IntVar],
    melody_domain: tuple[int, ...],
    bass_domain: tuple[int, ...],
) -> None:
    """Compile CM005/CM006 without the v2.11 diatonic-outer-voice shortcut.

    The support degree still participates in CM007 and legacy structural semantics.
    At a beat whose support degree can host a certified secondary seventh, the outer
    variable domain admits every pitch class of that exact target-derived family.
    The SATB functional row table subsequently narrows the beat to one exact sonority,
    so ordinary harmony is not weakened.
    """
    for left, right in pairwise(chord):
        model.add_allowed_assignments([left, right], spec.progression_pairs)

    for beat in range(spec.total_beats):
        chord_melody_pairs = [
            (degree, note_index)
            for degree in range(7)
            for note_index, note in enumerate(melody_domain)
            if note % 12 in _support_tones_for_degree(spec, beat, degree)
        ]
        chord_bass_pairs = [
            (degree, note_index)
            for degree in range(7)
            for note_index, note in enumerate(bass_domain)
            if note % 12 in _support_tones_for_degree(spec, beat, degree)
        ]
        strong_step = beat * spec.subdivisions_per_beat
        model.add_allowed_assignments(
            [chord[beat], melody_choice[strong_step]],
            chord_melody_pairs,
        )
        model.add_allowed_assignments(
            [chord[beat], bass_choice[beat]],
            chord_bass_pairs,
        )

    if spec.require_authentic_cadence:
        key = spec.tonal_key
        tonic_melody_indices = [
            index
            for index, note in enumerate(melody_domain)
            if note % 12 == key.tonic_pc
        ]
        tonic_bass_indices = [
            index
            for index, note in enumerate(bass_domain)
            if note % 12 == key.tonic_pc
        ]
        model.add(chord[0] == 0)
        model.add_allowed_assignments([chord[-2]], [(4,), (6,)])
        model.add(chord[-1] == 0)
        model.add_allowed_assignments(
            [melody_choice[-1]],
            [(index,) for index in tonic_melody_indices],
        )
        model.add_allowed_assignments(
            [bass_choice[-1]],
            [(index,) for index in tonic_bass_indices],
        )

    if spec.modulation_enabled:
        destination = spec.modulation_destination
        boundary = spec.modulation_boundary_beat
        if destination is None or boundary is None:
            raise ValueError("Validated modulation spec lost destination/boundary")
        pivot = boundary - 1
        tonic_melody_indices = [
            index
            for index, note in enumerate(melody_domain)
            if note % 12 == destination.tonic_pc
        ]
        tonic_bass_indices = [
            index
            for index, note in enumerate(bass_domain)
            if note % 12 == destination.tonic_pc
        ]
        model.add(chord[0] == 0)
        model.add(chord[pivot] == 0)
        model.add(chord[-2] == 4)
        model.add(chord[-1] == 0)
        final_strong = (spec.total_beats - 1) * spec.subdivisions_per_beat
        model.add_allowed_assignments(
            [melody_choice[final_strong]],
            [(index,) for index in tonic_melody_indices],
        )
        model.add_allowed_assignments(
            [melody_choice[-1]],
            [(index,) for index in tonic_melody_indices],
        )
        model.add_allowed_assignments(
            [bass_choice[-1]],
            [(index,) for index in tonic_bass_indices],
        )


def add_complete_secondary_melodic_constraints(
    model: cp_model.CpModel,
    spec: GenerationSpec,
    melody_choice: list[cp_model.IntVar],
    melody_domain: tuple[int, ...],
) -> None:
    """Compile legacy melodic grammar with chromaticity only on strong secondary beats."""
    for step, choice in enumerate(melody_choice):
        beat = step // spec.subdivisions_per_beat
        strong = step % spec.subdivisions_per_beat == 0
        allowed_pitch_classes = (
            secondary_seventh_outer_pitch_classes(spec, beat)
            if strong
            else frozenset(spec.active_key_at_beat(beat).pitch_classes)
        )
        allowed_indices = [
            (index,)
            for index, note in enumerate(melody_domain)
            if note % 12 in allowed_pitch_classes
        ]
        model.add_allowed_assignments([choice], allowed_indices)

    pair_rows_by_leading_pc: dict[int, list[tuple[int, int]]] = {}

    def pair_rows(leading_tone_pc: int) -> list[tuple[int, int]]:
        cached = pair_rows_by_leading_pc.get(leading_tone_pc)
        if cached is not None:
            return cached
        rows: list[tuple[int, int]] = []
        for left_index, left_note in enumerate(melody_domain):
            for right_index, right_note in enumerate(melody_domain):
                leap = right_note - left_note
                if abs(leap) > spec.max_melody_leap or abs(leap) % 12 == 6:
                    continue
                if (
                    spec.resolve_leading_tone
                    and left_note % 12 == leading_tone_pc
                    and right_note != left_note + 1
                ):
                    continue
                rows.append((left_index, right_index))
        pair_rows_by_leading_pc[leading_tone_pc] = rows
        return rows

    for step, (left_var, right_var) in enumerate(pairwise(melody_choice)):
        beat = step // spec.subdivisions_per_beat
        key = spec.active_key_at_beat(beat)
        model.add_allowed_assignments(
            [left_var, right_var],
            pair_rows(key.leading_tone_pc),
        )

    window = spec.max_repeated_notes + 1
    if window <= len(melody_choice):
        repeated_rows = [(index,) * window for index in range(len(melody_domain))]
        for start in range(len(melody_choice) - window + 1):
            model.add_forbidden_assignments(
                melody_choice[start : start + window],
                repeated_rows,
            )

    recovery_rows: list[tuple[int, int, int]] = []
    for a_index, a in enumerate(melody_domain):
        for b_index, b in enumerate(melody_domain):
            first = b - a
            if abs(first) > spec.max_melody_leap or abs(first) % 12 == 6:
                continue
            for c_index, c in enumerate(melody_domain):
                second = c - b
                if abs(first) <= 7 or (abs(second) <= 2 and first * second < 0):
                    recovery_rows.append((a_index, b_index, c_index))
    for start in range(len(melody_choice) - 2):
        model.add_allowed_assignments(
            melody_choice[start : start + 3],
            recovery_rows,
        )
