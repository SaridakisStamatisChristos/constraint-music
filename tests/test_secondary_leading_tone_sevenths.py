from __future__ import annotations

from dataclasses import replace
from functools import cache

import pytest

from constraint_music.contract import HARD_CONSTRAINT_IDS
from constraint_music.modal_mixture import canonical_modal_source
from constraint_music.models import GenerationSpec
from constraint_music.modulation_runtime import ModulatedSatbGenerationResult, result_from_dict
from constraint_music.provenance import artifact_payload, verify_artifact_integrity
from constraint_music.satb import SatbGenerationResult
from constraint_music.secondary_leading_tone import (
    secondary_leading_tone_seventh_name,
    secondary_leading_tone_seventh_pitch_classes,
    secondary_leading_tone_seventh_support_degree,
    supported_secondary_leading_tone_seventh_targets,
)
from constraint_music.solver import ConstraintMusicSolver
from constraint_music.theory import ChordKind, Key, Mode
from constraint_music.verifier import verify_result


@cache
def secondary_seventh_piece() -> SatbGenerationResult:
    spec = GenerationSpec(
        bars=1,
        beats_per_bar=2,
        subdivisions_per_beat=1,
        require_authentic_cadence=False,
        harmony_vocabulary="triads+sevenths",
        secondary_leading_tone_seventh_enabled=True,
        minimum_secondary_leading_tone_seventh_chords=1,
        avoid_parallel_perfects=False,
        workers=1,
        seed=3101,
        max_time_seconds=30,
        tension_curve=(0.8, 0.1),
    )
    result = ConstraintMusicSolver().generate(spec)
    assert isinstance(result, SatbGenerationResult)
    return result


@cache
def mixed_applied_secondary_seventh_piece() -> SatbGenerationResult:
    spec = GenerationSpec(
        bars=1,
        beats_per_bar=5,
        subdivisions_per_beat=1,
        require_authentic_cadence=False,
        harmony_vocabulary="triads+sevenths",
        tonicization_enabled=True,
        minimum_applied_dominants=1,
        secondary_leading_tone_seventh_enabled=True,
        minimum_secondary_leading_tone_seventh_chords=1,
        avoid_parallel_perfects=False,
        workers=1,
        seed=3102,
        max_time_seconds=30,
        tension_curve=(0.8, 0.2, 0.7, 0.3, 0.1),
    )
    result = ConstraintMusicSolver().generate(spec)
    assert isinstance(result, SatbGenerationResult)
    return result


@cache
def modulated_secondary_seventh_piece() -> ModulatedSatbGenerationResult:
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
        harmony_vocabulary="triads+sevenths",
        secondary_leading_tone_seventh_enabled=True,
        minimum_secondary_leading_tone_seventh_chords=1,
        modulation_enabled=True,
        modulation_destination_key="G",
        modulation_boundary_beat=3,
        avoid_parallel_perfects=False,
        workers=1,
        seed=3103,
        max_time_seconds=30,
        tension_curve=(0.05, 0.15, 0.1, 0.8, 0.35, 0.45, 0.9, 0.05),
    )
    result = ConstraintMusicSolver().generate(spec)
    assert isinstance(result, ModulatedSatbGenerationResult)
    return result


def _voice_pitch_classes(result: SatbGenerationResult, beat: int) -> tuple[int, ...]:
    return tuple(
        voice[beat] % 12
        for voice in (result.soprano, result.alto, result.tenor, result.bass)
    )


def _is_exact_applied(result: SatbGenerationResult, beat: int) -> bool:
    target = result.tonicization_targets[beat]
    if target is None or not result.spec.tonicization_enabled:
        return False
    if ChordKind.parse(result.chord_kinds[beat]) is not ChordKind.SEVENTH:
        return False
    key = result.spec.active_key_at_beat(beat)
    if target not in key.applied_dominant_targets:
        return False
    expected = key.applied_dominant_seventh_pitch_classes(target)
    return (
        result.chord_degrees[beat] == key.applied_dominant_root_degree(target)
        and set(_voice_pitch_classes(result, beat)) == set(expected)
        and len(set(_voice_pitch_classes(result, beat))) == 4
        and result.bass[beat] % 12 == expected[result.chord_inversions[beat]]
    )


