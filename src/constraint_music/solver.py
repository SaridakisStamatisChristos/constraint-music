from __future__ import annotations

from dataclasses import replace

from ortools.sat.python import cp_model

from .compiler_structure import add_motif_constraints, add_rhythm_constraints
from .compiler_tonal import (
    add_bass_constraints,
    add_harmony_constraints,
    add_melodic_constraints,
    add_voice_leading_constraints,
)
from .contract import HARD_CONSTRAINT_IDS
from .models import GenerationResult, GenerationSpec, RhythmState
from .objective import add_objective
from .verifier import verify_result

COMPILED_HARD_CONSTRAINT_IDS: tuple[str, ...] = HARD_CONSTRAINT_IDS


class NoSolutionError(RuntimeError):
    pass


class InternalVerificationError(RuntimeError):
    """Raised when the solver emits an assignment rejected by the independent verifier."""


class ConstraintMusicSolver:
    """Compile the declared musical contract into CP-SAT and fail closed after verification."""

    def generate(self, spec: GenerationSpec) -> GenerationResult:
        melody_domain = spec.tonal_key.pitches_in_range(spec.melody_low, spec.melody_high)
        bass_domain = spec.tonal_key.pitches_in_range(spec.bass_low, spec.bass_high)
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

        rhythm = [model.new_int_var(0, 2, f"rhythm_{step}") for step in range(spec.total_steps)]
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

        add_harmony_constraints(
            model, spec, chord, melody_choice, bass_choice, melody_domain, bass_domain
        )
        add_melodic_constraints(model, spec, melody_choice, melody_domain)
        add_bass_constraints(model, spec, bass_choice, bass_domain)
        add_voice_leading_constraints(
            model, spec, melody_note, bass_note, melody_domain, bass_domain
        )
        add_rhythm_constraints(model, spec, rhythm, melody_note)
        add_motif_constraints(model, spec, rhythm, melody_note)
        objective_terms, actual_tension = add_objective(
            model,
            spec,
            chord,
            melody_choice,
            melody_note,
            rhythm,
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
                f"No feasible composition found ({status_name}). Relax pitch, rhythm, motif, cadence, "
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
            rhythm=tuple(RhythmState(solver.value(item)) for item in rhythm),
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
