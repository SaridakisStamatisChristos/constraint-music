from __future__ import annotations

import random
from dataclasses import dataclass
from itertools import pairwise

from ortools.sat.python import cp_model

from .models import GenerationResult, GenerationSpec
from .search import (
    DEFAULT_OBJECTIVE_WEIGHTS,
    OBJECTIVE_COMPONENTS,
    ObjectiveVector,
    normalize_objective_weights,
    objective_mapping,
)
from .theory import CHORD_TENSION, DEGREE_TENSION


@dataclass(frozen=True, slots=True)
class ObjectiveBundle:
    components: dict[str, cp_model.IntVar]
    actual_tensions: list[cp_model.IntVar]
    scalarized: cp_model.LinearExpr


def add_objective(
    model: cp_model.CpModel,
    spec: GenerationSpec,
    chord: list[cp_model.IntVar],
    melody_choice: list[cp_model.IntVar],
    melody_note: list[cp_model.IntVar],
    rhythm: list[cp_model.IntVar],
    bass_note: list[cp_model.IntVar],
    melody_domain: tuple[int, ...],
    weights: ObjectiveVector = DEFAULT_OBJECTIVE_WEIGHTS,
) -> ObjectiveBundle:
    key = spec.tonal_key
    target = spec.expanded_tension()
    chord_tension_table = CHORD_TENSION[spec.mode]
    melody_tension_table = [DEGREE_TENSION[key.degree_of_pc(note % 12)] for note in melody_domain]
    component_terms: dict[str, list[cp_model.LinearExpr]] = {
        name: [] for name in OBJECTIVE_COMPONENTS
    }
    actual_tensions: list[cp_model.IntVar] = []
    jitter_terms: list[cp_model.LinearExpr] = []

    for beat in range(spec.total_beats):
        chord_tension = model.new_int_var(0, 100, f"chord_tension_{beat}")
        melody_tension = model.new_int_var(0, 100, f"melody_tension_{beat}")
        actual = model.new_int_var(0, 300, f"actual_tension_{beat}")
        deviation = model.new_int_var(0, 300, f"tension_deviation_{beat}")
        model.add_element(chord[beat], chord_tension_table, chord_tension)
        model.add_element(
            melody_choice[beat * spec.subdivisions_per_beat], melody_tension_table, melody_tension
        )
        model.add(actual == 2 * chord_tension + melody_tension)
        model.add_abs_equality(deviation, actual - target[beat] * 3)
        component_terms["tension_deviation"].append(deviation)
        actual_tensions.append(actual)

    for step, (left, right) in enumerate(pairwise(melody_note)):
        delta = model.new_int_var(-24, 24, f"melody_delta_{step}")
        absolute = model.new_int_var(0, 24, f"melody_abs_delta_{step}")
        excess = model.new_int_var(0, 24, f"melody_excess_{step}")
        same = model.new_bool_var(f"melody_same_{step}")
        model.add(delta == right - left)
        model.add_abs_equality(absolute, delta)
        model.add_max_equality(excess, [absolute - 5, 0])
        model.add(left == right).only_enforce_if(same)
        model.add(left != right).only_enforce_if(same.negated())
        component_terms["melody_motion"].append(2 * excess + same)

    for beat, (left, right) in enumerate(pairwise(bass_note)):
        delta = model.new_int_var(-24, 24, f"bass_delta_{beat}")
        absolute = model.new_int_var(0, 24, f"bass_abs_delta_{beat}")
        excess = model.new_int_var(0, 24, f"bass_excess_{beat}")
        model.add(delta == right - left)
        model.add_abs_equality(absolute, delta)
        model.add_max_equality(excess, [absolute - 4, 0])
        component_terms["bass_motion"].append(excess)

    for beat, (left, right) in enumerate(pairwise(chord)):
        same = model.new_bool_var(f"chord_same_{beat}")
        model.add(left == right).only_enforce_if(same)
        model.add(left != right).only_enforce_if(same.negated())
        component_terms["harmonic_repetition"].append(same)

    for beat in range(spec.total_beats - 1):
        change = target[beat + 1] - target[beat]
        if abs(change) < 8:
            continue
        left = melody_note[beat * spec.subdivisions_per_beat]
        right = melody_note[(beat + 1) * spec.subdivisions_per_beat]
        follows = model.new_bool_var(f"contour_follows_{beat}")
        if change > 0:
            model.add(right >= left + 1).only_enforce_if(follows)
            model.add(right <= left).only_enforce_if(follows.negated())
        else:
            model.add(right <= left - 1).only_enforce_if(follows)
            model.add(right >= left).only_enforce_if(follows.negated())
        component_terms["contour_mismatch"].append(follows.negated())

    rng = random.Random(spec.seed)
    for index, choice in enumerate(melody_choice):
        jitter_table = [rng.randrange(0, 4) for _ in melody_domain]
        jitter = model.new_int_var(0, 3, f"melody_jitter_{index}")
        model.add_element(choice, jitter_table, jitter)
        jitter_terms.append(jitter)
    for index, item in enumerate(chord):
        jitter_table = [rng.randrange(0, 3) for _ in range(7)]
        jitter = model.new_int_var(0, 2, f"chord_jitter_{index}")
        model.add_element(item, jitter_table, jitter)
        jitter_terms.append(jitter)
    if spec.rhythm_enabled:
        for index, item in enumerate(rhythm):
            jitter_table = [rng.randrange(0, 4) for _ in range(3)]
            jitter = model.new_int_var(0, 3, f"rhythm_jitter_{index}")
            model.add_element(item, jitter_table, jitter)
            jitter_terms.append(jitter)

    components: dict[str, cp_model.IntVar] = {}
    for name in OBJECTIVE_COMPONENTS:
        component = model.new_int_var(0, 1_000_000, f"objective_{name}")
        model.add(component == sum(component_terms[name]))
        components[name] = component

    weight_map = objective_mapping(normalize_objective_weights(weights))
    scalarized = sum(weight_map[name] * components[name] for name in OBJECTIVE_COMPONENTS)
    scalarized += sum(jitter_terms)
    return ObjectiveBundle(components, actual_tensions, scalarized)


