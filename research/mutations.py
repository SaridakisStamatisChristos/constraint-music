"""Deterministic semantic-corruption corpus generation."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from constraint_music.provenance import artifact_content_digest


@dataclass(frozen=True, slots=True)
class MutationCase:
    case_id: str
    tier: str
    family: str
    expected_class: str
    payload: dict[str, Any]


def generate_mutations(payload: dict[str, Any]) -> tuple[MutationCase, ...]:
    """Create independent, named attacks without modifying the source payload."""

    cases: list[MutationCase] = []

    changed_pitch = deepcopy(payload)
    changed_pitch["music"]["alto_midi"][0] += 1
    cases.append(
        MutationCase("music.alto-pitch", "T1", "realized-music", "invalid", changed_pitch)
    )

    empty_claim = deepcopy(payload)
    empty_claim["provenance"]["verified_constraint_ids"] = []
    empty_claim["provenance"]["artifact_content_sha256"] = artifact_content_digest(empty_claim)
    cases.append(
        MutationCase(
            "integrity.empty-rule-claim",
            "T2",
            "integrity-request",
            "invalid",
            empty_claim,
        )
    )

    missing_voice = deepcopy(payload)
    missing_voice["music"].pop("tenor_midi")
    cases.append(
        MutationCase("shape.missing-tenor", "T4", "structure", "malformed", missing_voice)
    )

    wrong_inversion = deepcopy(payload)
    wrong_inversion["music"]["chord_inversions"][0] = 3
    cases.append(
        MutationCase(
            "harmony.illegal-inversion",
            "T1",
            "harmonic-claims",
            "invalid",
            wrong_inversion,
        )
    )
    return tuple(cases)

