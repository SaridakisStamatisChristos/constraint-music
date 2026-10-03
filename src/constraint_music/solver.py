from __future__ import annotations

import random
from dataclasses import replace
from itertools import pairwise

from ortools.sat.python import cp_model

from .contract import HARD_CONSTRAINT_IDS
from .models import GenerationResult, GenerationSpec
from .theory import (
    CHORD_TENSION,
    DEGREE_TENSION,
    is_parallel_perfect,
)
from .verifier import verify_result


COMPILED_HARD_CONSTRAINT_IDS: tuple[str, ...] = HARD_CONSTRAINT_IDS


class NoSolutionError(RuntimeError):
    pass


class InternalVerificationError(RuntimeError):
    """Raised when the solver emits an assignment rejected by the independent verifier."""


class ConstraintMusicSolver:
    """Compile tonal rules into an OR-Tools CP-SAT model and optimize musical shape."""

    def generate(self, spec: GenerationSpec) -> GenerationResult:
        key = spec.tonal_key
        melody_domain = key.pitches_in_range(spec.melody_low, spec.melody_high)
        bass_domain = key.pitches_in_range(spec.bass_low, spec.bass_high)
        model = cp_model.CpModel()

        melody_choice = [
            model.new_int_var(0, len(melody_domain) - 1, f"melody_choice_{step}")
            for step in range(spec.total_steps)
        ]
        melody_note = [
            model.new_int_var(spec.melody_low, spec.melody_high, f"melody_note_{step}")
            for step in range(spec.total_steps)
        ]
        for choice, note in zip(melody_choice, melody_note, strict=True):
            model.add_element(choice, melody_domain, note)

        bass_choice = [
            model.new_int_var(0, len(bass_domain) - 1, f"bass_choice_{beat}")
            for beat in range(spec.total_beats)
        ]
        bass_note = [
            model.new_int_var(spec.bass_low, spec.bass_high, f"bass_note_{beat}")
            for beat in range(spec.total_beats)
        ]
        for choice, note in zip(bass_choice, bass_note, strict=True):
            model.add_element(choice, bass_domain, note)

        chord = [model.new_int_var(0, 6, f"chord_{beat}") for beat in range(spec.total_beats)]

        self._add_harmony_constraints(
            model, spec, chord, melody_choice, bass_choice, melody_domain, bass_domain
        )
        self._add_melodic_constraints(model, spec, melody_choice, melody_note, melody_domain)
        self._add_bass_constraints(model, spec, bass_choice, bass_note, bass_domain)
        self._add_voice_leading_constraints(
            model, spec, melody_note, bass_note, melody_domain, bass_domain
        )
        objective_terms, actual_tension = self._add_objective(
            model,
            spec,
            chord,
            melody_choice,
            melody_note,
            bass_note,
            melody_domain,
        )
        model.minimize(sum(objective_terms))

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = spec.max_time_seconds
        solver.parameters.num_search_workers = spec.workers
        solver.parameters.random_seed = spec.seed
        solver.parameters.randomize_search = True
        solver.parameters.log_search_progress = False

        status = solver.solve(model)
        status_name = solver.status_name(status)
        if status not in {cp_model.OPTIMAL, cp_model.FEASIBLE}:
            raise NoSolutionError(
                f"No feasible composition found ({status_name}). Relax the range, leap, cadence, "
                "or repetition constraints."
            )

        raw_result = GenerationResult(
            spec=spec,
            melody=tuple(solver.value(note) for note in melody_note),
            bass=tuple(solver.value(note) for note in bass_note),
            chord_degrees=tuple(solver.value(item) for item in chord),
            target_tension=spec.expanded_tension(),
            actual_tension=tuple(round(solver.value(value) / 3) for value in actual_tension),
            objective_value=solver.objective_value,
            solver_status=status_name,
            wall_time_seconds=solver.wall_time,
        )
        report = verify_result(raw_result)
        if not report.valid:
            joined = "; ".join(report.issues[:5])
            raise InternalVerificationError(f"Solver/verifier contract breach: {joined}")
        return replace(raw_result, validation=report)

    def generate_many(self, spec: GenerationSpec, count: int) -> tuple[GenerationResult, ...]:
        if not 1 <= count <= 32:
            raise ValueError("count must be in 1..32")
        return tuple(
            self.generate(replace(spec, seed=spec.seed + offset * 104729))
            for offset in range(count)
        )

    def _add_harmony_constraints(
        self,
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
            dominant_function = [(4,), (6,)]
            model.add(chord[0] == 0)
            model.add_allowed_assignments([chord[-2]], dominant_function)
            model.add(chord[-1] == 0)
            model.add_allowed_assignments([melody_choice[-1]], [(i,) for i in tonic_melody_indices])
            model.add_allowed_assignments([bass_choice[-1]], [(i,) for i in tonic_bass_indices])

    def _add_melodic_constraints(
        self,
        model: cp_model.CpModel,
        spec: GenerationSpec,
        melody_choice: list[cp_model.IntVar],
        melody_note: list[cp_model.IntVar],
        melody_domain: tuple[int, ...],
    ) -> None:
        key = spec.tonal_key
        allowed_pairs: list[tuple[int, int]] = []
        for left_index, left_note in enumerate(melody_domain):
            for right_index, right_note in enumerate(melody_domain):
                leap = right_note - left_note
                if abs(leap) > spec.max_melody_leap:
                    continue
                if abs(leap) % 12 == 6:
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
                model.add_forbidden_assignments(
                    melody_choice[start : start + window], repeated_rows
                )

        # A large melodic leap must be followed by contrary stepwise recovery.
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

    def _add_bass_constraints(
        self,
        model: cp_model.CpModel,
        spec: GenerationSpec,
        bass_choice: list[cp_model.IntVar],
        bass_note: list[cp_model.IntVar],
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

    def _add_voice_leading_constraints(
        self,
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
        # The bass is held for a full beat. Check every adjacent melodic transition
        # against the bass sounding on each side. Within-beat transitions have no bass
        # motion and therefore cannot be parallel motion; weak-to-strong boundaries can.
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

    def _add_objective(
        self,
        model: cp_model.CpModel,
        spec: GenerationSpec,
        chord: list[cp_model.IntVar],
        melody_choice: list[cp_model.IntVar],
        melody_note: list[cp_model.IntVar],
        bass_note: list[cp_model.IntVar],
        melody_domain: tuple[int, ...],
    ) -> tuple[list[cp_model.LinearExpr], list[cp_model.IntVar]]:
        key = spec.tonal_key
        target = spec.expanded_tension()
        chord_tension_table = CHORD_TENSION[spec.mode]
        melody_tension_table = [
            DEGREE_TENSION[key.degree_of_pc(note % 12)] for note in melody_domain
        ]
        objective: list[cp_model.LinearExpr] = []
        actual_tensions: list[cp_model.IntVar] = []

        for beat in range(spec.total_beats):
            chord_tension = model.new_int_var(0, 100, f"chord_tension_{beat}")
            melody_tension = model.new_int_var(0, 100, f"melody_tension_{beat}")
            actual = model.new_int_var(0, 300, f"actual_tension_{beat}")
            deviation = model.new_int_var(0, 300, f"tension_deviation_{beat}")
            model.add_element(chord[beat], chord_tension_table, chord_tension)
            model.add_element(
                melody_choice[beat * spec.subdivisions_per_beat],
                melody_tension_table,
                melody_tension,
            )
            model.add(actual == 2 * chord_tension + melody_tension)
            model.add_abs_equality(deviation, actual - target[beat] * 3)
            objective.append(8 * deviation)
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
            objective.extend((4 * excess, 2 * same))

        for beat, (left, right) in enumerate(pairwise(bass_note)):
            delta = model.new_int_var(-24, 24, f"bass_delta_{beat}")
            absolute = model.new_int_var(0, 24, f"bass_abs_delta_{beat}")
            excess = model.new_int_var(0, 24, f"bass_excess_{beat}")
            model.add(delta == right - left)
            model.add_abs_equality(absolute, delta)
            model.add_max_equality(excess, [absolute - 4, 0])
            objective.append(3 * excess)

        for beat, (left, right) in enumerate(pairwise(chord)):
            same = model.new_bool_var(f"chord_same_{beat}")
            model.add(left == right).only_enforce_if(same)
            model.add(left != right).only_enforce_if(same.negated())
            objective.append(same)

        # Make the melodic contour broadly follow tension changes.
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
            objective.append(4 * follows.negated())

        # Seeded micro-costs create diverse but reproducible tie-breaking.
        rng = random.Random(spec.seed)
        for index, choice in enumerate(melody_choice):
            jitter_table = [rng.randrange(0, 4) for _ in melody_domain]
            jitter = model.new_int_var(0, 3, f"melody_jitter_{index}")
            model.add_element(choice, jitter_table, jitter)
            objective.append(jitter)
        for index, item in enumerate(chord):
            jitter_table = [rng.randrange(0, 3) for _ in range(7)]
            jitter = model.new_int_var(0, 2, f"chord_jitter_{index}")
            model.add_element(item, jitter_table, jitter)
            objective.append(jitter)

        return objective, actual_tensions
