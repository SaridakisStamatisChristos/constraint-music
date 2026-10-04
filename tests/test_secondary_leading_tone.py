from __future__ import annotations

from dataclasses import replace
from functools import cache

import pytest

from constraint_music.contract import HARD_CONSTRAINT_IDS
from constraint_music.models import GenerationSpec
from constraint_music.modulation_runtime import ModulatedSatbGenerationResult, result_from_dict
from constraint_music.provenance import artifact_payload, verify_artifact_integrity
from constraint_music.satb import SatbGenerationResult
from constraint_music.secondary_leading_tone import (
    secondary_leading_tone_name,
    secondary_leading_tone_support_degree,
    secondary_leading_tone_triad_pitch_classes,
    supported_secondary_leading_tone_targets,
)
from constraint_music.solver import ConstraintMusicSolver
from constraint_music.theory import ChordKind, Key, Mode
from constraint_music.verifier import verify_result


@cache
def secondary_piece() -> SatbGenerationResult:
    spec = GenerationSpec(
        bars=1,
        beats_per_bar=2,
        subdivisions_per_beat=1,
        require_authentic_cadence=False,
        secondary_leading_tone_enabled=True,
        minimum_secondary_leading_tone_chords=1,
        avoid_parallel_perfects=False,
        workers=1,
        seed=3001,
        max_time_seconds=30,
        tension_curve=(0.75, 0.1),
    )
    result = ConstraintMusicSolver().generate(spec)
    assert isinstance(result, SatbGenerationResult)
    return result


@cache
def modulated_secondary_piece() -> ModulatedSatbGenerationResult:
    # This graph forces 0,1,0,2,3,1,4,0. With boundary=3, the only non-anchor
    # support->target pair eligible for v2.10 is destination-key degree 2 -> 3
    # at beats 3 -> 4. That makes the post-modulation secondary chord deterministic.
    graph = (
        (1, 2),
        (0, 4),
        (3,),
        (1,),
        (0,),
        (5,),
        (6,),
    )
    spec = GenerationSpec(
        bars=1,
        beats_per_bar=8,
        subdivisions_per_beat=1,
        require_authentic_cadence=False,
        progression_graph=graph,
        secondary_leading_tone_enabled=True,
        minimum_secondary_leading_tone_chords=1,
        modulation_enabled=True,
        modulation_destination_key="G",
        modulation_boundary_beat=3,
        avoid_parallel_perfects=False,
        workers=1,
        seed=3002,
        max_time_seconds=30,
        tension_curve=(0.05, 0.15, 0.1, 0.7, 0.35, 0.45, 0.9, 0.05),
    )
    result = ConstraintMusicSolver().generate(spec)
    assert isinstance(result, ModulatedSatbGenerationResult)
    return result


def _secondary_beat(result: SatbGenerationResult) -> int:
    for beat, (target, raw_kind) in enumerate(
        zip(result.tonicization_targets, result.chord_kinds, strict=True)
    ):
        if target is not None and ChordKind.parse(raw_kind) is ChordKind.TRIAD:
            return beat
    raise AssertionError("Expected a secondary leading-tone chord")


def test_v210_target_policy_and_support_degree_are_deterministic() -> None:
    key = Key("C", Mode.MAJOR)
    graph = GenerationSpec().progression_graph
    assert supported_secondary_leading_tone_targets(key, graph) == (1, 3, 4, 5)
    assert secondary_leading_tone_support_degree(key, 1, graph) == 0
    assert secondary_leading_tone_triad_pitch_classes(key, 1) == (1, 4, 7)
    assert secondary_leading_tone_name(key, 1, 1) == "vii°6/ii"
    with pytest.raises(ValueError, match=r"target degree must be in 1\.\.6"):
        secondary_leading_tone_triad_pitch_classes(key, 0)


def test_minimum_secondary_count_requires_feature_flag() -> None:
    with pytest.raises(ValueError, match="secondary_leading_tone_enabled=true"):
        GenerationSpec(minimum_secondary_leading_tone_chords=1)


