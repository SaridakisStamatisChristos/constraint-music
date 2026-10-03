from __future__ import annotations

from dataclasses import replace
from functools import cache

import pytest

from constraint_music.contract import HARD_CONSTRAINT_IDS
from constraint_music.models import GenerationSpec
from constraint_music.provenance import artifact_payload, verify_artifact_integrity
from constraint_music.satb import SatbGenerationResult, result_from_dict
from constraint_music.solver import ConstraintMusicSolver
from constraint_music.theory import ChordKind, Key, Mode
from constraint_music.verifier import verify_result

FORCED_V_OF_V_GRAPH: tuple[tuple[int, ...], ...] = (
    (1,),
    (4,),
    (2,),
    (3,),
    (0,),
    (5,),
    (6,),
)


@cache
def applied_dominant_piece() -> SatbGenerationResult:
    spec = GenerationSpec(
        bars=1,
        beats_per_bar=4,
        subdivisions_per_beat=1,
        progression_graph=FORCED_V_OF_V_GRAPH,
        harmony_vocabulary="triads+sevenths",
        minimum_seventh_chords=1,
        tonicization_enabled=True,
        minimum_applied_dominants=1,
        max_time_seconds=30,
        workers=1,
        seed=2606,
        tension_curve=(0.05, 0.65, 0.9, 0.02),
    )
    result = ConstraintMusicSolver().generate(spec)
    assert isinstance(result, SatbGenerationResult)
    return result


def test_c_major_supported_applied_dominant_targets_are_explicit() -> None:
    key = Key("C", Mode.MAJOR)
    assert key.applied_dominant_targets == (1, 3, 4, 5)
    assert key.applied_dominant_root_degree(4) == 1
    assert key.applied_dominant_seventh_pitch_classes(4) == (2, 6, 9, 0)
    assert key.applied_dominant_name(4, 0) == "V7/V"


def test_tonicization_requires_expanded_seventh_vocabulary() -> None:
    with pytest.raises(ValueError, match="tonicization_enabled requires"):
        GenerationSpec(tonicization_enabled=True)
    with pytest.raises(ValueError, match="minimum_applied_dominants requires"):
        GenerationSpec(minimum_applied_dominants=1)


def test_solver_emits_verified_v7_of_v() -> None:
    result = applied_dominant_piece()
    assert result.validation.valid, result.validation.issues
    assert result.validation.checked_rules == HARD_CONSTRAINT_IDS
    assert result.chord_degrees == (0, 1, 4, 0)
    assert result.tonicization_targets == (None, 4, None, None)
    assert result.chord_kinds[1] is ChordKind.SEVENTH
    assert result.chord_form_names[1] == "V7/V" or result.chord_form_names[1] in {
        "V65/V",
        "V43/V",
    }

    applied = result.spec.tonal_key.applied_dominant_seventh_pitch_classes(4)
    pcs = {
        result.soprano[1] % 12,
        result.alto[1] % 12,
        result.tenor[1] % 12,
        result.bass[1] % 12,
    }
    assert pcs == set(applied)
    assert result.bass[1] % 12 == applied[result.chord_inversions[1]]


def test_verifier_rejects_forged_tonicization_target() -> None:
    result = applied_dominant_piece()
    targets = list(result.tonicization_targets)
    targets[1] = 3
    report = verify_result(replace(result, tonicization_targets=tuple(targets)))
    assert not report.valid
    assert "CM038" in report.failed_rules
    assert "CM039" in report.failed_rules


def test_verifier_rejects_wrong_applied_target_resolution() -> None:
    result = applied_dominant_piece()
    chords = list(result.chord_degrees)
    chords[2] = 3
    report = verify_result(replace(result, chord_degrees=tuple(chords)))
    assert not report.valid
    assert "CM039" in report.failed_rules


def test_verifier_rejects_unresolved_applied_leading_tone() -> None:
    result = applied_dominant_piece()
    leading_pc = result.spec.tonal_key.applied_dominant_seventh_pitch_classes(4)[1]
    for field_name in ("soprano", "alto", "tenor", "bass"):
        voice = list(getattr(result, field_name))
        if voice[1] % 12 != leading_pc:
            continue
        voice[2] = voice[1]
        report = verify_result(replace(result, **{field_name: tuple(voice)}))
        assert not report.valid
        assert "CM040" in report.failed_rules
        return
    raise AssertionError("Generated V7/V has no local leading-tone carrier")


def test_verifier_rejects_unresolved_applied_chordal_seventh() -> None:
    result = applied_dominant_piece()
    seventh_pc = result.spec.tonal_key.applied_dominant_seventh_pitch_classes(4)[3]
    for field_name in ("soprano", "alto", "tenor", "bass"):
        voice = list(getattr(result, field_name))
        if voice[1] % 12 != seventh_pc:
            continue
        voice[2] = voice[1]
        report = verify_result(replace(result, **{field_name: tuple(voice)}))
        assert not report.valid
        assert "CM040" in report.failed_rules
        return
    raise AssertionError("Generated V7/V has no chordal-seventh carrier")


def test_tonicization_tampering_breaks_semantic_provenance() -> None:
    result = applied_dominant_piece()
    payload = artifact_payload(result)
    payload["music"]["tonicization_targets"][1] = 3
    tampered = result_from_dict(payload)
    issues = verify_artifact_integrity(tampered, payload)
    assert "composition digest mismatch" in issues
    assert "artifact content digest mismatch" in issues


def test_absent_tonicization_metadata_remains_loadable_when_feature_is_off() -> None:
    result = applied_dominant_piece()
    legacy_spec = replace(
        result.spec,
        tonicization_enabled=False,
        minimum_applied_dominants=0,
        progression_graph=(
            (0, 4),
            (1,),
            (2,),
            (3,),
            (0,),
            (5,),
            (0,),
        ),
    )
    legacy = ConstraintMusicSolver().generate(legacy_spec)
    assert isinstance(legacy, SatbGenerationResult)
    payload = legacy.to_dict()
    payload["music"].pop("tonicization_targets", None)
    loaded = result_from_dict(payload)
    assert isinstance(loaded, SatbGenerationResult)
    assert loaded.tonicization_targets == ()
    report = verify_result(loaded)
    assert report.valid, report.issues
