from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from ortools.sat.python import cp_model

from .borrowed_seventh_runtime import add_borrowed_seventh_satb_constraints
from .compiler_structure import (
    add_motif_constraints,
    add_phrase_constraints,
    add_rhythm_constraints,
)
from .compiler_tonal import (
    add_bass_constraints,
    add_harmony_constraints,
    add_melodic_constraints,
    add_voice_leading_constraints,
)
from .contract import HARD_CONSTRAINT_IDS
from .modal_mixture import NO_MODAL_SOURCE, ModalSource
from .models import GenerationResult, GenerationSpec, RhythmState
from .modulation_runtime import ModulatedSatbGenerationResult, add_modulated_satb_constraints
from .objective import ObjectiveBundle, add_objective, evaluate_objective_vector
from .satb import SatbGenerationResult, SatbVariables, add_satb_constraints
from .search import (
    DEFAULT_OBJECTIVE_WEIGHTS,
    ObjectiveVector,
    normalize_distinct_on,
    normalize_objective_weights,
    pareto_indices,
    scalarization_profiles,
)
from .secondary_leading_tone_complete_compiler import (
    add_complete_secondary_harmony_constraints,
    add_complete_secondary_melodic_constraints,
    secondary_seventh_outer_pitches_in_range,
)
from .secondary_leading_tone_runtime import add_secondary_leading_tone_satb_constraints
from .secondary_leading_tone_seventh_runtime import (
    add_secondary_leading_tone_seventh_satb_constraints,
)
from .theory import NO_TONICIZATION_TARGET, ChordKind
from .verifier import verify_result

COMPILED_HARD_CONSTRAINT_IDS: tuple[str, ...] = HARD_CONSTRAINT_IDS


class NoSolutionError(RuntimeError):
    pass


class InternalVerificationError(RuntimeError):
    """Raised when solver output disagrees with an independent application-level check."""


@dataclass(slots=True)
class _CompiledProblem:
    model: cp_model.CpModel
    melody_note: list[cp_model.IntVar]
    rhythm: list[cp_model.IntVar]
    bass_note: list[cp_model.IntVar]
    chord: list[cp_model.IntVar]
    satb: SatbVariables
    objective: ObjectiveBundle


