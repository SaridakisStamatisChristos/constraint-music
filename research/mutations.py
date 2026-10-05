"""Frozen, deterministic semantic-corruption corpus generation."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from io import BytesIO
from typing import Any, Literal

from mido import MidiFile

from constraint_music.modulation_runtime import result_from_dict
from constraint_music.provenance import artifact_content_digest, artifact_payload

Split = Literal["development", "evaluation"]


@dataclass(frozen=True, slots=True)
class MutationCase:
    case_id: str
    split: Split
    tier: str
    family: str
    cluster_id: str
    expected_class: str
    expected_outcomes: tuple[str, ...]
    payload: dict[str, Any]
    delivery_bytes: bytes | None = None
    expected_spec_variant: str = "identity"


@dataclass(frozen=True, slots=True)
class CaseDefinition:
    case_id: str
    split: Split
    tier: str
    family: str
    cluster_id: str
    expected_class: str
    expected_outcomes: tuple[str, ...]
    mutation: str


_DEFINITIONS = (
    CaseDefinition(
        "control.artifact",
        "development",
        "T0",
        "control",
        "control-artifact",
        "valid",
        ("ACCEPT",),
        "identity",
    ),
    CaseDefinition(
        "control.delivery",
        "evaluation",
        "T0",
        "control",
        "control-delivery",
        "valid",
        ("ACCEPT",),
        "delivery.identity",
    ),
    CaseDefinition(
        "music.soprano-pitch",
        "development",
        "T1",
        "realized-music",
        "rm-outer-upper",
        "invalid",
        ("REJECT",),
        "music.soprano-pitch.naive",
    ),
    CaseDefinition(
        "music.alto-pitch",
        "development",
        "T2",
        "realized-music",
        "rm-outer-upper",
        "invalid",
        ("REJECT",),
        "music.alto-pitch.rehash",
    ),
    CaseDefinition(
        "music.tenor-pitch",
        "evaluation",
        "T3",
        "realized-music",
        "rm-inner-lower",
        "invalid",
        ("REJECT",),
        "music.tenor-pitch.coordinated",
    ),
    CaseDefinition(
        "music.bass-pitch",
        "evaluation",
        "T3",
        "realized-music",
        "rm-inner-lower",
        "invalid",
        ("REJECT",),
        "music.bass-pitch.coordinated",
    ),
    CaseDefinition(
        "music.melody-pitch",
        "development",
        "T2",
        "realized-music",
        "rm-melodic-line",
        "invalid",
        ("REJECT",),
        "music.melody-pitch.rehash",
    ),
    CaseDefinition(
        "music.final-rest",
        "development",
        "T3",
        "realized-music",
        "rm-melodic-line",
        "invalid",
        ("REJECT",),
        "music.final-rest.coordinated",
    ),
    CaseDefinition(
        "harmony.illegal-inversion",
        "development",
        "T1",
        "harmonic-claims",
        "hm-form",
        "invalid",
        ("REJECT",),
        "harmony.inversion.naive",
    ),
    CaseDefinition(
        "harmony.false-kind",
        "development",
        "T3",
        "harmonic-claims",
        "hm-form",
        "invalid",
        ("REJECT",),
        "harmony.kind.coordinated",
    ),
    CaseDefinition(
        "harmony.false-degree",
        "evaluation",
        "T3",
        "harmonic-claims",
        "hm-function",
        "invalid",
        ("REJECT",),
        "harmony.degree.coordinated",
    ),
    CaseDefinition(
        "harmony.false-target",
        "evaluation",
        "T2",
        "harmonic-claims",
        "hm-function",
        "invalid",
        ("REJECT",),
        "harmony.target.rehash",
    ),
    CaseDefinition(
        "harmony.false-modal-source",
        "evaluation",
        "T2",
        "harmonic-claims",
        "hm-claims",
        "invalid",
        ("REJECT",),
        "harmony.modal-source.rehash",
    ),
    CaseDefinition(
        "harmony.false-display-name",
        "evaluation",
        "T2",
        "harmonic-claims",
        "hm-claims",
        "invalid",
        ("REJECT",),
        "harmony.display-name.rehash",
    ),
    CaseDefinition(
        "shape.missing-tenor",
        "development",
        "T4",
        "structure",
        "st-cardinality",
        "malformed",
        ("BLOCKED",),
        "shape.missing-tenor",
    ),
    CaseDefinition(
        "shape.short-bass",
        "development",
        "T4",
        "structure",
        "st-cardinality",
        "malformed",
        ("BLOCKED",),
        "shape.short-bass",
    ),
    CaseDefinition(
        "shape.boolean-degree",
        "evaluation",
        "T4",
        "structure",
        "st-wire-types",
        "malformed",
        ("BLOCKED",),
        "shape.boolean-degree",
    ),
    CaseDefinition(
        "shape.legacy-schema",
        "evaluation",
        "T4",
        "structure",
        "st-wire-types",
        "malformed",
        ("BLOCKED",),
        "shape.legacy-schema",
    ),
    CaseDefinition(
        "shape.missing-validation",
        "evaluation",
        "T4",
        "structure",
        "st-root-sections",
        "malformed",
        ("BLOCKED",),
        "shape.missing-validation",
    ),
    CaseDefinition(
        "shape.nonobject-music",
        "evaluation",
        "T4",
        "structure",
        "st-root-sections",
        "malformed",
        ("BLOCKED",),
        "shape.nonobject-music",
    ),
    CaseDefinition(
        "integrity.contract-version",
        "development",
        "T2",
        "integrity-request",
        "in-contract",
        "invalid",
        ("REJECT",),
        "integrity.contract-version.rehash",
    ),
    CaseDefinition(
        "integrity.contract-digest",
        "development",
        "T2",
        "integrity-request",
        "in-contract",
        "invalid",
        ("REJECT",),
        "integrity.contract-digest.rehash",
    ),
    CaseDefinition(
        "integrity.empty-rule-claim",
        "evaluation",
        "T2",
        "integrity-request",
        "in-provenance",
        "invalid",
        ("REJECT",),
        "integrity.empty-rule-claim.rehash",
    ),
    CaseDefinition(
        "integrity.composition-digest",
        "evaluation",
        "T2",
        "integrity-request",
        "in-provenance",
        "invalid",
        ("REJECT",),
        "integrity.composition-digest.rehash",
    ),
    CaseDefinition(
        "integrity.objective-vector",
        "evaluation",
        "T2",
        "integrity-request",
        "in-objective",
        "invalid",
        ("REJECT",),
        "integrity.objective-vector.rehash",
    ),
    CaseDefinition(
        "request.external-seed",
        "evaluation",
        "T3",
        "integrity-request",
        "in-objective",
        "invalid",
        ("REJECT",),
        "request.external-seed",
    ),
    CaseDefinition(
        "delivery.changed-pitch",
        "development",
        "T1",
        "delivery",
        "dl-notes",
        "invalid",
        ("REJECT",),
        "delivery.changed-pitch",
    ),
    CaseDefinition(
        "delivery.changed-channel",
        "development",
        "T1",
        "delivery",
        "dl-notes",
        "invalid",
        ("REJECT",),
        "delivery.changed-channel",
    ),
    CaseDefinition(
        "delivery.missing-track",
        "evaluation",
        "T1",
        "delivery",
        "dl-structure",
        "invalid",
        ("REJECT",),
        "delivery.missing-track",
    ),
    CaseDefinition(
        "delivery.duplicate-track",
        "evaluation",
        "T1",
        "delivery",
        "dl-structure",
        "invalid",
        ("REJECT",),
        "delivery.duplicate-track",
    ),
    CaseDefinition(
        "delivery.wrong-key",
        "evaluation",
        "T1",
        "delivery",
        "dl-context",
        "invalid",
        ("REJECT",),
        "delivery.wrong-key",
    ),
    CaseDefinition(
        "delivery.wrong-division",
        "evaluation",
        "T1",
        "delivery",
        "dl-context",
        "invalid",
        ("REJECT",),
        "delivery.wrong-division",
    ),
)


def mutation_manifest() -> dict[str, object]:
    """Return the frozen adjudication manifest without fixture-specific values."""

    return {
        "schema_version": 1,
        "claim_boundary": (
            "A deterministic artifact-and-delivery corruption corpus. Cases sharing a "
            "cluster stay in one split; metrics do not claim independence within clusters."
        ),
        "tiers": {
            "T0": "valid control",
            "T1": "direct semantic or delivery mutation",
            "T2": "mutation with repaired artifact-content digest",
            "T3": "coordinated semantic claims or independently changed request",
            "T4": "malformed wire structure blocked before reconstruction",
        },
        "cases": [
            {
                "case_id": case.case_id,
                "split": case.split,
                "tier": case.tier,
                "family": case.family,
                "cluster_id": case.cluster_id,
                "expected_class": case.expected_class,
                "expected_outcomes": list(case.expected_outcomes),
                "mutation": case.mutation,
            }
            for case in _DEFINITIONS
        ],
    }


def _rehash(payload: dict[str, Any]) -> dict[str, Any]:
    provenance = _mapping(payload, "provenance")
    provenance["artifact_content_sha256"] = artifact_content_digest(payload)
    return payload


def _coordinated(payload: dict[str, Any]) -> dict[str, Any]:
    return artifact_payload(result_from_dict(payload))


def _mapping(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):  # pragma: no cover - valid fixture invariant
        raise AssertionError(f"Fixture {key!r} is not an object")
    return value


def _artifact_mutation(payload: dict[str, Any], mutation: str) -> dict[str, Any]:
    changed = deepcopy(payload)
    music = _mapping(changed, "music")
    provenance = _mapping(changed, "provenance")
    search = _mapping(changed, "search")
    if mutation == "identity" or mutation.startswith("delivery."):
        return changed
    if mutation.startswith("music.soprano-pitch"):
        music["soprano_midi"][0] += 1
    elif mutation.startswith("music.alto-pitch"):
        music["alto_midi"][0] += 1
    elif mutation.startswith("music.tenor-pitch"):
        music["tenor_midi"][0] += 1
    elif mutation.startswith("music.bass-pitch"):
        music["bass_midi"][0] += 1
    elif mutation.startswith("music.melody-pitch"):
        music["melody_midi"][0] += 1
    elif mutation.startswith("music.final-rest"):
        music["rhythm"][-1] = "rest"
    elif mutation.startswith("harmony.inversion"):
        music["chord_inversions"][0] = 3
    elif mutation.startswith("harmony.kind"):
        music["chord_kinds"][0] = "seventh"
    elif mutation.startswith("harmony.degree"):
        music["chord_degrees"][0] = 1
    elif mutation.startswith("harmony.target"):
        music["tonicization_targets"][0] = 1
    elif mutation.startswith("harmony.modal-source"):
        music["modal_sources"][0] = "parallel-natural-minor"
    elif mutation.startswith("harmony.display-name"):
        music["chord_form_names"][0] = "forged"
    elif mutation == "shape.missing-tenor":
        music.pop("tenor_midi")
    elif mutation == "shape.short-bass":
        music["bass_midi"].pop()
    elif mutation == "shape.boolean-degree":
        music["chord_degrees"][0] = True
    elif mutation == "shape.legacy-schema":
        changed["schema_version"] = "2.12"
    elif mutation == "shape.missing-validation":
        changed.pop("validation")
    elif mutation == "shape.nonobject-music":
        changed["music"] = []
    elif mutation.startswith("integrity.contract-version"):
        provenance["constraint_contract_version"] = "forged"
    elif mutation.startswith("integrity.contract-digest"):
        provenance["constraint_contract_sha256"] = "0" * 64
    elif mutation.startswith("integrity.empty-rule-claim"):
        provenance["verified_constraint_ids"] = []
    elif mutation.startswith("integrity.composition-digest"):
        provenance["composition_sha256"] = "0" * 64
    elif mutation.startswith("integrity.objective-vector"):
        objective_vector = _mapping(search, "objective_vector")
        objective_vector["tension_deviation"] += 1
    elif mutation == "request.external-seed":
        return changed
    else:  # pragma: no cover - manifest/code synchronization invariant
        raise AssertionError(f"Unknown mutation {mutation!r}")
    if mutation.endswith(".coordinated"):
        return _coordinated(changed)
    if mutation.endswith(".rehash"):
        return _rehash(changed)
    return changed


def _midi_mutation(source: bytes, mutation: str) -> bytes:
    if mutation == "delivery.identity":
        return source
    midi = MidiFile(file=BytesIO(source))
    if mutation == "delivery.changed-pitch":
        track = next(track for track in midi.tracks if track.name == "Soprano")
        original: int | None = None
        for message in track:
            if original is None and message.type == "note_on":
                original = message.note
                message.note += 1
            elif original is not None and message.type == "note_off" and message.note == original:
                message.note += 1
                break
    elif mutation == "delivery.changed-channel":
        track = next(track for track in midi.tracks if track.name == "Soprano")
        for message in track:
            if message.type in {"note_on", "note_off"}:
                message.channel = 5
    elif mutation == "delivery.missing-track":
        midi.tracks.remove(next(track for track in midi.tracks if track.name == "Tenor"))
    elif mutation == "delivery.duplicate-track":
        midi.tracks.append(
            deepcopy(next(track for track in midi.tracks if track.name == "Soprano"))
        )
    elif mutation == "delivery.wrong-key":
        message = next(
            message for track in midi.tracks for message in track if message.type == "key_signature"
        )
        message.key = "G"
    elif mutation == "delivery.wrong-division":
        midi.ticks_per_beat *= 2
    else:  # pragma: no cover - manifest/code synchronization invariant
        raise AssertionError(f"Unknown delivery mutation {mutation!r}")
    output = BytesIO()
    midi.save(file=output)
    return output.getvalue()


def generate_mutations(
    payload: dict[str, Any],
    *,
    delivery_bytes: bytes | None = None,
) -> tuple[MutationCase, ...]:
    """Create every named attack without modifying the source fixture."""

    cases: list[MutationCase] = []
    for definition in _DEFINITIONS:
        is_delivery = definition.mutation.startswith("delivery.")
        if is_delivery and delivery_bytes is None:
            continue
        cases.append(
            MutationCase(
                case_id=definition.case_id,
                split=definition.split,
                tier=definition.tier,
                family=definition.family,
                cluster_id=definition.cluster_id,
                expected_class=definition.expected_class,
                expected_outcomes=definition.expected_outcomes,
                payload=_artifact_mutation(payload, definition.mutation),
                delivery_bytes=(
                    _midi_mutation(delivery_bytes, definition.mutation)
                    if is_delivery and delivery_bytes is not None
                    else None
                ),
                expected_spec_variant=(
                    "seed+1" if definition.mutation == "request.external-seed" else "identity"
                ),
            )
        )
    return tuple(cases)
