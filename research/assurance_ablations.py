"""Research-only assurance-channel ablations over the frozen EH-09 corpus.

These channels are observational projections of production checks.  They are
not switches in the certifier, and their overlapping responsibilities make
them unsuitable for claims of causal or statistical independence.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Final

from constraint_music.artifact_validation import ArtifactShapeError, validate_artifact_payload
from constraint_music.delivery import RenderProfile, verify_delivery
from constraint_music.models import GenerationSpec
from constraint_music.modulation_runtime import result_from_dict
from constraint_music.provenance import verify_artifact_integrity
from constraint_music.verifier import verify_result

from .mutations import MutationCase, generate_mutations
from .run_corruption_benchmark import _evaluate_case, _expected_spec

CHANNELS: Final = (
    "wire_shape",
    "semantic_rules",
    "integrity_request",
    "delivery_parseback",
)


def _signal(status: str, detected: bool, reasons: tuple[str, ...] = ()) -> dict[str, object]:
    return {"status": status, "detected": detected, "reasons": list(reasons)}


def _evaluate_channels(
    case: MutationCase,
    expected_spec: GenerationSpec,
) -> dict[str, dict[str, object]]:
    signals: dict[str, dict[str, object]] = {}
    try:
        validate_artifact_payload(case.payload)
    except ArtifactShapeError as exc:
        signals["wire_shape"] = _signal("FAIL", True, exc.issues)
        blocked = _signal("BLOCKED", False, ("wire-shape validation did not admit the artifact",))
        signals["semantic_rules"] = blocked
        signals["integrity_request"] = blocked
        signals["delivery_parseback"] = (
            blocked
            if case.delivery_bytes is not None
            else _signal("NOT_APPLICABLE", False)
        )
        return signals

    signals["wire_shape"] = _signal("PASS", False)
    result = result_from_dict(case.payload)

    semantic = verify_result(result)
    signals["semantic_rules"] = _signal(
        "FAIL" if not semantic.valid else "PASS",
        not semantic.valid,
        semantic.issues,
    )

    integrity_issues = verify_artifact_integrity(
        result,
        case.payload,
        expected_spec=_expected_spec(case, expected_spec),
    )
    signals["integrity_request"] = _signal(
        "FAIL" if integrity_issues else "PASS",
        bool(integrity_issues),
        integrity_issues,
    )

    if case.delivery_bytes is None:
        signals["delivery_parseback"] = _signal("NOT_APPLICABLE", False)
    else:
        with NamedTemporaryFile(suffix=".mid") as handle:
            handle.write(case.delivery_bytes)
            handle.flush()
            delivery = verify_delivery(result, Path(handle.name), RenderProfile.CERTIFIED_SATB)
        signals["delivery_parseback"] = _signal(
            "FAIL" if not delivery.accepted else "PASS",
            not delivery.accepted,
            delivery.issues,
        )
    return signals


def run_ablations(
    payload: dict[str, Any],
    expected_spec: GenerationSpec,
    *,
    delivery_bytes: bytes,
) -> list[dict[str, object]]:
    """Measure full and leave-one-channel-out signal coverage for every case."""

    rows: list[dict[str, object]] = []
    for case in generate_mutations(payload, delivery_bytes=delivery_bytes):
        signals = _evaluate_channels(case, expected_spec)
        detected_by = [name for name in CHANNELS if bool(signals[name]["detected"])]
        production_outcome, _ = _evaluate_case(case, expected_spec)
        rows.append(
            {
                "case_id": case.case_id,
                "split": case.split,
                "family": case.family,
                "cluster_id": case.cluster_id,
                "expected_class": case.expected_class,
                "production_outcome": production_outcome,
                "signals": signals,
                "detected_by": detected_by,
                "full_signal_decision": "DETECT" if detected_by else "ACCEPT",
            }
        )
    return rows


def summarize_ablations(rows: list[dict[str, object]]) -> dict[str, object]:
    """Summarize exact denominators and leave-one-channel-out losses."""

    attacks = [row for row in rows if row["expected_class"] != "valid"]
    controls = [row for row in rows if row["expected_class"] == "valid"]
    full_detected = sum(row["full_signal_decision"] == "DETECT" for row in attacks)
    false_positive_controls = [
        str(row["case_id"]) for row in controls if row["full_signal_decision"] == "DETECT"
    ]
    per_channel: dict[str, object] = {}
    for omitted in CHANNELS:
        omitted_detected = []
        unique = []
        for row in attacks:
            detected_by = set(row["detected_by"])  # type: ignore[arg-type]
            if detected_by - {omitted}:
                omitted_detected.append(str(row["case_id"]))
            if detected_by == {omitted}:
                unique.append(str(row["case_id"]))
        escaped = sorted(set(str(row["case_id"]) for row in attacks) - set(omitted_detected))
        per_channel[omitted] = {
            "attack_denominator": len(attacks),
            "detected_without_channel": len(omitted_detected),
            "escaped_without_channel": len(escaped),
            "coverage_without_channel": round(len(omitted_detected) / len(attacks), 6),
            "unique_catch_count": len(unique),
            "unique_catch_case_ids": sorted(unique),
            "escape_case_ids": escaped,
        }

    return {
        "schema_version": 1,
        "study_type": "observational assurance-channel signal ablation",
        "claim_boundary": (
            "Finite leave-one-channel-out signal coverage over the frozen EH-09 corpus. "
            "Channels overlap operationally; results are not causal, statistically "
            "independent, or production configurations."
        ),
        "channels": list(CHANNELS),
        "case_denominator": len(rows),
        "attack_denominator": len(attacks),
        "control_denominator": len(controls),
        "full_detected": full_detected,
        "full_attack_coverage": round(full_detected / len(attacks), 6),
        "false_positive_controls": false_positive_controls,
        "production_outcomes": dict(
            sorted(Counter(str(row["production_outcome"]) for row in rows).items())
        ),
        "leave_one_channel_out": per_channel,
    }
