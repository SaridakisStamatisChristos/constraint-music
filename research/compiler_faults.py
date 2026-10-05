"""Deterministic fault injection at the solver's independent finalization boundary."""

from __future__ import annotations

from dataclasses import replace
from functools import cache
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path

from constraint_music.errors import InternalVerificationError
from constraint_music.models import GenerationResult, GenerationSpec
from constraint_music.objective import evaluate_objective_vector
from constraint_music.provenance import request_digest
from constraint_music.satb import SatbGenerationResult
from constraint_music.secondary_leading_tone_seventh_runtime import (
    reconstruct_secondary_leading_tone_seventh,
)
from constraint_music.solver import ConstraintMusicSolver, finalize_generated_result

_ORTOOLS_VERSION = "9.15.6755"
_SEED = 6131
_ROOT = Path(__file__).resolve().parents[1]


def _control_result() -> SatbGenerationResult:
    result = ConstraintMusicSolver().generate(
        GenerationSpec(
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
    )
    if not isinstance(result, SatbGenerationResult):  # pragma: no cover - compiler invariant
        raise AssertionError("Expected solver-native SATB output")
    return result


def _secondary_beat(result: SatbGenerationResult) -> int:
    for beat in range(result.spec.total_beats):
        if reconstruct_secondary_leading_tone_seventh(result, beat) is not None:
            return beat
    raise AssertionError("Pinned control omitted its required secondary seventh")


def _with_voice(
    result: SatbGenerationResult,
    label: str,
    values: tuple[int, ...],
) -> SatbGenerationResult:
    if label == "soprano":
        return replace(result, soprano=values, melody=values)
    if label == "alto":
        return replace(result, alto=values)
    if label == "tenor":
        return replace(result, tenor=values)
    if label == "bass":
        return replace(result, bass=values)
    raise ValueError(f"Unknown SATB voice: {label}")


def _semantic_faults(
    control: SatbGenerationResult,
) -> tuple[tuple[str, SatbGenerationResult], ...]:
    beat = _secondary_beat(control)
    reconstruction = reconstruct_secondary_leading_tone_seventh(control, beat)
    if reconstruction is None:  # pragma: no cover - established by _secondary_beat
        raise AssertionError("Secondary-seventh reconstruction disappeared")
    _quality, tones = reconstruction

    melody = list(control.melody)
    melody[0] = 0
    melody_domain = replace(control, melody=tuple(melody))

    targets = list(control.tonicization_targets)
    targets[beat] = None
    target_metadata = replace(control, tonicization_targets=tuple(targets))

    inversions = list(control.chord_inversions)
    inversions[beat] = (inversions[beat] + 1) % 4
    inversion_bass = replace(control, chord_inversions=tuple(inversions))

    root = tones[0]
    tendency_resolution: SatbGenerationResult | None = None
    for label in ("soprano", "alto", "tenor", "bass"):
        voice = getattr(control, label)
        if voice[beat] % 12 != root:
            continue
        forged = list(voice)
        forged[beat + 1] = forged[beat] + 2
        tendency_resolution = _with_voice(control, label, tuple(forged))
        break
    if tendency_resolution is None:  # pragma: no cover - exact realization invariant
        raise AssertionError("Secondary seventh omitted its local leading tone")

    return (
        ("melody_domain", melody_domain),
        ("target_metadata", target_metadata),
        ("inversion_bass", inversion_bass),
        ("tendency_resolution", tendency_resolution),
    )


def _observe(
    result: GenerationResult,
    compiled_vector: tuple[tuple[str, int], ...],
) -> tuple[str, str | None]:
    try:
        finalize_generated_result(result, compiled_vector)
    except InternalVerificationError as exc:
        return "REJECT", str(exc)
    return "ACCEPT", None


def _source_hash(relative_path: str) -> str:
    return sha256((_ROOT / relative_path).read_bytes()).hexdigest()


@cache
def generator_boundary_fault_report() -> dict[str, object]:
    """Run one pinned control and five named boundary corruptions."""

    observed_version = version("ortools")
    if observed_version != _ORTOOLS_VERSION:
        raise RuntimeError(
            f"Pinned fault evidence requires ortools=={_ORTOOLS_VERSION}, "
            f"found {observed_version}"
        )

    control = _control_result()
    compiled_vector = evaluate_objective_vector(control)
    cases: dict[str, dict[str, object]] = {}

    outcome, diagnostic = _observe(control, compiled_vector)
    cases["control"] = {
        "expected": "ACCEPT",
        "observed": outcome,
        "diagnostic": diagnostic,
    }

    for name, corrupted in _semantic_faults(control):
        outcome, diagnostic = _observe(corrupted, compiled_vector)
        cases[name] = {
            "expected": "REJECT",
            "observed": outcome,
            "diagnostic": diagnostic,
        }

    objective_name, objective_value = compiled_vector[0]
    corrupted_vector = (
        (objective_name, objective_value + 1),
        *compiled_vector[1:],
    )
    outcome, diagnostic = _observe(control, corrupted_vector)
    cases["compiled_objective"] = {
        "expected": "REJECT",
        "observed": outcome,
        "diagnostic": diagnostic,
    }

    escaped_faults = sum(
        case["observed"] != case["expected"] for case in cases.values()
    )
    return {
        "schema_version": 1,
        "claim_boundary": (
            "This matrix tests deterministic corruption at the generated-assignment and "
            "compiled-objective finalization boundary; it is not exhaustive CP-SAT validation."
        ),
        "toolchain": {
            "ortools": observed_version,
            "workers": 1,
            "seed": _SEED,
            "request_sha256": request_digest(control.spec),
        },
        "implementation_hashes": {
            path: _source_hash(path)
            for path in (
                "pyproject.toml",
                "research/compiler_faults.py",
                "src/constraint_music/solver.py",
            )
        },
        "visited": len(cases),
        "escaped_faults": escaped_faults,
        "cases": cases,
    }
