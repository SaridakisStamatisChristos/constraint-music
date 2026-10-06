"""Pinned deletion of one named CP-SAT constraint with independent adjudication."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from functools import cache
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path

from ortools.sat.python import cp_model

from constraint_music.errors import InternalVerificationError
from constraint_music.modal_mixture import NO_MODAL_SOURCE, ModalSource
from constraint_music.models import GenerationSpec, RhythmState
from constraint_music.satb import SatbGenerationResult
from constraint_music.search import DEFAULT_OBJECTIVE_WEIGHTS
from constraint_music.secondary_leading_tone_seventh_runtime import (
    reconstruct_secondary_leading_tone_seventh,
)
from constraint_music.solver import (
    ConstraintMusicSolver,
    _CompiledProblem,
    finalize_generated_result,
)
from constraint_music.theory import NO_TONICIZATION_TARGET, ChordKind
from constraint_music.verifier import verify_result

from .oracle.rhythm_phrase import RhythmPolicy, adjudicate_rhythm
from .oracle.secondary_seventh import (
    SeventhQuality,
    adjudicate_voice_resolutions,
)

_ORTOOLS_VERSION = "9.15.6755"
_SEED = 6131
_ROOT = Path(__file__).resolve().parents[1]
_VOICE_NAMES = ("soprano", "alto", "tenor", "bass")


def _spec() -> GenerationSpec:
    return GenerationSpec(
        bars=1,
        beats_per_bar=2,
        subdivisions_per_beat=1,
        require_authentic_cadence=False,
        harmony_vocabulary="triads+sevenths",
        secondary_leading_tone_seventh_enabled=True,
        minimum_secondary_leading_tone_seventh_chords=1,
        avoid_parallel_perfects=False,
        workers=1,
        seed=_SEED,
        max_time_seconds=30,
        tension_curve=(0.8, 0.1),
    )


def _secondary_beat(result: SatbGenerationResult) -> int:
    for beat in range(result.spec.total_beats - 1):
        if reconstruct_secondary_leading_tone_seventh(result, beat) is not None:
            return beat
    raise AssertionError("Pinned control omitted its required secondary seventh")


def _delete_constraint(model: cp_model.CpModel, name: str) -> int:
    constraints = [deepcopy(constraint) for constraint in model.proto.constraints]
    matches = tuple(
        index
        for index, constraint in enumerate(constraints)
        if constraint.name == name
    )
    if len(matches) != 1:
        raise AssertionError(f"Expected one named compiler constraint {name!r}, got {len(matches)}")
    retained = [constraint for constraint in constraints if constraint.name != name]
    model.proto.constraints.clear()
    model.proto.constraints.extend(retained)
    return matches[0]


def _materialize_candidate(
    problem: _CompiledProblem,
    solver: cp_model.CpSolver,
    spec: GenerationSpec,
    status: cp_model.CpSolverStatus,
) -> tuple[SatbGenerationResult, tuple[tuple[str, int], ...]]:
    target_values = tuple(
        solver.value(variable) for variable in problem.satb.tonicization_target
    )
    source_values = tuple(solver.value(variable) for variable in problem.satb.modal_source)
    result = SatbGenerationResult(
        spec=spec,
        melody=tuple(solver.value(variable) for variable in problem.melody_note),
        bass=tuple(solver.value(variable) for variable in problem.bass_note),
        chord_degrees=tuple(solver.value(variable) for variable in problem.chord),
        target_tension=spec.expanded_tension(),
        actual_tension=tuple(
            round(solver.value(variable) / 3)
            for variable in problem.objective.actual_tensions
        ),
        objective_value=solver.objective_value,
        solver_status=solver.status_name(status),
        wall_time_seconds=solver.wall_time,
        rhythm=tuple(
            RhythmState(solver.value(variable)) for variable in problem.rhythm
        ),
        soprano=tuple(solver.value(variable) for variable in problem.satb.soprano),
        alto=tuple(solver.value(variable) for variable in problem.satb.alto),
        tenor=tuple(solver.value(variable) for variable in problem.satb.tenor),
        chord_kinds=tuple(
            ChordKind(solver.value(variable)) for variable in problem.satb.chord_kind
        ),
        chord_inversions=tuple(
            solver.value(variable) for variable in problem.satb.chord_inversion
        ),
        tonicization_targets=tuple(
            None if value == NO_TONICIZATION_TARGET else value for value in target_values
        ),
        modal_sources=tuple(
            None if value == NO_MODAL_SOURCE else ModalSource(value)
            for value in source_values
        ),
    )
    vector = tuple(
        (name, solver.value(problem.objective.components[name]))
        for name, _weight in DEFAULT_OBJECTIVE_WEIGHTS
    )
    return result, vector


def _source_hash(relative_path: str) -> str:
    return sha256((_ROOT / relative_path).read_bytes()).hexdigest()


def _solve_forced_deletion(
    spec: GenerationSpec,
    constraint_name: str,
    force_witness: Callable[[_CompiledProblem], None],
) -> tuple[
    SatbGenerationResult,
    tuple[tuple[str, int], ...],
    int,
    dict[str, object],
]:
    problem = ConstraintMusicSolver()._compile(spec, DEFAULT_OBJECTIVE_WEIGHTS)
    deleted_index = _delete_constraint(problem.model, constraint_name)
    registration = next(
        item
        for item in problem.compiler_registrations
        if item.constraint_start <= deleted_index < item.constraint_end
    )
    force_witness(problem)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = spec.max_time_seconds
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = spec.seed
    status = solver.solve(problem.model)
    if status not in {cp_model.OPTIMAL, cp_model.FEASIBLE}:
        raise AssertionError(
            f"Deleting {constraint_name!r} did not expose a feasible forced witness"
        )
    candidate, compiled_vector = _materialize_candidate(problem, solver, spec, status)
    return candidate, compiled_vector, deleted_index, registration.to_dict()


def _boundary_observation(
    candidate: SatbGenerationResult,
    compiled_vector: tuple[tuple[str, int], ...],
) -> tuple[str, str | None]:
    try:
        finalize_generated_result(candidate, compiled_vector)
    except InternalVerificationError as exc:
        return "REJECT", str(exc)
    return "ACCEPT", None


def _harmony_opening_deletion() -> dict[str, object]:
    spec = GenerationSpec(
        bars=1,
        beats_per_bar=4,
        subdivisions_per_beat=1,
        require_authentic_cadence=True,
        avoid_parallel_perfects=False,
        workers=1,
        seed=7401,
        max_time_seconds=30,
        tension_curve=(0.6, 0.5, 0.2, 0.1),
    )
    name = "CM016.opening-tonic"
    candidate, vector, index, registration = _solve_forced_deletion(
        spec,
        name,
        lambda problem: problem.model.add(problem.chord[0] == 3),
    )
    verifier = verify_result(candidate)
    boundary_outcome, diagnostic = _boundary_observation(candidate, vector)
    return {
        "constraint_name": name,
        "constraint_index": index,
        "registered_phase": registration,
        "forced_witness": {"opening_degree": candidate.chord_degrees[0]},
        "adjudicator": "production_verifier_independent_of_compiler",
        "verifier_valid": verifier.valid,
        "failed_rules": verifier.failed_rules,
        "boundary_outcome": boundary_outcome,
        "boundary_diagnostic": diagnostic,
        "escaped": verifier.valid or boundary_outcome != "REJECT",
    }


def _rhythm_initial_tie_deletion() -> dict[str, object]:
    spec = GenerationSpec(
        bars=1,
        beats_per_bar=4,
        subdivisions_per_beat=2,
        require_authentic_cadence=False,
        avoid_parallel_perfects=False,
        rhythm_enabled=True,
        require_bar_downbeat_onset=False,
        min_onsets_per_bar=1,
        max_onsets_per_bar=8,
        min_rests_per_bar=0,
        max_rests_per_bar=2,
        min_ties_per_bar=0,
        max_ties_per_bar=2,
        workers=1,
        seed=7402,
        max_time_seconds=30,
        tension_curve=(0.6, 0.5, 0.2, 0.1),
    )
    name = "CM018.initial-not-tie"
    candidate, vector, index, registration = _solve_forced_deletion(
        spec,
        name,
        lambda problem: problem.model.add(problem.rhythm[0] == int(RhythmState.TIE)),
    )
    oracle = adjudicate_rhythm(
        candidate.melody,
        candidate.rhythm_names,
        policy=RhythmPolicy(
            bars=spec.bars,
            steps_per_bar=spec.steps_per_bar,
            enabled=True,
            min_onsets_per_bar=spec.min_onsets_per_bar,
            max_onsets_per_bar=spec.max_onsets_per_bar,
            min_rests_per_bar=spec.min_rests_per_bar,
            max_rests_per_bar=spec.max_rests_per_bar,
            min_ties_per_bar=spec.min_ties_per_bar,
            max_ties_per_bar=spec.max_ties_per_bar,
            max_consecutive_rests=spec.max_consecutive_rests,
            max_tie_steps=spec.max_tie_steps,
            require_bar_downbeat_onset=spec.require_bar_downbeat_onset,
            require_final_onset=False,
        ),
    )
    verifier = verify_result(candidate)
    boundary_outcome, diagnostic = _boundary_observation(candidate, vector)
    return {
        "constraint_name": name,
        "constraint_index": index,
        "registered_phase": registration,
        "forced_witness": {"first_rhythm_state": candidate.rhythm_names[0]},
        "adjudicator": "standard_library_rhythm_oracle",
        "oracle_valid": oracle.valid,
        "oracle_reasons": oracle.reasons,
        "verifier_valid": verifier.valid,
        "failed_rules": verifier.failed_rules,
        "boundary_outcome": boundary_outcome,
        "boundary_diagnostic": diagnostic,
        "escaped": oracle.valid or verifier.valid or boundary_outcome != "REJECT",
    }


@cache
def compiler_constraint_deletion_report() -> dict[str, object]:
    """Delete one exact CM057 clause and require the finalizer to catch its witness."""

    observed_version = version("ortools")
    if observed_version != _ORTOOLS_VERSION:
        raise RuntimeError(
            f"Pinned compiler-deletion evidence requires ortools=={_ORTOOLS_VERSION}, "
            f"found {observed_version}"
        )

    spec = _spec()
    control = ConstraintMusicSolver().generate(spec)
    if not isinstance(control, SatbGenerationResult):  # pragma: no cover - invariant
        raise AssertionError("Expected solver-native SATB control")
    beat = _secondary_beat(control)
    reconstruction = reconstruct_secondary_leading_tone_seventh(control, beat)
    if reconstruction is None:  # pragma: no cover - established above
        raise AssertionError("Secondary-seventh reconstruction disappeared")
    production_quality, _tones = reconstruction
    control_source_voices = (
        control.soprano[beat],
        control.alto[beat],
        control.tenor[beat],
        control.bass[beat],
    )
    voice_index = 2
    constraint_name = f"CM057.root.beat-{beat}.voice-{voice_index}"

    compiler = ConstraintMusicSolver()
    problem = compiler._compile(spec, DEFAULT_OBJECTIVE_WEIGHTS)
    registration = next(
        item
        for item in problem.compiler_registrations
        if item.phase == "secondary_seventh_satb"
    )
    deleted_index = _delete_constraint(problem.model, constraint_name)
    if not registration.constraint_start <= deleted_index < registration.constraint_end:
        raise AssertionError("Deleted constraint fell outside its registered compiler phase")

    # Force a valid vii7/ii source with the local leading tone in tenor, then
    # displace its resolution down an octave. The destination remains the target
    # root by pitch class, isolating the exact-pitch (+1 semitone) compiler clause.
    problem.model.add(problem.satb.tonicization_target[beat] == 1)
    problem.model.add(problem.satb.chord_kind[beat] == int(ChordKind.SEVENTH))
    problem.model.add(problem.satb.tenor[beat] == 61)
    problem.model.add(problem.satb.tenor[beat + 1] == 50)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = spec.max_time_seconds
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = _SEED
    status = solver.solve(problem.model)
    if status not in {cp_model.OPTIMAL, cp_model.FEASIBLE}:
        raise AssertionError(
            "Deleting the named CM057 clause did not expose a feasible violating witness"
        )

    candidate, compiled_vector = _materialize_candidate(problem, solver, spec, status)
    candidate_reconstruction = reconstruct_secondary_leading_tone_seventh(candidate, beat)
    if candidate_reconstruction is None:  # pragma: no cover - pinned witness invariant
        raise AssertionError("Deleted-constraint witness is not a secondary seventh")
    production_quality, _candidate_tones = candidate_reconstruction
    source_voices = (
        candidate.soprano[beat],
        candidate.alto[beat],
        candidate.tenor[beat],
        candidate.bass[beat],
    )
    report = verify_result(candidate)
    try:
        finalize_generated_result(candidate, compiled_vector)
    except InternalVerificationError as exc:
        boundary_outcome = "REJECT"
        boundary_diagnostic: str | None = str(exc)
    else:  # pragma: no cover - evidence invariant
        boundary_outcome = "ACCEPT"
        boundary_diagnostic = None

    target = candidate.tonicization_targets[beat]
    if target is None:  # pragma: no cover - pinned source invariant
        raise AssertionError("Deleted-constraint witness lost its local target")
    active_key = spec.active_key_at_beat(beat)
    target_pitch_class = active_key.pitch_classes[target]
    target_triad = active_key.triad_pitch_classes(target)
    target_is_major = (target_triad[1] - target_triad[0]) % 12 == 4
    quality = (
        SeventhQuality.FULLY_DIMINISHED
        if production_quality.value == "fully_diminished"
        else SeventhQuality.HALF_DIMINISHED
    )
    destination_voices = (
        candidate.soprano[beat + 1],
        candidate.alto[beat + 1],
        candidate.tenor[beat + 1],
        candidate.bass[beat + 1],
    )
    oracle = adjudicate_voice_resolutions(
        source_voices,
        destination_voices,
        target_pitch_class=target_pitch_class,
        target_is_major=target_is_major,
        quality=quality,
    )

    escaped_faults = int(boundary_outcome != "REJECT" or report.valid or oracle.valid)
    return {
        "schema_version": 1,
        "claim_boundary": (
            "This experiment deletes one exact named CP-SAT CM057 clause, forces the "
            "corresponding violating witness, and compares the independent oracle and "
            "production finalizer. It is not every-constraint mutation coverage."
        ),
        "toolchain": {
            "ortools": observed_version,
            "workers": 1,
            "seed": _SEED,
        },
        "visited": 2,
        "deleted_constraints": 1,
        "escaped_faults": escaped_faults,
        "control": {
            "observed": "ACCEPT",
            "secondary_beat": beat,
            "source_voices": control_source_voices,
        },
        "deletion": {
            "constraint_name": constraint_name,
            "constraint_index": deleted_index,
            "registered_phase": registration.to_dict(),
            "violating_voice": _VOICE_NAMES[voice_index],
            "source_voices": source_voices,
            "destination_voices": destination_voices,
            "oracle_valid": oracle.valid,
            "oracle_reasons": oracle.reasons,
            "verifier_valid": report.valid,
            "failed_rules": report.failed_rules,
            "boundary_outcome": boundary_outcome,
            "boundary_diagnostic": boundary_diagnostic,
        },
        "implementation_hashes": {
            path: _source_hash(path)
            for path in (
                "research/compiler_deletions.py",
                "research/oracle/secondary_seventh.py",
                "src/constraint_music/compiler_registry.py",
                "src/constraint_music/secondary_leading_tone_seventh_runtime.py",
                "src/constraint_music/solver.py",
            )
        },
    }


@cache
def expanded_compiler_constraint_deletion_report() -> dict[str, object]:
    """Exercise named deletions from three distinct registered compiler phases."""

    secondary_report = compiler_constraint_deletion_report()
    secondary = secondary_report["deletion"]
    if not isinstance(secondary, dict):  # pragma: no cover - construction invariant
        raise AssertionError("Legacy compiler deletion is not an object")
    deletions = [
        {
            **secondary,
            "adjudicator": "standard_library_secondary_seventh_oracle",
            "forced_witness": {
                "violating_voice": secondary["violating_voice"],
                "source_voices": secondary["source_voices"],
                "destination_voices": secondary["destination_voices"],
            },
            "escaped": bool(
                secondary["oracle_valid"]
                or secondary["verifier_valid"]
                or secondary["boundary_outcome"] != "REJECT"
            ),
        },
        _harmony_opening_deletion(),
        _rhythm_initial_tie_deletion(),
    ]
    phases = {
        str(deletion["registered_phase"]["phase"])
        for deletion in deletions
        if isinstance(deletion["registered_phase"], dict)
    }
    return {
        "schema_version": 1,
        "claim_boundary": (
            "Three exact named CP-SAT clauses from distinct registered phases are "
            "deleted one at a time under forced witnesses. This is bounded deletion "
            "evidence, not mutation coverage for every compiled clause."
        ),
        "toolchain": secondary_report["toolchain"],
        "deleted_constraints": len(deletions),
        "distinct_registered_phases": len(phases),
        "escaped_faults": sum(bool(item["escaped"]) for item in deletions),
        "deletions": deletions,
        "implementation_hashes": {
            path: _source_hash(path)
            for path in (
                "research/compiler_deletions.py",
                "research/oracle/rhythm_phrase.py",
                "research/oracle/secondary_seventh.py",
                "src/constraint_music/compiler_structure.py",
                "src/constraint_music/compiler_tonal.py",
                "src/constraint_music/secondary_leading_tone_seventh_runtime.py",
                "src/constraint_music/solver.py",
            )
        },
    }