def test_solver_emits_complete_verified_secondary_leading_tone_chord() -> None:
    result = secondary_piece()
    assert result.validation.valid, result.validation.issues
    assert result.validation.checked_rules == HARD_CONSTRAINT_IDS
    assert len(HARD_CONSTRAINT_IDS) == 54

    beat = _secondary_beat(result)
    target = result.tonicization_targets[beat]
    assert target is not None
    key = result.spec.active_key_at_beat(beat)
    expected = secondary_leading_tone_triad_pitch_classes(key, target)
    support = secondary_leading_tone_support_degree(
        key, target, result.spec.progression_graph
    )
    assert result.chord_degrees[beat] == support
    assert result.chord_kinds[beat] is ChordKind.TRIAD
    assert result.modal_sources[beat] is None

    pcs = (
        result.soprano[beat] % 12,
        result.alto[beat] % 12,
        result.tenor[beat] % 12,
        result.bass[beat] % 12,
    )
    root, third, diminished_fifth = expected
    assert set(pcs) == set(expected)
    assert pcs.count(root) == 1
    assert pcs.count(third) == 2
    assert pcs.count(diminished_fifth) == 1
    assert result.bass[beat] % 12 == expected[result.chord_inversions[beat]]


def test_secondary_tendency_tones_resolve_independently() -> None:
    result = secondary_piece()
    beat = _secondary_beat(result)
    target = result.tonicization_targets[beat]
    assert target is not None
    root, _, diminished_fifth = secondary_leading_tone_triad_pitch_classes(
        result.spec.active_key_at_beat(beat), target
    )
    for voice in (result.soprano, result.alto, result.tenor, result.bass):
        if voice[beat] % 12 == root:
            assert voice[beat + 1] == voice[beat] + 1
        if voice[beat] % 12 == diminished_fifth:
            assert voice[beat + 1] - voice[beat] in {-1, -2}


def test_secondary_resolves_immediately_to_declared_unaltered_target() -> None:
    result = secondary_piece()
    beat = _secondary_beat(result)
    target = result.tonicization_targets[beat]
    assert target is not None
    assert result.chord_degrees[beat + 1] == target
    assert result.tonicization_targets[beat + 1] is None
    assert result.chord_kinds[beat + 1] is ChordKind.TRIAD
    assert result.modal_sources[beat + 1] is None


def test_verifier_rejects_wrong_secondary_support_degree() -> None:
    result = secondary_piece()
    beat = _secondary_beat(result)
    chords = list(result.chord_degrees)
    chords[beat] = (chords[beat] + 1) % 7
    report = verify_result(replace(result, chord_degrees=tuple(chords)))
    assert not report.valid
    assert "CM052" in report.failed_rules


def test_verifier_rejects_secondary_inversion_mismatch() -> None:
    result = secondary_piece()
    beat = _secondary_beat(result)
    inversions = list(result.chord_inversions)
    inversions[beat] = (inversions[beat] + 1) % 3
    report = verify_result(replace(result, chord_inversions=tuple(inversions)))
    assert not report.valid
    assert "CM053" in report.failed_rules


def test_verifier_rejects_doubled_secondary_tendency_tone() -> None:
    result = secondary_piece()
    beat = _secondary_beat(result)
    target = result.tonicization_targets[beat]
    assert target is not None
    expected = secondary_leading_tone_triad_pitch_classes(
        result.spec.active_key_at_beat(beat), target
    )
    root = expected[0]
    voices = [list(result.soprano), list(result.alto), list(result.tenor), list(result.bass)]
    carrier = next(index for index, voice in enumerate(voices) if voice[beat] % 12 == root)
    other = next(index for index in range(4) if index != carrier)
    current = voices[other][beat]
    voices[other][beat] = current + ((root - current) % 12)
    report = verify_result(
        replace(
            result,
            soprano=tuple(voices[0]),
            alto=tuple(voices[1]),
            tenor=tuple(voices[2]),
            bass=tuple(voices[3]),
        )
    )
    assert not report.valid
    assert "CM053" in report.failed_rules


