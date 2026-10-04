from __future__ import annotations

from dataclasses import replace
from functools import cache

import pytest

from constraint_music.contract import HARD_CONSTRAINT_IDS
from constraint_music.modal_mixture import (
    ModalSource,
    borrowed_seventh_chord_name,
    borrowed_seventh_pitch_classes,
    canonical_modal_source,
    modal_source_leading_tone_pc,
    supported_borrowed_seventh_degrees,
)
from constraint_music.models import GenerationSpec
from constraint_music.modulation_runtime import ModulatedSatbGenerationResult, result_from_dict
from constraint_music.provenance import artifact_payload, verify_artifact_integrity
from constraint_music.satb import SatbGenerationResult
from constraint_music.search import DISTINCT_DIMENSIONS
from constraint_music.solver import ConstraintMusicSolver
from constraint_music.theory import ChordKind, Key, Mode
from constraint_music.verifier import verify_result


@cache
def borrowed_seventh_piece() -> SatbGenerationResult:
    spec = GenerationSpec(
        bars=1,
        beats_per_bar=2,
        subdivisions_per_beat=1,
        require_authentic_cadence=False,
        harmony_vocabulary="triads+sevenths",
        minimum_seventh_chords=1,
        modal_mixture_enabled=True,
        minimum_borrowed_chords=1,
        avoid_parallel_perfects=False,
        workers=1,
        seed=2901,
        max_time_seconds=30,
        tension_curve=(0.55, 0.05),
    )
    result = ConstraintMusicSolver().generate(spec)
    assert isinstance(result, SatbGenerationResult)
    return result


@cache
def minor_source_leading_piece() -> SatbGenerationResult:
    graph = (
        (0,),
        (3,),
        (0,),
        (3,),
        (4,),
        (5,),
        (6,),
    )
    spec = GenerationSpec(
        key="C",
        mode=Mode.MINOR,
        bars=1,
        beats_per_bar=2,
        subdivisions_per_beat=1,
        require_authentic_cadence=False,
        progression_graph=graph,
        harmony_vocabulary="triads+sevenths",
        minimum_seventh_chords=1,
        modal_mixture_enabled=True,
        minimum_borrowed_chords=1,
        avoid_parallel_perfects=False,
        workers=1,
        seed=2902,
        max_time_seconds=30,
        tension_curve=(0.7, 0.05),
    )
    result = ConstraintMusicSolver().generate(spec)
    assert isinstance(result, SatbGenerationResult)
    return result


@cache
def modulated_borrowed_sevenths() -> ModulatedSatbGenerationResult:
    spec = GenerationSpec(
        bars=1,
        beats_per_bar=6,
        subdivisions_per_beat=1,
        require_authentic_cadence=False,
        harmony_vocabulary="triads+sevenths",
        minimum_seventh_chords=3,
        modal_mixture_enabled=True,
        minimum_borrowed_chords=2,
        modulation_enabled=True,
        modulation_destination_key="G",
        modulation_boundary_beat=2,
        avoid_parallel_perfects=False,
        workers=1,
        seed=2903,
        max_time_seconds=30,
        tension_curve=(0.05, 0.15, 0.45, 0.65, 0.9, 0.05),
    )
    result = ConstraintMusicSolver().generate(spec)
    assert isinstance(result, ModulatedSatbGenerationResult)
    return result


def _borrowed_seventh_beat(result: SatbGenerationResult) -> int:
    pairs = zip(result.modal_sources, result.chord_kinds, strict=True)
    for beat, (source, kind) in enumerate(pairs):
        if source is not None and ChordKind.parse(kind) is ChordKind.SEVENTH:
            return beat
    raise AssertionError("Expected a borrowed seventh chord")


def test_v29_supported_borrowed_seventh_policy_is_narrow_and_source_aware() -> None:
    major = Key("C", Mode.MAJOR)
    minor = Key("C", Mode.MINOR)
    assert supported_borrowed_seventh_degrees(major) == (1, 4)
    assert supported_borrowed_seventh_degrees(minor) == (1, 2)
    assert modal_source_leading_tone_pc(
        major, ModalSource.PARALLEL_NATURAL_MINOR
    ) is None
    assert modal_source_leading_tone_pc(minor, ModalSource.PARALLEL_MAJOR) == 11
    assert borrowed_seventh_chord_name(
        major,
        1,
        ModalSource.PARALLEL_NATURAL_MINOR,
        1,
    ) == "ii°65[parallel_natural_minor]"


