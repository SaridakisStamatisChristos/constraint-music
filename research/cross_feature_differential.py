"""Deterministic cross-feature controls and independently adjudicated faults."""

from __future__ import annotations

from dataclasses import replace
from functools import cache
from hashlib import sha256
from pathlib import Path

from constraint_music.modal_mixture import canonical_modal_source
from constraint_music.models import GenerationSpec, RhythmState
from constraint_music.modulation_runtime import ModulatedSatbGenerationResult
from constraint_music.satb import SatbGenerationResult
from constraint_music.secondary_leading_tone_seventh_runtime import (
    reconstruct_secondary_leading_tone_seventh,
)
from constraint_music.solver import ConstraintMusicSolver
from constraint_music.theory import Key
from constraint_music.verifier import verify_result

from .oracle.contextual_harmony import TonalMode
from .oracle.modulation import OracleKey, adjudicate_modulation_plan
from .oracle.rhythm_phrase import RhythmPolicy, adjudicate_rhythm
from .oracle.secondary_seventh import adjudicate_secondary_seventh_context

_ROOT = Path(__file__).resolve().parents[1]
_SEEDS = {
    "tonicization": 7101,
    "modal_mixture": 7102,
    "rhythm": 7103,
    "authentic_cadence": 7104,
    "modulation": 7105,
}


def _base_spec(**overrides: object) -> GenerationSpec:
    values: dict[str, object] = {
        "bars": 1,
        "beats_per_bar": 4,
        "subdivisions_per_beat": 1,
        "require_authentic_cadence": False,
        "harmony_vocabulary": "triads+sevenths",
        "secondary_leading_tone_seventh_enabled": True,
        "minimum_secondary_leading_tone_seventh_chords": 1,
        "avoid_parallel_perfects": False,
        "workers": 1,
        "max_time_seconds": 20,
        "tension_curve": (0.8, 0.6, 0.3, 0.1),
    }
    values.update(overrides)
    return GenerationSpec(**values)  # type: ignore[arg-type]


def _specs() -> dict[str, GenerationSpec]:
    return {
        "tonicization": _base_spec(
            tonicization_enabled=True,
            seed=_SEEDS["tonicization"],
        ),
        "modal_mixture": _base_spec(
            modal_mixture_enabled=True,
            seed=_SEEDS["modal_mixture"],
        ),
        "rhythm": _base_spec(
            rhythm_enabled=True,
            max_onsets_per_bar=4,
            max_rests_per_bar=4,
            max_ties_per_bar=4,
            seed=_SEEDS["rhythm"],
        ),
        "authentic_cadence": _base_spec(
            require_authentic_cadence=True,
            seed=_SEEDS["authentic_cadence"],
        ),
        "modulation": _base_spec(
            beats_per_bar=6,
            tension_curve=(0.8, 0.7, 0.6, 0.4, 0.2, 0.1),
            modulation_enabled=True,
            modulation_destination_key="G",
            modulation_boundary_beat=3,
            seed=_SEEDS["modulation"],
        ),
    }


def _generate(spec: GenerationSpec) -> SatbGenerationResult:
    result = ConstraintMusicSolver().generate(spec)
    if not isinstance(result, SatbGenerationResult):  # pragma: no cover - invariant
        raise AssertionError("Cross-feature evidence requires a SATB result")
    report = verify_result(result)
    if not report.valid:
        raise AssertionError(f"Generated control is invalid: {report.issues}")
    return result


def _secondary_beat(result: SatbGenerationResult) -> int:
    matches = tuple(
        beat
        for beat in range(result.spec.total_beats - 1)
        if reconstruct_secondary_leading_tone_seventh(result, beat) is not None
    )
    if not matches:
        raise AssertionError("Required secondary seventh is absent")
    return matches[0]


def _rhythm_policy(spec: GenerationSpec, *, require_final_onset: bool) -> RhythmPolicy:
    return RhythmPolicy(
        bars=spec.bars,
        steps_per_bar=spec.steps_per_bar,
        enabled=spec.rhythm_enabled,
        min_onsets_per_bar=spec.min_onsets_per_bar,
        max_onsets_per_bar=spec.max_onsets_per_bar,
        min_rests_per_bar=spec.min_rests_per_bar,
        max_rests_per_bar=spec.max_rests_per_bar,
        min_ties_per_bar=spec.min_ties_per_bar,
        max_ties_per_bar=spec.max_ties_per_bar,
        max_consecutive_rests=spec.max_consecutive_rests,
        max_tie_steps=spec.max_tie_steps,
        require_bar_downbeat_onset=spec.require_bar_downbeat_onset,
        require_final_onset=require_final_onset,
    )


def _oracle_key(key: Key) -> OracleKey:
    return OracleKey(key.tonic_pc, TonalMode(key.mode.value))


def _nested_bool(case: dict[str, object], section: str, field: str) -> bool:
    nested = case[section]
    if not isinstance(nested, dict):  # pragma: no cover - construction invariant
        raise AssertionError(f"{section} is not a mapping")
    return bool(nested[field])


def _case(
    *,
    feature: str,
    control: SatbGenerationResult,
    fault: SatbGenerationResult,
    oracle_valid: bool,
    oracle_reason: object,
    expected_rule: str,
) -> dict[str, object]:
    control_report = verify_result(control)
    fault_report = verify_result(fault)
    return {
        "feature": feature,
        "seed": control.spec.seed,
        "control": {
            "verifier_valid": control_report.valid,
            "secondary_beat": _secondary_beat(control),
        },
        "fault": {
            "expected_rule": expected_rule,
            "oracle_valid": oracle_valid,
            "oracle_reason": oracle_reason,
            "verifier_valid": fault_report.valid,
            "failed_rules": fault_report.failed_rules,
        },
        "disagreement": oracle_valid != fault_report.valid,
        "escaped": oracle_valid or fault_report.valid,
    }