def _secondary_seventh_beat(result: SatbGenerationResult) -> int:
    for beat, (target, raw_kind) in enumerate(
        zip(result.tonicization_targets, result.chord_kinds, strict=True)
    ):
        if (
            target is not None
            and ChordKind.parse(raw_kind) is ChordKind.SEVENTH
            and not _is_exact_applied(result, beat)
        ):
            return beat
    raise AssertionError("Expected a secondary leading-tone seventh chord")


def test_v211_quality_target_support_and_names_are_deterministic() -> None:
    key = Key("C", Mode.MAJOR)
    graph = GenerationSpec().progression_graph
    assert supported_secondary_leading_tone_seventh_targets(key, graph)
    assert secondary_leading_tone_seventh_pitch_classes(key, 1) == (1, 4, 7, 10)
    assert secondary_leading_tone_seventh_support_degree(key, 1, graph) == 0
    assert secondary_leading_tone_seventh_name(key, 1, 0) == "vii°7/ii"
    assert secondary_leading_tone_seventh_name(key, 1, 1) == "vii°65/ii"
    assert secondary_leading_tone_seventh_name(key, 1, 2) == "vii°43/ii"
    with pytest.raises(ValueError, match=r"inversion must be in 0\.\.2"):
        secondary_leading_tone_seventh_name(key, 1, 3)


def test_secondary_seventh_requires_expanded_harmony_and_own_minimum_flag() -> None:
    with pytest.raises(ValueError, match=r"harmony_vocabulary='triads\+sevenths'"):
        GenerationSpec(secondary_leading_tone_seventh_enabled=True)
    with pytest.raises(ValueError, match="secondary_leading_tone_seventh_enabled=true"):
        GenerationSpec(
            harmony_vocabulary="triads+sevenths",
            minimum_secondary_leading_tone_seventh_chords=1,
        )


def test_solver_emits_complete_verified_fully_diminished_secondary_seventh() -> None:
    result = secondary_seventh_piece()
    assert result.validation.valid, result.validation.issues
    assert result.validation.checked_rules == HARD_CONSTRAINT_IDS
    assert HARD_CONSTRAINT_IDS[-3:] == ("CM055", "CM056", "CM057")

    beat = _secondary_seventh_beat(result)
    target = result.tonicization_targets[beat]
    assert target is not None
    key = result.spec.active_key_at_beat(beat)
    expected = secondary_leading_tone_seventh_pitch_classes(key, target)
    support = secondary_leading_tone_seventh_support_degree(
        key,
        target,
        result.spec.progression_graph,
    )
    assert result.chord_degrees[beat] == support
    assert set(_voice_pitch_classes(result, beat)) == set(expected)
    assert len(set(_voice_pitch_classes(result, beat))) == 4
    assert result.chord_inversions[beat] in {0, 1, 2}
    assert result.bass[beat] % 12 == expected[result.chord_inversions[beat]]
    assert result.modal_sources[beat] is None


def test_secondary_seventh_tendency_tones_and_target_resolve_independently() -> None:
    result = secondary_seventh_piece()
    beat = _secondary_seventh_beat(result)
    target = result.tonicization_targets[beat]
    assert target is not None
    root, _third, diminished_fifth, diminished_seventh = (
        secondary_leading_tone_seventh_pitch_classes(
            result.spec.active_key_at_beat(beat),
            target,
        )
    )
    assert result.chord_degrees[beat + 1] == target
    assert result.tonicization_targets[beat + 1] is None
    assert result.chord_kinds[beat + 1] is ChordKind.TRIAD
    assert result.modal_sources[beat + 1] is None
    for voice in (result.soprano, result.alto, result.tenor, result.bass):
        if voice[beat] % 12 == root:
            assert voice[beat + 1] == voice[beat] + 1
        if voice[beat] % 12 in {diminished_fifth, diminished_seventh}:
            assert voice[beat + 1] - voice[beat] in {-1, -2}