class ConstraintMusicSolver:
    """Compile the musical contract into CP-SAT and fail closed after verification."""

    def generate(self, spec: GenerationSpec) -> GenerationResult:
        return self.generate_weighted(spec, DEFAULT_OBJECTIVE_WEIGHTS)

    def generate_weighted(
        self,
        spec: GenerationSpec,
        weights: object,
    ) -> GenerationResult:
        normalized = normalize_objective_weights(weights)
        return self._solve(spec, normalized, (), ("melody",))

    def generate_many(
        self,
        spec: GenerationSpec,
        count: int,
        distinct_on: object = ("melody",),
    ) -> tuple[GenerationResult, ...]:
        if not 1 <= count <= 32:
            raise ValueError("count must be in 1..32")
        dimensions = normalize_distinct_on(distinct_on)
        results: list[GenerationResult] = []
        for _ in range(count):
            try:
                result = self._solve(
                    spec,
                    DEFAULT_OBJECTIVE_WEIGHTS,
                    tuple(results),
                    dimensions,
                )
            except NoSolutionError as exc:
                raise NoSolutionError(
                    f"Only {len(results)} distinct compositions exist under "
                    f"distinct_on={dimensions}"
                ) from exc
            results.append(result)
        return tuple(results)

    def generate_pareto(
        self,
        spec: GenerationSpec,
        count: int,
        distinct_on: object = ("melody",),
        candidate_multiplier: int = 3,
    ) -> tuple[GenerationResult, ...]:
        if not 1 <= count <= 16:
            raise ValueError("Pareto count must be in 1..16")
        if not 1 <= candidate_multiplier <= 8:
            raise ValueError("candidate_multiplier must be in 1..8")
        dimensions = normalize_distinct_on(distinct_on)
        pool_size = min(32, max(count, count * candidate_multiplier))
        profiles = scalarization_profiles(DEFAULT_OBJECTIVE_WEIGHTS, pool_size)
        candidates: list[GenerationResult] = []
        for profile in profiles:
            try:
                candidate = self._solve(spec, profile, tuple(candidates), dimensions)
            except NoSolutionError:
                break
            candidates.append(candidate)
        if not candidates:
            raise NoSolutionError("No feasible composition found during Pareto search")
        vectors = tuple(evaluate_objective_vector(candidate) for candidate in candidates)
        front = pareto_indices(vectors)
        return tuple(candidates[index] for index in front[:count])

    def _solve(
        self,
        spec: GenerationSpec,
        weights: ObjectiveVector,
        exclusions: tuple[GenerationResult, ...],
        distinct_on: tuple[str, ...],
    ) -> GenerationResult:
        problem = self._compile(spec, weights)
        for exclusion_index, result in enumerate(exclusions):
            self._add_no_good(problem, result, distinct_on, exclusion_index)

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = spec.max_time_seconds
        solver.parameters.num_search_workers = spec.workers
        solver.parameters.random_seed = spec.seed
        solver.parameters.randomize_search = True
        solver.parameters.log_search_progress = False

        status = solver.solve(problem.model)
        status_name = solver.status_name(status)
        if status not in {cp_model.OPTIMAL, cp_model.FEASIBLE}:
            raise NoSolutionError(
                f"No feasible composition found ({status_name}). Relax pitch, rhythm, motif, "
                "phrase, cadence, SATB voice-leading, expanded harmony, tonicization, modal "
                "mixture, secondary leading-tone, modulation, repetition, or distinctness "
                "constraints."
            )

        common: dict[str, Any] = dict(
            spec=spec,
            melody=tuple(solver.value(note) for note in problem.melody_note),
            bass=tuple(solver.value(note) for note in problem.bass_note),
            chord_degrees=tuple(solver.value(item) for item in problem.chord),
            target_tension=spec.expanded_tension(),
            actual_tension=tuple(
                round(solver.value(value) / 3) for value in problem.objective.actual_tensions
            ),
            objective_value=solver.objective_value,
            solver_status=status_name,
            wall_time_seconds=solver.wall_time,
            rhythm=tuple(RhythmState(solver.value(item)) for item in problem.rhythm),
            soprano=tuple(solver.value(item) for item in problem.satb.soprano),
            alto=tuple(solver.value(item) for item in problem.satb.alto),
            tenor=tuple(solver.value(item) for item in problem.satb.tenor),
            chord_kinds=tuple(
                ChordKind(solver.value(item)) for item in problem.satb.chord_kind
            ),
            chord_inversions=tuple(
                solver.value(item) for item in problem.satb.chord_inversion
            ),
            tonicization_targets=tuple(
                None if value == NO_TONICIZATION_TARGET else value
                for value in (
                    solver.value(item) for item in problem.satb.tonicization_target
                )
            ),
            modal_sources=tuple(
                None if value == NO_MODAL_SOURCE else ModalSource(value)
                for value in (solver.value(item) for item in problem.satb.modal_source)
            ),
        )
        if spec.modulation_enabled:
            raw_result: SatbGenerationResult = ModulatedSatbGenerationResult(
                **common,
                key_contexts=spec.expected_key_contexts,
            )
        else:
            raw_result = SatbGenerationResult(**common)

        report = verify_result(raw_result)
        if not report.valid:
            joined = "; ".join(report.issues[:5])
            raise InternalVerificationError(f"Solver/verifier contract breach: {joined}")

        solver_vector = tuple(
            (name, solver.value(problem.objective.components[name])) for name, _ in weights
        )
        independent_vector = evaluate_objective_vector(raw_result)
        if solver_vector != independent_vector:
            raise InternalVerificationError(
                "Solver/objective-vector breach: compiled and independent objective vectors differ"
            )
        return replace(raw_result, validation=report)

    def _compile(self, spec: GenerationSpec, weights: ObjectiveVector) -> _CompiledProblem:
        if spec.secondary_leading_tone_seventh_enabled:
            melody_domain = secondary_seventh_outer_pitches_in_range(
                spec,
                spec.melody_low,
                spec.melody_high,
            )
            bass_domain = secondary_seventh_outer_pitches_in_range(
                spec,
                spec.bass_low,
                spec.bass_high,
            )
        else:
            melody_domain = (
                spec.context_pitches_in_range(spec.melody_low, spec.melody_high)
                if spec.modulation_enabled
                else spec.tonal_key.pitches_in_range(spec.melody_low, spec.melody_high)
            )
            bass_domain = (
                spec.context_pitches_in_range(spec.bass_low, spec.bass_high)
                if spec.modulation_enabled
                else spec.tonal_key.pitches_in_range(spec.bass_low, spec.bass_high)
            )
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

        if spec.secondary_leading_tone_seventh_enabled:
            add_complete_secondary_harmony_constraints(
                model,
                spec,
                chord,
                melody_choice,
                bass_choice,
                melody_domain,
                bass_domain,
            )
            add_complete_secondary_melodic_constraints(
                model,
                spec,
                melody_choice,
                melody_domain,
            )
        else:
            add_harmony_constraints(
                model,
                spec,
                chord,
                melody_choice,
                bass_choice,
                melody_domain,
                bass_domain,
            )
            add_melodic_constraints(model, spec, melody_choice, melody_domain)
        add_bass_constraints(model, spec, bass_choice, bass_domain)
        add_voice_leading_constraints(
            model, spec, melody_note, bass_note, melody_domain, bass_domain
        )
        if spec.secondary_leading_tone_seventh_enabled:
            satb = add_secondary_leading_tone_seventh_satb_constraints(
                model,
                spec,
                chord,
                melody_note,
                bass_note,
            )
        elif spec.secondary_leading_tone_enabled:
            satb = add_secondary_leading_tone_satb_constraints(
                model, spec, chord, melody_note, bass_note
            )
        elif spec.modal_mixture_enabled and spec.expanded_harmony_enabled:
            satb = add_borrowed_seventh_satb_constraints(
                model, spec, chord, melody_note, bass_note
            )
        elif spec.modulation_enabled:
            satb = add_modulated_satb_constraints(model, spec, chord, melody_note, bass_note)
        else:
            satb = add_satb_constraints(model, spec, chord, melody_note, bass_note)
        add_rhythm_constraints(model, spec, rhythm, melody_note)
        add_motif_constraints(model, spec, rhythm, melody_note)
        add_phrase_constraints(model, spec, rhythm, melody_note, bass_note, chord)
        objective = add_objective(
            model,
            spec,
            chord,
            melody_choice,
            melody_note,
            rhythm,
            bass_note,
            melody_domain,
            weights,
        )
        model.minimize(objective.scalarized)
        return _CompiledProblem(model, melody_note, rhythm, bass_note, chord, satb, objective)

    def _add_no_good(
        self,
        problem: _CompiledProblem,
        result: GenerationResult,
        distinct_on: tuple[str, ...],
        exclusion_index: int,
    ) -> None:
        variables: list[tuple[cp_model.IntVar, int]] = []
        if "melody" in distinct_on:
            variables.extend(zip(problem.melody_note, result.melody, strict=True))
        if "rhythm" in distinct_on:
            variables.extend(
                (variable, int(value))
                for variable, value in zip(problem.rhythm, result.effective_rhythm, strict=True)
            )
        if "bass" in distinct_on:
            variables.extend(zip(problem.bass_note, result.bass, strict=True))
        if "harmony" in distinct_on:
            variables.extend(zip(problem.chord, result.chord_degrees, strict=True))
        if "voicing" in distinct_on:
            if not isinstance(result, SatbGenerationResult):
                raise ValueError("voicing distinctness requires a SATB result")
            variables.extend(zip(problem.satb.alto, result.alto, strict=True))
            variables.extend(zip(problem.satb.tenor, result.tenor, strict=True))
        if "harmonic_form" in distinct_on:
            if not isinstance(result, SatbGenerationResult):
                raise ValueError("harmonic_form distinctness requires a SATB result")
            if not (
                len(result.chord_kinds)
                == len(result.chord_inversions)
                == len(problem.chord)
            ):
                raise ValueError("harmonic_form distinctness requires explicit form metadata")
            variables.extend(
                (variable, int(ChordKind.parse(value)))
                for variable, value in zip(
                    problem.satb.chord_kind,
                    result.chord_kinds,
                    strict=True,
                )
            )
            variables.extend(
                zip(problem.satb.chord_inversion, result.chord_inversions, strict=True)
            )
        if "tonicization" in distinct_on:
            if not isinstance(result, SatbGenerationResult):
                raise ValueError("tonicization distinctness requires a SATB result")
            if len(result.tonicization_targets) != len(problem.chord):
                raise ValueError("tonicization distinctness requires explicit target metadata")
            variables.extend(
                (
                    variable,
                    NO_TONICIZATION_TARGET if target is None else int(target),
                )
                for variable, target in zip(
                    problem.satb.tonicization_target,
                    result.tonicization_targets,
                    strict=True,
                )
            )
        if "modal_source" in distinct_on:
            if not isinstance(result, SatbGenerationResult):
                raise ValueError("modal_source distinctness requires a SATB result")
            if len(result.modal_sources) != len(problem.chord):
                raise ValueError("modal_source distinctness requires explicit source metadata")
            variables.extend(
                (
                    variable,
                    NO_MODAL_SOURCE if source is None else int(ModalSource.parse(source)),
                )
                for variable, source in zip(
                    problem.satb.modal_source,
                    result.modal_sources,
                    strict=True,
                )
            )
        if "key_context" in distinct_on:
            if not isinstance(result, ModulatedSatbGenerationResult):
                raise ValueError("key_context distinctness requires a modulated SATB result")
            if len(result.key_contexts) != len(problem.chord):
                raise ValueError("key_context distinctness requires explicit context metadata")

        differs: list[cp_model.IntVar] = []
        for index, (variable, value) in enumerate(variables):
            flag = problem.model.new_bool_var(f"nogood_{exclusion_index}_{index}")
            problem.model.add(variable != value).only_enforce_if(flag)
            problem.model.add(variable == value).only_enforce_if(flag.negated())
            differs.append(flag)
        problem.model.add(sum(differs) >= 1)