def evaluate_objective_vector(result: GenerationResult) -> ObjectiveVector:
    spec = result.spec
    key = spec.tonal_key
    target = spec.expanded_tension()

    tension_deviation = 0
    for beat, chord in enumerate(result.chord_degrees):
        strong_step = beat * spec.subdivisions_per_beat
        melody = result.melody[strong_step]
        chord_tension = CHORD_TENSION[spec.mode][chord]
        melody_tension = DEGREE_TENSION[key.degree_of_pc(melody % 12)]
        actual = 2 * chord_tension + melody_tension
        tension_deviation += abs(actual - target[beat] * 3)

    melody_motion = sum(
        2 * max(abs(right - left) - 5, 0) + int(left == right)
        for left, right in pairwise(result.melody)
    )
    bass_motion = sum(
        max(abs(right - left) - 4, 0) for left, right in pairwise(result.bass)
    )
    harmonic_repetition = sum(
        int(left == right) for left, right in pairwise(result.chord_degrees)
    )

    contour_mismatch = 0
    for beat in range(spec.total_beats - 1):
        change = target[beat + 1] - target[beat]
        if abs(change) < 8:
            continue
        left = result.melody[beat * spec.subdivisions_per_beat]
        right = result.melody[(beat + 1) * spec.subdivisions_per_beat]
        follows = right > left if change > 0 else right < left
        contour_mismatch += int(not follows)

    values = {
        "tension_deviation": tension_deviation,
        "melody_motion": melody_motion,
        "bass_motion": bass_motion,
        "harmonic_repetition": harmonic_repetition,
        "contour_mismatch": contour_mismatch,
    }
    return tuple((name, values[name]) for name in OBJECTIVE_COMPONENTS)