def test_verifier_rejects_half_diminished_counterfeit() -> None:
    result = secondary_seventh_piece()
    beat = _secondary_seventh_beat(result)
    target = result.tonicization_targets[beat]
    assert target is not None
    diminished_seventh = secondary_leading_tone_seventh_pitch_classes(
        result.spec.active_key_at_beat(beat),
        target,
    )[3]
    for label in ("soprano", "alto", "tenor", "bass"):
        voice = getattr(result, label)
        if voice[beat] % 12 != diminished_seventh:
            continue
        forged = list(voice)
        forged[beat] += 1
        report = verify_result(replace(result, **{label: tuple(forged)}))
        assert not report.valid
        assert "CM056" in report.failed_rules
        break
    else:
        pytest.fail("Complete fully diminished seventh must carry its diminished seventh")


def test_verifier_rejects_missing_or_duplicated_secondary_seventh_tone() -> None:
    result = secondary_seventh_piece()
    beat = _secondary_seventh_beat(result)
    voices = [list(result.soprano), list(result.alto), list(result.tenor), list(result.bass)]
    source_pc = voices[0][beat] % 12
    current = voices[1][beat]
    voices[1][beat] = current + ((source_pc - current) % 12)
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
    assert "CM056" in report.failed_rules


def test_verifier_rejects_third_inversion_and_other_inversion_mismatch() -> None:
    result = secondary_seventh_piece()
    beat = _secondary_seventh_beat(result)
    inversions = list(result.chord_inversions)
    inversions[beat] = 3
    report = verify_result(replace(result, chord_inversions=tuple(inversions)))
    assert not report.valid
    assert "CM056" in report.failed_rules

    inversions[beat] = (result.chord_inversions[beat] + 1) % 3
    report = verify_result(replace(result, chord_inversions=tuple(inversions)))
    assert not report.valid
    assert "CM056" in report.failed_rules


def test_verifier_rejects_wrong_support_target_and_modal_overlap() -> None:
    result = secondary_seventh_piece()
    beat = _secondary_seventh_beat(result)

    chords = list(result.chord_degrees)
    chords[beat] = (chords[beat] + 1) % 7
    report = verify_result(replace(result, chord_degrees=tuple(chords)))
    assert not report.valid
    assert "CM055" in report.failed_rules

    targets = list(result.tonicization_targets)
    targets[beat] = 0
    report = verify_result(replace(result, tonicization_targets=tuple(targets)))
    assert not report.valid
    assert "CM055" in report.failed_rules

    sources = list(result.modal_sources)
    sources[beat] = canonical_modal_source(result.spec.active_key_at_beat(beat))
    report = verify_result(replace(result, modal_sources=tuple(sources)))
    assert not report.valid
    assert "CM055" in report.failed_rules


def test_verifier_rejects_wrong_leading_tone_resolution() -> None:
    result = secondary_seventh_piece()
    beat = _secondary_seventh_beat(result)
    target = result.tonicization_targets[beat]
    assert target is not None
    root = secondary_leading_tone_seventh_pitch_classes(
        result.spec.active_key_at_beat(beat),
        target,
    )[0]
    for label in ("soprano", "alto", "tenor", "bass"):
        voice = getattr(result, label)
        if voice[beat] % 12 != root:
            continue
        forged = list(voice)
        forged[beat + 1] = forged[beat] + 2
        report = verify_result(replace(result, **{label: tuple(forged)}))
        assert not report.valid
        assert "CM057" in report.failed_rules
        break
    else:
        pytest.fail("Secondary leading-tone seventh must carry its root")


