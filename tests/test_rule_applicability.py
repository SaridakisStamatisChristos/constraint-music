from __future__ import annotations

from dataclasses import replace
from itertools import pairwise

from constraint_music.compiler_registry import (
    COMPILED_HARD_CONSTRAINT_IDS,
    COMPILER_PHASES,
)
from constraint_music.contract import HARD_CONSTRAINT_IDS, RuleStatus, build_rule_outcomes
from constraint_music.models import GenerationResult, GenerationSpec
from constraint_music.search import DEFAULT_OBJECTIVE_WEIGHTS
from constraint_music.solver import ConstraintMusicSolver
from constraint_music.verifier import verify_result


def test_rule_ledger_is_complete_unique_and_reconciled(
    solved_piece: GenerationResult,
) -> None:
    report = verify_result(solved_piece)
    assert len(report.rule_outcomes) == 57
    assert tuple(outcome.rule_id for outcome in report.rule_outcomes) == HARD_CONSTRAINT_IDS
    assert len(set(HARD_CONSTRAINT_IDS)) == 57
    assert all(outcome.status is not RuleStatus.BLOCKED for outcome in report.rule_outcomes)
    assert not set(report.evaluated_rule_ids) & set(report.not_applicable_rule_ids)
    assert set(report.evaluated_rule_ids) | set(report.not_applicable_rule_ids) == set(
        HARD_CONSTRAINT_IDS
    )
    assert all(
        outcome.visited
        == (outcome.status in {RuleStatus.PASS, RuleStatus.FAIL})
        for outcome in report.rule_outcomes
    )


def test_disabled_feature_rules_are_not_reported_as_pass(
    solved_piece: GenerationResult,
) -> None:
    report = verify_result(solved_piece)
    outcomes = {outcome.rule_id: outcome.status for outcome in report.rule_outcomes}
    assert outcomes["CM037"] is RuleStatus.NOT_APPLICABLE
    assert outcomes["CM043"] is RuleStatus.NOT_APPLICABLE
    assert outcomes["CM055"] is RuleStatus.NOT_APPLICABLE


def test_shape_failure_blocks_dependent_rules(solved_piece: GenerationResult) -> None:
    report = verify_result(replace(solved_piece, melody=solved_piece.melody[:-1]))
    assert not report.valid
    assert report.failed_rules == ("CM001",)
    assert "CM002" in report.blocked_rule_ids


def test_applicable_unvisited_rule_is_blocked() -> None:
    spec = GenerationSpec(require_authentic_cadence=False)
    outcomes = build_rule_outcomes(spec, (), visited_rules=("CM001",))
    by_id = {outcome.rule_id: outcome for outcome in outcomes}
    assert by_id["CM001"].status is RuleStatus.PASS
    assert by_id["CM002"].status is RuleStatus.BLOCKED
    assert by_id["CM002"].diagnostic_codes == ("CM002.NOT_VISITED",)


def test_failures_emit_structured_diagnostics(solved_piece: GenerationResult) -> None:
    corrupted = replace(solved_piece, melody=(0, *solved_piece.melody[1:]))
    report = verify_result(corrupted)
    diagnostic = next(item for item in report.diagnostics if item.rule_id == "CM002")
    assert diagnostic.code == "CM002.FAILED"
    assert diagnostic.feature == "tonal-core"
    assert diagnostic.location == "step:0"
    assert diagnostic.voice == "soprano"


def test_compiler_coverage_is_registered_from_real_phase_spans() -> None:
    spec = GenerationSpec(
        bars=1,
        beats_per_bar=2,
        subdivisions_per_beat=1,
        require_authentic_cadence=False,
        avoid_parallel_perfects=False,
    )
    problem = ConstraintMusicSolver()._compile(spec, DEFAULT_OBJECTIVE_WEIGHTS)
    registrations = problem.compiler_registrations

    assert COMPILED_HARD_CONSTRAINT_IDS == HARD_CONSTRAINT_IDS
    assert tuple(item.phase for item in registrations) == (
        "variable_domains",
        "harmony",
        "melody",
        "bass",
        "outer_voice_leading",
        "satb",
        "rhythm",
        "motif",
        "phrase",
    )
    assert registrations[0].constraint_start == 0
    assert all(
        left.constraint_end <= right.constraint_start
        for left, right in pairwise(registrations)
    )
    assert registrations[-1].constraint_end <= len(problem.model.proto.constraints)
    assert any(item.constraint_count > 0 for item in registrations)
    assert len({phase.name for phase in COMPILER_PHASES}) == len(COMPILER_PHASES)
