from __future__ import annotations

from dataclasses import replace

from constraint_music.contract import HARD_CONSTRAINT_IDS, RuleStatus
from constraint_music.models import GenerationResult
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
