"""Validate the EH-12 closure matrix and its human-readable mirror."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX = ROOT / "research/configs/eh12_closure_matrix.json"
DEFAULT_DOCUMENT = ROOT / "docs/EH12_CLOSURE_MATRIX.md"

EXPECTED_WORK_PACKAGES = {f"EH-{index:02d}" for index in range(1, 12)}
ALLOWED_CLASSIFICATIONS = {"satisfied", "deferred_by_non_claim", "blocker"}


class ClosureMatrixError(ValueError):
    """Raised when the EH-12 closure matrix is internally inconsistent."""


@dataclass(frozen=True, slots=True)
class ClosureSummary:
    residuals: int
    deferred: int
    blockers: tuple[str, ...]
    satisfied_gates: int
    publication_decision: str


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ClosureMatrixError(f"{location} must be an object")
    return value


def _sequence(value: object, location: str) -> Sequence[Any]:
    if not isinstance(value, list):
        raise ClosureMatrixError(f"{location} must be an array")
    return value


def _text(value: object, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ClosureMatrixError(f"{location} must be a non-empty string")
    return value


def _text_list(value: object, location: str) -> tuple[str, ...]:
    items = tuple(
        _text(item, f"{location}[{index}]")
        for index, item in enumerate(_sequence(value, location))
    )
    if not items:
        raise ClosureMatrixError(f"{location} must not be empty")
    return items


def _normalized_text(value: str) -> str:
    return " ".join(value.split())


def _normalized_document_text(value: str) -> str:
    return _normalized_text(
        " ".join(
            line[2:] if line.startswith("> ") else line
            for line in value.splitlines()
        )
    )


def load_matrix(path: Path = DEFAULT_MATRIX) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ClosureMatrixError("closure matrix root must be an object")
    return value


def _validate_documented_item(
    rendered: str, item: Mapping[str, Any], location: str
) -> None:
    item_id = _text(item.get("id"), f"{location}.id")
    rows = [line for line in rendered.splitlines() if f"| `{item_id}` |" in line]
    if len(rows) != 1:
        raise ClosureMatrixError(
            f"human closure matrix must contain exactly one table row for {item_id}"
        )
    row = rows[0]
    classification = _text(item.get("classification"), f"{location}.classification")
    if classification == "satisfied" and "| Satisfied" not in row:
        raise ClosureMatrixError(f"human closure matrix misclassifies {item_id}")
    if classification == "deferred_by_non_claim":
        if "| Deferred" not in row:
            raise ClosureMatrixError(f"human closure matrix misclassifies {item_id}")
        for non_claim_id in _text_list(
            item.get("non_claim_ids"), f"{location}.non_claim_ids"
        ):
            if f"`{non_claim_id}`" not in row:
                raise ClosureMatrixError(
                    f"human closure matrix omits {item_id} deferral {non_claim_id}"
                )
    if classification == "blocker":
        target = _text(item.get("target_slice"), f"{location}.target_slice")
        if f"| Blocker → {target}" not in row:
            raise ClosureMatrixError(f"human closure matrix misclassifies {item_id}")


def _validate_item(
    item: Mapping[str, Any],
    location: str,
    non_claim_ids: set[str],
    root: Path,
) -> tuple[str, str]:
    item_id = _text(item.get("id"), f"{location}.id")
    _text(item.get("title"), f"{location}.title")
    classification = _text(item.get("classification"), f"{location}.classification")
    if classification not in ALLOWED_CLASSIFICATIONS:
        raise ClosureMatrixError(
            f"{location}.classification must be one of {sorted(ALLOWED_CLASSIFICATIONS)}"
        )

    if classification == "satisfied":
        for reference in _text_list(item.get("evidence_refs"), f"{location}.evidence_refs"):
            if not (root / reference).is_file():
                raise ClosureMatrixError(f"{location} evidence does not exist: {reference}")
    elif classification == "deferred_by_non_claim":
        references = set(
            _text_list(item.get("non_claim_ids"), f"{location}.non_claim_ids")
        )
        unknown = references - non_claim_ids
        if unknown:
            raise ClosureMatrixError(f"{location} references unknown non-claims: {unknown}")
        _text(item.get("rationale"), f"{location}.rationale")
    else:
        _text(item.get("target_slice"), f"{location}.target_slice")
        _text_list(item.get("acceptance_criteria"), f"{location}.acceptance_criteria")

    return item_id, classification


def validate_matrix(
    matrix: Mapping[str, Any],
    *,
    root: Path = ROOT,
    document: Path = DEFAULT_DOCUMENT,
) -> ClosureSummary:
    if matrix.get("schema_version") != 1:
        raise ClosureMatrixError("schema_version must be 1")
    if matrix.get("program_id") != "EH-12":
        raise ClosureMatrixError("program_id must be EH-12")

    definitions = _mapping(
        matrix.get("classification_definitions"), "classification_definitions"
    )
    if set(definitions) != ALLOWED_CLASSIFICATIONS:
        raise ClosureMatrixError("classification definitions must cover every allowed value")
    for name, definition in definitions.items():
        _text(definition, f"classification_definitions.{name}")

    decision_policy = _mapping(matrix.get("decision_policy"), "decision_policy")
    _text(decision_policy.get("hold_when"), "decision_policy.hold_when")
    _text(decision_policy.get("complete_when"), "decision_policy.complete_when")

    non_claims = _sequence(matrix.get("non_claims"), "non_claims")
    non_claim_ids: set[str] = set()
    for index, raw_item in enumerate(non_claims):
        location = f"non_claims[{index}]"
        item = _mapping(raw_item, location)
        non_claim_ids.add(_text(item.get("id"), f"{location}.id"))
        _text(item.get("statement"), f"{location}.statement")
    if len(non_claim_ids) != len(non_claims):
        raise ClosureMatrixError("non-claim IDs must be unique")

    claim = _mapping(matrix.get("claim"), "claim")
    _text(claim.get("id"), "claim.id")
    _text(claim.get("statement"), "claim.statement")
    _text_list(claim.get("scope"), "claim.scope")
    excluded = set(
        _text_list(claim.get("excluded_non_claim_ids"), "claim.excluded_non_claim_ids")
    )
    if excluded != non_claim_ids:
        raise ClosureMatrixError("the frozen claim must reference every declared non-claim")

    residuals = _sequence(matrix.get("residuals"), "residuals")
    work_package_list: list[str] = []
    item_ids: set[str] = set()
    classifications: list[str] = []
    item_records: list[tuple[str, str]] = []
    for index, raw_item in enumerate(residuals):
        location = f"residuals[{index}]"
        item = _mapping(raw_item, location)
        work_package_list.append(
            _text(item.get("work_package"), f"{location}.work_package")
        )
        item_id, classification = _validate_item(
            item, location, non_claim_ids, root
        )
        if item_id in item_ids:
            raise ClosureMatrixError(f"duplicate closure item ID: {item_id}")
        item_ids.add(item_id)
        classifications.append(classification)
        item_records.append((item_id, classification))

    if (
        set(work_package_list) != EXPECTED_WORK_PACKAGES
        or len(work_package_list) != len(EXPECTED_WORK_PACKAGES)
    ):
        raise ClosureMatrixError(
            "residuals must adjudicate exactly EH-01 through EH-11"
        )

    gates = _sequence(matrix.get("eh12_gates"), "eh12_gates")
    gate_ids: set[str] = set()
    gate_classifications: list[str] = []
    gate_records: list[tuple[str, str]] = []
    for index, raw_item in enumerate(gates):
        location = f"eh12_gates[{index}]"
        item_id, classification = _validate_item(
            _mapping(raw_item, location), location, non_claim_ids, root
        )
        if item_id in gate_ids or item_id in item_ids:
            raise ClosureMatrixError(f"duplicate closure item ID: {item_id}")
        gate_ids.add(item_id)
        gate_classifications.append(classification)
        gate_records.append((item_id, classification))

    all_blockers = tuple(
        sorted(
            item_id
            for item_id, classification in [*item_records, *gate_records]
            if classification == "blocker"
        )
    )
    expected_decision = "HOLD" if all_blockers else "COMPLETE"
    decision = _text(matrix.get("publication_decision"), "publication_decision")
    if decision != expected_decision:
        raise ClosureMatrixError(
            f"publication_decision must be {expected_decision} for the current blockers"
        )

    rendered = document.read_text(encoding="utf-8")
    missing_from_document = {
        token for token in item_ids | gate_ids | non_claim_ids if token not in rendered
    }
    if missing_from_document:
        raise ClosureMatrixError(
            f"human closure matrix omits IDs: {sorted(missing_from_document)}"
        )
    if f"`{_text(claim.get('id'), 'claim.id')}`" not in rendered:
        raise ClosureMatrixError("human closure matrix omits the frozen claim ID")
    claim_statement = _text(claim.get("statement"), "claim.statement")
    if _normalized_text(claim_statement) not in _normalized_document_text(rendered):
        raise ClosureMatrixError("human closure matrix drifts from the frozen claim statement")
    if f"**Publication gate: {decision}.**" not in rendered:
        raise ClosureMatrixError("human closure matrix drifts from the publication decision")
    for index, raw_item in enumerate(residuals):
        _validate_documented_item(
            rendered, _mapping(raw_item, f"residuals[{index}]"), f"residuals[{index}]"
        )
    for index, raw_item in enumerate(gates):
        _validate_documented_item(
            rendered, _mapping(raw_item, f"eh12_gates[{index}]"), f"eh12_gates[{index}]"
        )

    return ClosureSummary(
        residuals=len(residuals),
        deferred=classifications.count("deferred_by_non_claim"),
        blockers=all_blockers,
        satisfied_gates=gate_classifications.count("satisfied"),
        publication_decision=decision,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--document", type=Path, default=DEFAULT_DOCUMENT)
    args = parser.parse_args(argv)
    summary = validate_matrix(load_matrix(args.matrix), document=args.document)
    print(json.dumps({
        "publication_decision": summary.publication_decision,
        "residuals": summary.residuals,
        "deferred": summary.deferred,
        "blockers": list(summary.blockers),
        "satisfied_gates": summary.satisfied_gates,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