def test_solver_emits_complete_verified_borrowed_seventh() -> None:
    result = borrowed_seventh_piece()
    assert result.validation.valid, result.validation.issues
    assert result.validation.checked_rules == HARD_CONSTRAINT_IDS
    assert len(HARD_CONSTRAINT_IDS) == 51

    beat = _borrowed_seventh_beat(result)
    source = result.modal_sources[beat]
    assert source is not None
    assert result.chord_kinds[beat] is ChordKind.SEVENTH
    assert result.tonicization_targets[beat] is None
    expected = borrowed_seventh_pitch_classes(
        result.spec.active_key_at_beat(beat),
        result.chord_degrees[beat],
        source,
    )
    pcs = (
        result.soprano[beat] % 12,
        result.alto[beat] % 12,
        result.tenor[beat] % 12,
        result.bass[beat] % 12,
    )
    assert set(pcs) == set(expected)
    assert len(set(pcs)) == 4
    assert result.bass[beat] % 12 == expected[result.chord_inversions[beat]]


def test_borrowed_chordal_seventh_resolves_down_by_step() -> None:
    result = borrowed_seventh_piece()
    beat = _borrowed_seventh_beat(result)
    source = result.modal_sources[beat]
    assert source is not None
    seventh_pc = borrowed_seventh_pitch_classes(
        result.spec.active_key_at_beat(beat),
        result.chord_degrees[beat],
        source,
    )[3]
    for voice in (result.soprano, result.alto, result.tenor, result.bass):
        if voice[beat] % 12 == seventh_pc:
            assert voice[beat + 1] - voice[beat] in {-1, -2}


def test_verifier_rejects_missing_or_duplicated_borrowed_seventh_tone() -> None:
    result = borrowed_seventh_piece()
    beat = _borrowed_seventh_beat(result)
    forged_alto = list(result.alto)
    forged_alto[beat] = result.tenor[beat]
    report = verify_result(replace(result, alto=tuple(forged_alto)))
    assert not report.valid
    assert "CM050" in report.failed_rules


def test_verifier_rejects_borrowed_seventh_inversion_mismatch() -> None:
    result = borrowed_seventh_piece()
    beat = _borrowed_seventh_beat(result)
    inversions = list(result.chord_inversions)
    inversions[beat] = (inversions[beat] + 1) % 3
    report = verify_result(replace(result, chord_inversions=tuple(inversions)))
    assert not report.valid
    assert "CM050" in report.failed_rules


def test_verifier_rejects_wrong_direction_borrowed_seventh_resolution() -> None:
    result = borrowed_seventh_piece()
    beat = _borrowed_seventh_beat(result)
    source = result.modal_sources[beat]
    assert source is not None
    seventh_pc = borrowed_seventh_pitch_classes(
        result.spec.active_key_at_beat(beat),
        result.chord_degrees[beat],
        source,
    )[3]
    for label in ("soprano", "alto", "tenor", "bass"):
        voice = getattr(result, label)
        if voice[beat] % 12 != seventh_pc:
            continue
        forged = list(voice)
        forged[beat + 1] = forged[beat] + 1
        report = verify_result(replace(result, **{label: tuple(forged)}))
        assert not report.valid
        assert "CM051" in report.failed_rules
        break
    else:
        pytest.fail("Complete borrowed seventh must carry its seventh")


def test_source_leading_tone_is_independently_resolved_in_parallel_major() -> None:
    result = minor_source_leading_piece()
    beat = _borrowed_seventh_beat(result)
    assert result.chord_degrees[beat] == 2
    source = result.modal_sources[beat]
    assert source is ModalSource.PARALLEL_MAJOR
    leading_pc = modal_source_leading_tone_pc(result.spec.tonal_key, source)
    assert leading_pc is not None
    carriers = [
        voice
        for voice in (result.soprano, result.alto, result.tenor, result.bass)
        if voice[beat] % 12 == leading_pc
    ]
    assert carriers
    for voice in carriers:
        assert voice[beat + 1] == voice[beat] + 1