@pytest.mark.parametrize("tone_index", [2, 3])
def test_verifier_rejects_wrong_downward_unstable_tone_resolution(tone_index: int) -> None:
    result = secondary_seventh_piece()
    beat = _secondary_seventh_beat(result)
    target = result.tonicization_targets[beat]
    assert target is not None
    unstable = secondary_leading_tone_seventh_pitch_classes(
        result.spec.active_key_at_beat(beat),
        target,
    )[tone_index]
    for label in ("soprano", "alto", "tenor", "bass"):
        voice = getattr(result, label)
        if voice[beat] % 12 != unstable:
            continue
        forged = list(voice)
        forged[beat + 1] = forged[beat] + 1
        report = verify_result(replace(result, **{label: tuple(forged)}))
        assert not report.valid
        assert "CM057" in report.failed_rules
        break
    else:
        pytest.fail("Complete secondary seventh must carry every unstable tone")


def test_secondary_seventh_cannot_counterfeit_applied_dominant_minimum() -> None:
    result = secondary_seventh_piece()
    forged_spec = replace(
        result.spec,
        tonicization_enabled=True,
        minimum_applied_dominants=1,
    )
    report = verify_result(replace(result, spec=forged_spec))
    assert not report.valid
    assert "CM037" in report.failed_rules


def test_applied_and_secondary_seventh_minima_remain_distinct_in_solver() -> None:
    result = mixed_applied_secondary_seventh_piece()
    assert result.validation.valid, result.validation.issues
    applied = sum(_is_exact_applied(result, beat) for beat in range(result.spec.total_beats))
    secondary = sum(
        target is not None
        and ChordKind.parse(kind) is ChordKind.SEVENTH
        and not _is_exact_applied(result, beat)
        for beat, (target, kind) in enumerate(
            zip(result.tonicization_targets, result.chord_kinds, strict=True)
        )
    )
    assert applied >= 1
    assert secondary >= 1


def test_secondary_seventh_target_identity_is_committed_by_provenance() -> None:
    result = secondary_seventh_piece()
    beat = _secondary_seventh_beat(result)
    payload = artifact_payload(result)
    target = payload["music"]["tonicization_targets"][beat]
    assert target is not None
    payload["music"]["tonicization_targets"][beat] = (int(target) + 1) % 7
    tampered = result_from_dict(payload)
    issues = verify_artifact_integrity(tampered, payload)
    assert "composition digest mismatch" in issues
    assert "artifact content digest mismatch" in issues


def test_secondary_seventh_is_rejected_on_legacy_cadence_anchor() -> None:
    result = secondary_seventh_piece()
    forged_spec = replace(
        result.spec,
        minimum_secondary_leading_tone_seventh_chords=0,
        require_authentic_cadence=True,
    )
    report = verify_result(replace(result, spec=forged_spec))
    assert not report.valid
    assert "CM055" in report.failed_rules


def test_post_modulation_secondary_seventh_uses_destination_active_key() -> None:
    result = modulated_secondary_seventh_piece()
    beat = _secondary_seventh_beat(result)
    boundary = result.spec.modulation_boundary_beat
    assert boundary is not None
    assert beat >= boundary
    target = result.tonicization_targets[beat]
    assert target is not None
    destination = result.spec.modulation_destination
    assert destination is not None
    expected = secondary_leading_tone_seventh_pitch_classes(destination, target)
    assert set(_voice_pitch_classes(result, beat)) == set(expected)
    assert verify_result(result).valid


def test_post_modulation_stale_global_secondary_seventh_interpretation_fails_closed() -> None:
    result = modulated_secondary_seventh_piece()
    beat = _secondary_seventh_beat(result)
    target = result.tonicization_targets[beat]
    assert target is not None
    stale = secondary_leading_tone_seventh_pitch_classes(result.spec.tonal_key, target)
    voices = [list(result.soprano), list(result.alto), list(result.tenor), list(result.bass)]
    for voice, pc in zip(voices, stale, strict=True):
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
    assert "CM056" in report.failed_rules or "CM046" in report.failed_rules
