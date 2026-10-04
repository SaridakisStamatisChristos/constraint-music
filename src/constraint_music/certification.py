"""Strict request-bound artifact and delivery certification APIs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .artifact_validation import validate_artifact_payload
from .contract import CONTRACT_VERSION, contract_digest
from .delivery import DeliveryReport, RenderProfile, output_digest, verify_delivery
from .models import GenerationSpec, ValidationReport
from .modulation_runtime import result_from_dict
from .provenance import (
    artifact_content_digest,
    composition_digest,
    request_digest,
    verify_artifact_integrity,
)
from .verifier import verify_result


@dataclass(frozen=True, slots=True)
class CertificationReport:
    accepted: bool
    scope: str
    semantic: ValidationReport
    integrity_issues: tuple[str, ...]
    certificate: Mapping[str, Any]
    delivery: DeliveryReport | None = None


def verify_artifact(
    payload: Mapping[str, Any],
    *,
    expected_spec: GenerationSpec,
    contract_version: str = CONTRACT_VERSION,
) -> CertificationReport:
    """Strictly certify an untrusted artifact against independently supplied context."""

    validate_artifact_payload(payload, require_current=True)
    result = result_from_dict(payload)
    semantic = verify_result(result)
    integrity = list(
        verify_artifact_integrity(result, payload, expected_spec=expected_spec)
    )
    if contract_version != CONTRACT_VERSION:
        integrity.append(
            f"requested contract {contract_version!r} is unsupported; "
            f"verifier has {CONTRACT_VERSION!r}"
        )
    if semantic.blocked_rule_ids:
        integrity.append(
            "semantic evaluation contains blocked rules: "
            + ", ".join(semantic.blocked_rule_ids)
        )
    accepted = semantic.valid and not integrity
    certificate = {
        "scope": "external-request artifact certification",
        "contract_version": CONTRACT_VERSION,
        "contract_sha256": contract_digest(),
        "request_sha256": request_digest(expected_spec),
        "composition_sha256": composition_digest(result),
        "artifact_content_sha256": artifact_content_digest(payload),
        "evaluated_rule_ids": list(semantic.evaluated_rule_ids),
        "not_applicable_rule_ids": list(semantic.not_applicable_rule_ids),
        "accepted": accepted,
    }
    return CertificationReport(
        accepted,
        "external-request artifact certification",
        semantic,
        tuple(integrity),
        certificate,
    )


def certify_delivery(
    payload: Mapping[str, Any],
    midi_path: str | Path,
    *,
    expected_spec: GenerationSpec,
    render_profile: str | RenderProfile = RenderProfile.CERTIFIED_SATB,
    contract_version: str = CONTRACT_VERSION,
) -> CertificationReport:
    artifact_report = verify_artifact(
        payload,
        expected_spec=expected_spec,
        contract_version=contract_version,
    )
    result = result_from_dict(payload)
    delivery = verify_delivery(result, midi_path, render_profile)
    certificate = dict(artifact_report.certificate)
    certificate.update(
        {
            "scope": "external-request artifact and MIDI delivery certification",
            "render_profile": delivery.profile.value,
            "output_sha256": output_digest(midi_path),
            "delivery_event_count": len(delivery.observed_events),
            "accepted": artifact_report.accepted and delivery.accepted,
        }
    )
    return CertificationReport(
        bool(certificate["accepted"]),
        "external-request artifact and MIDI delivery certification",
        artifact_report.semantic,
        artifact_report.integrity_issues,
        certificate,
        delivery,
    )