def test_borrowed_seventh_cannot_overlap_tonicization() -> None:
    result = borrowed_seventh_piece()
    beat = _borrowed_seventh_beat(result)
    targets = list(result.tonicization_targets)
    targets[beat] = 1
    report = verify_result(replace(result, tonicization_targets=tuple(targets)))
    assert not report.valid
    assert "CM049" in report.failed_rules or "CM041" in report.failed_rules


def test_borrowed_seventh_serialized_as_ordinary_seventh_fails_closed() -> None:
    result = borrowed_seventh_piece()
    beat = _borrowed_seventh_beat(result)
    sources = list(result.modal_sources)
    sources[beat] = None
    report = verify_result(replace(result, modal_sources=tuple(sources)))
    assert not report.valid
    assert "CM034" in report.failed_rules


def test_ordinary_active_key_seventh_forged_as_borrowed_fails_cm050() -> None:
    result = borrowed_seventh_piece()
    beat = _borrowed_seventh_beat(result)
    key = result.spec.active_key_at_beat(beat)
    degree = result.chord_degrees[beat]
    active = key.seventh_pitch_classes(degree)
    voices = [list(result.soprano), list(result.alto), list(result.tenor), list(result.bass)]
    for voice, pc in zip(voices, active, strict=True):
        current = voice[beat]
        voice[beat] = current + ((pc - current) % 12)
    forged = replace(
        result,
        soprano=tuple(voices[0]),
        alto=tuple(voices[1]),
        tenor=tuple(voices[2]),
        bass=tuple(voices[3]),
    )
    report = verify_result(forged)
    assert not report.valid
    assert "CM050" in report.failed_rules


def test_borrowed_seventh_provenance_commits_source_and_harmonic_form() -> None:
    result = borrowed_seventh_piece()
    beat = _borrowed_seventh_beat(result)
    payload = artifact_payload(result)
    payload["music"]["modal_sources"][beat] = None
    tampered = result_from_dict(payload)
    issues = verify_artifact_integrity(tampered, payload)
    assert "composition digest mismatch" in issues
    assert "artifact content digest mismatch" in issues


def test_search_axes_remain_orthogonal() -> None:
    assert "modal_source" in DISTINCT_DIMENSIONS
    assert "harmonic_form" in DISTINCT_DIMENSIONS
    assert "key_context" in DISTINCT_DIMENSIONS


def test_post_modulation_borrowed_sevenths_use_destination_active_key() -> None:
    result = modulated_borrowed_sevenths()
    borrowed = [
        beat
        for beat, (source, kind) in enumerate(
            zip(result.modal_sources, result.chord_kinds, strict=True)
        )
        if source is not None and ChordKind.parse(kind) is ChordKind.SEVENTH
    ]
    assert borrowed == [2, 3]
    destination = result.spec.modulation_destination
    assert destination is not None
    for beat in borrowed:
        source = result.modal_sources[beat]
        assert source is canonical_modal_source(destination)
        expected = borrowed_seventh_pitch_classes(
            destination,
            result.chord_degrees[beat],
            source,
        )
        pcs = {
            result.soprano[beat] % 12,
            result.alto[beat] % 12,
            result.tenor[beat] % 12,
            result.bass[beat] % 12,
        }
        assert pcs == set(expected)
    assert verify_result(result).valid


def test_post_modulation_stale_global_borrowed_seventh_interpretation_fails_closed() -> None:
    result = modulated_borrowed_sevenths()
    beat = _borrowed_seventh_beat(result)
    assert beat >= result.spec.modulation_boundary_beat
    source = result.modal_sources[beat]
    assert source is not None
    global_expected = borrowed_seventh_pitch_classes(
        result.spec.tonal_key,
        result.chord_degrees[beat],
        source,
    )
    voices = [list(result.soprano), list(result.alto), list(result.tenor), list(result.bass)]
    for voice, pc in zip(voices, global_expected, strict=True):
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
    assert "CM050" in report.failed_rules or "CM046" in report.failed_rules
