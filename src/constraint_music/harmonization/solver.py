"""Compact CP-SAT model for exact request obligations, without style filtering."""

from __future__ import annotations

import math
from itertools import combinations, pairwise, product

from ortools.sat.python import cp_model

from ..errors import InternalVerificationError, NoSolutionError
from ..theory import Key, Mode
from .models import HarmonizationRequest, HarmonizationResult, integer
from .verifier import verify_harmonization


def compile_request(
    request: HarmonizationRequest,
) -> tuple[cp_model.CpModel, list[list[cp_model.IntVar]]]:
    model = cp_model.CpModel()
    key = Key(request.key, Mode.MAJOR)
    notes, pcs = [], []
    for index, chord in enumerate(request.chords):
        row = [
            model.new_int_var(lo, hi, f"pitch_{index}_{v}")
            for v, (lo, hi) in enumerate(request.ranges)
        ]
        pitch_classes = [model.new_int_var(0, 11, f"pc_{index}_{v}") for v in range(4)]
        for pitch, pc, given in zip(row, pitch_classes, request.given_voices[index], strict=True):
            model.add_modulo_equality(pc, pitch, 12)
            if given is not None:
                model.add(pitch == given)
        tones = (
            key.seventh_pitch_classes(chord.degree)
            if chord.seventh
            else key.triad_pitch_classes(chord.degree)
        )
        allowed = [
            values
            for values in product(tones, repeat=4)
            if values[3] == tones[chord.inversion] and set(values) == set(tones)
        ]
        model.add_allowed_assignments(pitch_classes, allowed)
        for upper_pitch, lower_pitch in pairwise(row):
            model.add(upper_pitch > lower_pitch)
        model.add(row[0] - row[1] <= request.max_upper_spacing)
        model.add(row[1] - row[2] <= request.max_upper_spacing)
        notes.append(row)
        pcs.append(pitch_classes)

    signs = []
    for index in range(len(notes) - 1):
        transition = []
        for voice in range(4):
            delta = model.new_int_var(-127, 127, f"delta_{index}_{voice}")
            sign = model.new_int_var(-1, 1, f"sign_{index}_{voice}")
            model.add(delta == notes[index + 1][voice] - notes[index][voice])
            model.add_allowed_assignments(
                [delta, sign], [(d, (d > 0) - (d < 0)) for d in range(-127, 128)]
            )
            transition.append(sign)
            chord = request.chords[index]
            if chord.degree == 4 and request.chords[index + 1].degree == 0:
                leading = model.new_bool_var(f"leading_{index}_{voice}")
                model.add(pcs[index][voice] == key.leading_tone_pc).only_enforce_if(leading)
                model.add(pcs[index][voice] != key.leading_tone_pc).only_enforce_if(~leading)
                model.add(delta == 1).only_enforce_if(leading)
            if chord.seventh:
                seventh = model.new_bool_var(f"seventh_{index}_{voice}")
                seventh_pc = key.seventh_pitch_classes(chord.degree)[3]
                model.add(pcs[index][voice] == seventh_pc).only_enforce_if(seventh)
                model.add(pcs[index][voice] != seventh_pc).only_enforce_if(~seventh)
                model.add(delta >= -2).only_enforce_if(seventh)
                model.add(delta <= -1).only_enforce_if(seventh)
        signs.append(transition)
    for a, b in combinations(range(4), 2):
        intervals = []
        for index, row in enumerate(notes):
            distance = model.new_int_var(1, 127, f"distance_{index}_{a}_{b}")
            interval = model.new_int_var(0, 11, f"interval_{index}_{a}_{b}")
            model.add(distance == row[a] - row[b])
            model.add_modulo_equality(interval, distance, 12)
            intervals.append(interval)
        for index in range(len(notes) - 1):
            model.add_forbidden_assignments(
                [intervals[index], intervals[index + 1], signs[index][a], signs[index][b]],
                [(p, p, s, s) for p in (0, 7) for s in (-1, 1)],
            )
    return model, notes


def harmonize(
    request: HarmonizationRequest,
    *,
    seed: int = 7,
    max_time_seconds: float = 20,
) -> HarmonizationResult:
    integer(seed, 0, 2**31 - 1, "seed")
    if type(max_time_seconds) not in (int, float) or (
        not math.isfinite(max_time_seconds) or not 0.05 <= max_time_seconds <= 600
    ):
        raise ValueError("max_time_seconds must be finite and in 0.05..600")
    model, notes = compile_request(request)
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.max_time_in_seconds = max_time_seconds
    solver.parameters.random_seed = seed
    solver.parameters.randomize_search = True
    status = solver.solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise NoSolutionError(
            f"No request-bound harmonization found ({solver.status_name(status)})"
        )
    rows = tuple(tuple(solver.value(pitch) for pitch in row) for row in notes)
    issues = verify_harmonization(request, rows)
    if issues:
        raise InternalVerificationError("Harmonization contract breach: " + "; ".join(issues))
    return HarmonizationResult(request, rows, solver.status_name(status), solver.wall_time)