def test_verifier_rejects_wrong_direction_local_leading_tone_resolution() -> None:
    result = secondary_piece()
    beat = _secondary_beat(result)
    target = result.tonicization_targets[beat]
    assert target is not None
    root = secondary_leading_tone_triad_pitch_classes(
        result.spec.active_key_at_beat(beat), target
    )[0]
    for label in ("soprano", "alto", "tenor", "bass"):
        voice = getattr(result, label)
        if voice[beat] % 12 != root:
            continue
        forged = list(voice)
        forged[beat + 1] = forged[beat] + 2
        report = verify_result(replace(result, **{label: tuple(forged)}))
        assert not report.valid
        assert "CM054" in report.failed_rules
        break
    else:
        pytest.fail("Complete secondary leading-tone triad must carry its root")


def test_verifier_rejects_wrong_direction_diminished_fifth_resolution() -> None:
    result = secondary_piece()
    beat = _secondary_beat(result)
    target = result.tonicization_targets[beat]
    assert target is not None
    diminished_fifth = secondary_leading_tone_triad_pitch_classes(
        result.spec.active_key_at_beat(beat), target
    )[2]
    for label in ("soprano", "alto", "tenor", "bass"):
        voice = getattr(result, label)
        if voice[beat] % 12 != diminished_fifth:
            continue
        forged = list(voice)
        forged[beat + 1] = forged[beat] + 1
        report = verify_result(replace(result, **{label: tuple(forged)}))
        assert not report.valid
        assert "CM054" in report.failed_rules
        break
    else:
        pytest.fail("Complete secondary leading-tone triad must carry its diminished fifth")


def test_secondary_target_cannot_counterfeit_minimum_applied_dominants() -> None:
    result = secondary_piece()
    forged_spec = replace(
        result.spec,
        harmony_vocabulary="triads+sevenths",
        tonicization_enabled=True,
        minimum_applied_dominants=1,
    )
    report = verify_result(replace(result, spec=forged_spec))
    assert not report.valid
    assert "CM037" in report.failed_rules


def test_secondary_target_identity_is_committed_by_provenance() -> None:
    result = secondary_piece()
    beat = _secondary_beat(result)
    payload = artifact_payload(result)
    target = payload["music"]["tonicization_targets"][beat]
    assert target is not None
    payload["music"]["tonicization_targets"][beat] = (int(target) + 1) % 7
    tampered = result_from_dict(payload)
    issues = verify_artifact_integrity(tampered, payload)
    assert "composition digest mismatch" in issues
    assert "artifact content digest mismatch" in issues


def test_post_modulation_secondary_uses_destination_active_key() -> None:
    result = modulated_secondary_piece()
    assert result.chord_degrees == (0, 1, 0, 2, 3, 1, 4, 0)
    beat = _secondary_beat(result)
    assert beat == 3
    destination = result.spec.modulation_destination
    assert destination is not None
    target = result.tonicization_targets[beat]
    assert target == 3
    expected = secondary_leading_tone_triad_pitch_classes(destination, target)
    pcs = {
        result.soprano[beat] % 12,
        result.alto[beat] % 12,
        result.tenor[beat] % 12,
        result.bass[beat] % 12,
    }
    assert pcs == set(expected)
    assert verify_result(result).valid


def test_post_modulation_stale_global_secondary_interpretation_fails_closed() -> None:
    result = modulated_secondary_piece()
    beat = _secondary_beat(result)
    target = result.tonicization_targets[beat]
    assert target is not None
    stale = secondary_leading_tone_triad_pitch_classes(result.spec.tonal_key, target)
    voices = [list(result.soprano), list(result.alto), list(result.tenor), list(result.bass)]
    for voice, pc in zip(voices, (*stale, stale[1]), strict=True):
        current = voice[beat]
        voice[beat] = current + ((pc - current) % 12)
    report = verify_result(
        replace(
            result,
            soprano=tuple(voices[0]),
            alto=tuple(voices[1]),
            tenor=tuple(voices[2]),
            bass=tuple(voices[3]),
        )
    )
    assert not report.valid
    assert "CM053" in report.failed_rules or "CM046" in report.failed_rules
