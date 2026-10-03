from __future__ import annotations

from itertools import pairwise

from ortools.sat.python import cp_model

from .models import GenerationSpec
from .theory import is_parallel_perfect


def add_harmony_constraints(
    model: cp_model.CpModel,
    spec: GenerationSpec,
    chord: list[cp_model.IntVar],
    melody_choice: list[cp_model.IntVar],
    bass_choice: list[cp_model.IntVar],
    melody_domain: tuple[int, ...],
    bass_domain: tuple[int, ...],
) -> None:
    key = spec.tonal_key
    for left, right in pairwise(chord):
        model.add_allowed_assignments([left, right], spec.progression_pairs)

    chord_melody_pairs = [
        (degree, note_index)
        for degree in range(7)
        for note_index, note in enumerate(melody_domain)
        if note % 12 in key.triad_pitch_classes(degree)
    ]
    chord_bass_pairs = [
        (degree, note_index)
        for degree in range(7)
        for note_index, note in enumerate(bass_domain)
        if note % 12 in key.triad_pitch_classes(degree)
    ]
    for beat in range(spec.total_beats):
        strong_step = beat * spec.subdivisions_per_beat
        model.add_allowed_assignments(
            [chord[beat], melody_choice[strong_step]], chord_melody_pairs
        )
        model.add_allowed_assignments([chord[beat], bass_choice[beat]], chord_bass_pairs)

    if spec.require_authentic_cadence:
        tonic_melody_indices = [
            i for i, note in enumerate(melody_domain) if note % 12 == key.tonic_pc
        ]
        tonic_bass_indices = [
            i for i, note in enumerate(bass_domain) if note % 12 == key.tonic_pc
        ]
        model.add(chord[0] == 0)
        model.add_allowed_assignments([chord[-2]], [(4,), (6,)])
        model.add(chord[-1] == 0)
        model.add_allowed_assignments([melody_choice[-1]], [(i,) for i in tonic_melody_indices])
        model.add_allowed_assignments([bass_choice[-1]], [(i,) for i in tonic_bass_indices])


def add_melodic_constraints(
    model: cp_model.CpModel,
    spec: GenerationSpec,
    melody_choice: list[cp_model.IntVar],
    melody_domain: tuple[int, ...],
) -> None:
    key = spec.tonal_key
    allowed_pairs: list[tuple[int, int]] = []
    for left_index, left_note in enumerate(melody_domain):
        for right_index, right_note in enumerate(melody_domain):
            leap = right_note - left_note
            if abs(leap) > spec.max_melody_leap or abs(leap) % 12 == 6:
                continue
            if (
                spec.resolve_leading_tone
                and left_note % 12 == key.leading_tone_pc
                and right_note != left_note + 1
            ):
                continue
            allowed_pairs.append((left_index, right_index))
    for left_var, right_var in pairwise(melody_choice):
        model.add_allowed_assignments([left_var, right_var], allowed_pairs)

    window = spec.max_repeated_notes + 1
    if window <= len(melody_choice):
        repeated_rows = [(index,) * window for index in range(len(melody_domain))]
        for start in range(len(melody_choice) - window + 1):
            model.add_forbidden_assignments(melody_choice[start : start + window], repeated_rows)

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
        model.add_allowed_assignments(melody_choice[start : start + 3], recovery_rows)


def add_bass_constraints(
    model: cp_model.CpModel,
    spec: GenerationSpec,
    bass_choice: list[cp_model.IntVar],
    bass_domain: tuple[int, ...],
) -> None:
    allowed_pairs = [
        (left_index, right_index)
        for left_index, left in enumerate(bass_domain)
        for right_index, right in enumerate(bass_domain)
        if abs(right - left) <= spec.max_bass_leap and abs(right - left) % 12 != 6
    ]
    for left, right in pairwise(bass_choice):
        model.add_allowed_assignments([left, right], allowed_pairs)


def add_voice_leading_constraints(
    model: cp_model.CpModel,
    spec: GenerationSpec,
    melody_note: list[cp_model.IntVar],
    bass_note: list[cp_model.IntVar],
    melody_domain: tuple[int, ...],
    bass_domain: tuple[int, ...],
) -> None:
    if not spec.avoid_parallel_perfects:
        return
    forbidden = [
        (melody_a, bass_a, melody_b, bass_b)
        for melody_a in melody_domain
        for bass_a in bass_domain
        for melody_b in melody_domain
        for bass_b in bass_domain
        if is_parallel_perfect(melody_a, bass_a, melody_b, bass_b)
    ]
    for step in range(spec.total_steps - 1):
        first_beat = step // spec.subdivisions_per_beat
        second_beat = (step + 1) // spec.subdivisions_per_beat
        if first_beat == second_beat:
            continue
        model.add_forbidden_assignments(
            [
                melody_note[step],
                bass_note[first_beat],
                melody_note[step + 1],
                bass_note[second_beat],
            ],
            forbidden,
        )
