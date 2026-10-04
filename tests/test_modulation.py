from __future__ import annotations

from dataclasses import replace
from functools import cache

import pytest

from constraint_music.contract import HARD_CONSTRAINT_IDS
from constraint_music.models import GenerationSpec
from constraint_music.modulation import dominant_key
from constraint_music.modulation_runtime import (
    ModulatedSatbGenerationResult,
    result_from_dict,
)
from constraint_music.provenance import artifact_payload, verify_artifact_integrity
from constraint_music.satb import SatbGenerationResult
from constraint_music.search import DISTINCT_DIMENSIONS
from constraint_music.solver import ConstraintMusicSolver, NoSolutionError
from constraint_music.theory import Key, Mode
from constraint_music.verifier import verify_result


def base_spec(**changes: object) -> GenerationSpec:
    values: dict[str, object] = {
        "bars": 2,
        "beats_per_bar": 4,
        "subdivisions_per_beat": 1,
        "require_authentic_cadence": False,
        "modulation_enabled": True,
        "modulation_destination_key": "G",
        "modulation_boundary_beat": 2,
        "avoid_parallel_perfects": False,
        "workers": 1,
        "seed": 2808,
        "max_time_seconds": 30,
        "tension_curve": (0.05, 0.15, 0.35, 0.55, 0.75, 0.9, 0.6, 0.1),
    }
    values.update(changes)
    return GenerationSpec(**values)


@cache
def modulated_piece() -> ModulatedSatbGenerationResult:
    result = ConstraintMusicSolver().generate(base_spec())
    assert isinstance(result, ModulatedSatbGenerationResult)
    return result


def test_dominant_destination_policy_and_configuration_fail_closed() -> None:
    assert dominant_key(Key("C", Mode.MAJOR)) == Key("G", Mode.MAJOR)
    with pytest.raises(ValueError, match="require_authentic_cadence=false"):
        GenerationSpec(
            modulation_enabled=True,
            modulation_destination_key="G",
            modulation_boundary_beat=2,
        )
    with pytest.raises(ValueError, match="same-mode dominant key G"):
        base_spec(modulation_destination_key="F")
    with pytest.raises(ValueError, match="modulation_boundary_beat"):
        base_spec(modulation_boundary_beat=1)


def test_solver_emits_verified_persistent_destination_context() -> None:
    result = modulated_piece()
    assert result.validation.valid, result.validation.issues
    assert result.validation.checked_rules == HARD_CONSTRAINT_IDS
    assert len(HARD_CONSTRAINT_IDS) == 48
    assert result.key_contexts[:2] == (Key("C", Mode.MAJOR),) * 2
    assert result.key_contexts[2:] == (Key("G", Mode.MAJOR),) * 6
    assert result.chord_degrees[1] == 0
    assert result.chord_degrees[-2:] == (4, 0)
    assert result.soprano[-1] % 12 == Key("G", Mode.MAJOR).tonic_pc
    assert result.bass[-1] % 12 == Key("G", Mode.MAJOR).tonic_pc


def test_shifted_or_forged_key_context_is_rejected() -> None:
    result = modulated_piece()
    contexts = list(result.key_contexts)
    contexts[2] = Key("C", Mode.MAJOR)
    report = verify_result(replace(result, key_contexts=tuple(contexts)))
    assert not report.valid
    assert "CM048" in report.failed_rules


def test_forged_pivot_and_destination_cadence_are_rejected() -> None:
    result = modulated_piece()
    chords = list(result.chord_degrees)
    chords[1] = 3
    report = verify_result(replace(result, chord_degrees=tuple(chords)))
    assert not report.valid
    assert "CM045" in report.failed_rules

    chords = list(result.chord_degrees)
    chords[-2] = 3
    report = verify_result(replace(result, chord_degrees=tuple(chords)))
    assert not report.valid
    assert "CM047" in report.failed_rules


def test_key_context_tampering_breaks_semantic_provenance() -> None:
    result = modulated_piece()
    payload = artifact_payload(result)
    payload["music"]["key_contexts"][2] = {"tonic": "C", "mode": "major"}
    tampered = result_from_dict(payload)
    issues = verify_artifact_integrity(tampered, payload)
    assert "composition digest mismatch" in issues
    assert "artifact content digest mismatch" in issues


def test_old_payload_without_key_context_remains_loadable_when_modulation_is_off() -> None:
    legacy = ConstraintMusicSolver().generate(
        GenerationSpec(
            bars=1,
            beats_per_bar=4,
            subdivisions_per_beat=1,
            workers=1,
            seed=2707,
        )
    )
    assert isinstance(legacy, SatbGenerationResult)
    payload = legacy.to_dict()
    payload["music"].pop("key_contexts", None)
    loaded = result_from_dict(payload)
    assert isinstance(loaded, SatbGenerationResult)
    assert not isinstance(loaded, ModulatedSatbGenerationResult)
    assert verify_result(loaded).valid


def test_key_context_is_separate_search_axis_and_spec_bound() -> None:
    assert "key_context" in DISTINCT_DIMENSIONS
    with pytest.raises(NoSolutionError, match="Only 1 distinct compositions"):
        ConstraintMusicSolver().generate_many(base_spec(seed=2810), 2, ("key_context",))


def test_modulation_followed_by_destination_tonicization() -> None:
    result = ConstraintMusicSolver().generate(
        base_spec(
            harmony_vocabulary="triads+sevenths",
            tonicization_enabled=True,
            minimum_applied_dominants=1,
            seed=2811,
        )
    )
    assert isinstance(result, ModulatedSatbGenerationResult)
    beats = [i for i, target in enumerate(result.tonicization_targets) if target is not None]
    assert beats and all(beat >= 2 for beat in beats)
    assert verify_result(result).valid


def test_modulation_followed_by_destination_modal_mixture() -> None:
    result = ConstraintMusicSolver().generate(
        base_spec(modal_mixture_enabled=True, minimum_borrowed_chords=1, seed=2812)
    )
    assert isinstance(result, ModulatedSatbGenerationResult)
    beats = [i for i, source in enumerate(result.modal_sources) if source is not None]
    assert beats and all(beat >= 2 for beat in beats)
    assert verify_result(result).valid


def test_post_modulation_borrowing_rejects_stale_pre_modulation_context() -> None:
    result = ConstraintMusicSolver().generate(
        base_spec(modal_mixture_enabled=True, minimum_borrowed_chords=1, seed=2813)
    )
    assert isinstance(result, ModulatedSatbGenerationResult)
    beat = next(i for i, source in enumerate(result.modal_sources) if source is not None)
    assert beat >= 2
    contexts = list(result.key_contexts)
    contexts[beat] = Key("C", Mode.MAJOR)
    report = verify_result(replace(result, key_contexts=tuple(contexts)))
    assert not report.valid
    assert "CM048" in report.failed_rules
