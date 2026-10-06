from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from research.validate_eh12_closure import (
    DEFAULT_DOCUMENT,
    DEFAULT_MATRIX,
    EXPECTED_WORK_PACKAGES,
    ClosureMatrixError,
    load_matrix,
    main,
    validate_matrix,
)


def test_closure_matrix_is_structurally_valid() -> None:
    summary = validate_matrix(load_matrix())

    assert summary.residuals == 11
    assert summary.deferred == 5
    assert summary.satisfied_gates == 3


def test_every_inherited_work_package_is_adjudicated_once() -> None:
    matrix = load_matrix()
    residuals = matrix["residuals"]

    assert isinstance(residuals, list)
    assert [item["work_package"] for item in residuals] == sorted(
        EXPECTED_WORK_PACKAGES
    )


def test_publication_gate_holds_while_blockers_remain() -> None:
    summary = validate_matrix(load_matrix())

    assert summary.publication_decision == "HOLD"
    assert summary.blockers == ("EH12-G04",)


def test_machine_matrix_is_deterministic_json() -> None:
    raw = DEFAULT_MATRIX.read_text(encoding="utf-8")
    parsed = json.loads(raw)

    assert parsed == load_matrix()
    assert json.loads(json.dumps(parsed, sort_keys=True)) == parsed


def test_closure_validator_cli_reports_current_decision(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main([]) == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert payload["publication_decision"] == "HOLD"
    assert payload["blockers"] == ["EH12-G04"]


def test_all_satisfied_evidence_references_exist() -> None:
    matrix = load_matrix()
    root = Path(__file__).resolve().parents[1]
    gates = matrix["eh12_gates"]

    assert isinstance(gates, list)
    references = [
        reference
        for gate in gates
        if gate["classification"] == "satisfied"
        for reference in gate["evidence_refs"]
    ]
    assert references
    assert all((root / reference).is_file() for reference in references)


def test_unknown_non_claim_cannot_justify_a_deferral() -> None:
    matrix = deepcopy(load_matrix())
    matrix["residuals"][2]["non_claim_ids"] = ["NC-404"]

    with pytest.raises(ClosureMatrixError, match="unknown non-claims"):
        validate_matrix(matrix)


def test_publication_decision_cannot_ignore_blockers() -> None:
    matrix = deepcopy(load_matrix())
    matrix["publication_decision"] = "COMPLETE"

    with pytest.raises(ClosureMatrixError, match="publication_decision must be HOLD"):
        validate_matrix(matrix)


def test_every_work_package_must_remain_in_the_matrix() -> None:
    matrix = deepcopy(load_matrix())
    matrix["residuals"].pop()

    with pytest.raises(ClosureMatrixError, match="exactly EH-01 through EH-11"):
        validate_matrix(matrix)


def test_satisfied_gate_cannot_reference_missing_evidence() -> None:
    matrix = deepcopy(load_matrix())
    matrix["eh12_gates"][0]["evidence_refs"] = ["missing-evidence.json"]

    with pytest.raises(ClosureMatrixError, match="evidence does not exist"):
        validate_matrix(matrix)


def test_human_matrix_cannot_drift_from_machine_classification(
    tmp_path: Path,
) -> None:
    rendered = DEFAULT_DOCUMENT.read_text(encoding="utf-8").replace(
        "| `EH12-R01` | EH-01 | Satisfied by PR-34 |",
        "| `EH12-R01` | EH-01 | Deferred → `NC-01` |",
    )
    document = tmp_path / "EH12_CLOSURE_MATRIX.md"
    document.write_text(rendered, encoding="utf-8")

    with pytest.raises(ClosureMatrixError, match="misclassifies EH12-R01"):
        validate_matrix(load_matrix(), document=document)


def test_human_matrix_cannot_drift_from_frozen_claim(tmp_path: Path) -> None:
    rendered = DEFAULT_DOCUMENT.read_text(encoding="utf-8").replace(
        "versioned, fail-closed generation and certification",
        "unversioned generation",
    )
    document = tmp_path / "EH12_CLOSURE_MATRIX.md"
    document.write_text(rendered, encoding="utf-8")

    with pytest.raises(ClosureMatrixError, match="frozen claim statement"):
        validate_matrix(load_matrix(), document=document)