def _source_hash(path: str) -> str:
    return sha256((_ROOT / path).read_bytes()).hexdigest()


@cache
def cross_feature_differential_report() -> dict[str, object]:
    """Exercise five feature intersections with one isolated metadata fault each."""

    controls = {name: _generate(spec) for name, spec in _specs().items()}
    cases: list[dict[str, object]] = []

    tonicization = controls["tonicization"]
    beat = _secondary_beat(tonicization)
    targets = list(tonicization.tonicization_targets)
    targets[beat] = None
    decision = adjudicate_secondary_seventh_context(
        beat=beat,
        total_beats=tonicization.spec.total_beats,
        target_supported=False,
        modal_overlap=False,
        require_authentic_cadence=False,
        modulation_boundary_beat=None,
    )
    cases.append(
        _case(
            feature="tonicization",
            control=tonicization,
            fault=replace(tonicization, tonicization_targets=tuple(targets)),
            oracle_valid=decision.valid,
            oracle_reason=decision.reasons,
            expected_rule="CM055",
        )
    )

    modal = controls["modal_mixture"]
    beat = _secondary_beat(modal)
    sources = list(modal.modal_sources)
    sources[beat] = canonical_modal_source(modal.spec.active_key_at_beat(beat))
    decision = adjudicate_secondary_seventh_context(
        beat=beat,
        total_beats=modal.spec.total_beats,
        target_supported=True,
        modal_overlap=True,
        require_authentic_cadence=False,
        modulation_boundary_beat=None,
    )
    cases.append(
        _case(
            feature="modal_mixture",
            control=modal,
            fault=replace(modal, modal_sources=tuple(sources)),
            oracle_valid=decision.valid,
            oracle_reason=decision.reasons,
            expected_rule="CM055",
        )
    )

    rhythm = controls["rhythm"]
    states = list(rhythm.effective_rhythm)
    states[0] = RhythmState.TIE
    rhythm_fault = replace(rhythm, rhythm=tuple(states))
    rhythm_decision = adjudicate_rhythm(
        rhythm_fault.melody,
        rhythm_fault.rhythm_names,
        policy=_rhythm_policy(rhythm.spec, require_final_onset=False),
    )
    cases.append(
        _case(
            feature="rhythm",
            control=rhythm,
            fault=rhythm_fault,
            oracle_valid=rhythm_decision.valid,
            oracle_reason=rhythm_decision.reasons,
            expected_rule="CM018",
        )
    )

    cadence = controls["authentic_cadence"]
    states = list(cadence.effective_rhythm)
    states[-1] = RhythmState.REST
    cadence_fault = replace(cadence, rhythm=tuple(states))
    cadence_decision = adjudicate_rhythm(
        cadence_fault.melody,
        cadence_fault.rhythm_names,
        policy=_rhythm_policy(cadence.spec, require_final_onset=True),
    )
    cases.append(
        _case(
            feature="authentic_cadence",
            control=cadence,
            fault=cadence_fault,
            oracle_valid=cadence_decision.valid,
            oracle_reason=cadence_decision.reasons,
            expected_rule="CM021",
        )
    )

    modulation = controls["modulation"]
    if not isinstance(modulation, ModulatedSatbGenerationResult):
        raise AssertionError("Modulation control omitted persistent key contexts")
    stale_contexts = (modulation.spec.tonal_key,) * modulation.spec.total_beats
    modulation_fault = replace(modulation, key_contexts=stale_contexts)
    destination = modulation.spec.modulation_destination
    boundary = modulation.spec.modulation_boundary_beat
    if destination is None or boundary is None:  # pragma: no cover - spec invariant
        raise AssertionError("Modulation control is incomplete")
    modulation_decision = adjudicate_modulation_plan(
        source=_oracle_key(modulation.spec.tonal_key),
        destination=_oracle_key(destination),
        boundary=boundary,
        total_beats=modulation.spec.total_beats,
        serialized_contexts=tuple(_oracle_key(key) for key in stale_contexts),
    )
    cases.append(
        _case(
            feature="modulation",
            control=modulation,
            fault=modulation_fault,
            oracle_valid=modulation_decision.valid,
            oracle_reason=modulation_decision.reason,
            expected_rule="CM048",
        )
    )

    disagreements = sum(bool(case["disagreement"]) for case in cases)
    escaped_faults = sum(bool(case["escaped"]) for case in cases)
    return {
        "schema_version": 1,
        "claim_boundary": (
            "Five deterministic feature intersections: secondary sevenths coenabled "
            "with tonicization, modal mixture, rhythm, authentic cadence, and modulation. "
            "Each partition compares one targeted fault with an independent local oracle; "
            "this is not global whole-composition oracle equivalence."
        ),
        "visited": len(cases) * 2,
        "controls_accepted": sum(
            _nested_bool(case, "control", "verifier_valid") for case in cases
        ),
        "faults_rejected": sum(
            not _nested_bool(case, "fault", "verifier_valid") for case in cases
        ),
        "disagreements": disagreements,
        "escaped_faults": escaped_faults,
        "cases": cases,
        "implementation_hashes": {
            path: _source_hash(path)
            for path in (
                "research/oracle/modulation.py",
                "research/oracle/rhythm_phrase.py",
                "research/oracle/secondary_seventh.py",
                "src/constraint_music/verifier.py",
            )
        },
    }
