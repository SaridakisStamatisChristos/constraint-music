from __future__ import annotations

from dataclasses import replace
from functools import cache

import pytest

from constraint_music.contract import HARD_CONSTRAINT_IDS
from constraint_music.modal_mixture import (
    ModalSource,
    borrowed_chord_name,
    borrowed_triad_pitch_classes,
    canonical_modal_source,
    supported_borrowed_degrees,
)
from constraint_music.models import GenerationSpec
from constraint_music.provenance import artifact_payload, verify_artifact_integrity
from constraint_music.satb import SatbGenerationResult, result_from_dict
from constraint_music.solver import ConstraintMusicSolver
from constraint_music.theory import ChordKind, Key, Mode
from constraint_music.verifier import verify_result

MIXTURE_CADENCE_GRAPH: tuple[tuple[int, ...], ...] = (
    (3,),
    (1,),
    (2,),
    (4,),
    (0,),
    (5,),
    (6,),
)


@cache
def borrowed_piece() -> SatbGenerationResult:
    spec = GenerationSpec(
        bars=1,
        beats_per_bar=4,
        subdivisions_per_beat=1,
        progression_graph=MIXTURE_CADENCE_GRAPH,
        modal_mixture_enabled=True,
        minimum_borrowed_chords=1,
        max_time_seconds=30,
        workers=1,
        seed=2707,
        tension_curve=(0.05, 0.35, 0.82, 0.02),
    )
    result = ConstraintMusicSolver().generate(spec)
    assert isinstance(result, SatbGenerationResult)
    return result


def _borrowed_beat(result: SatbGenerationResult) -> int:
    for beat, source in enumerate(result.modal_sources):
        if source is not None:
            return beat
    raise AssertionError("Expected at least one borrowed chord")


def test_parallel_source_model_is_explicit_and_mode_specific() -> None:
    major = Key("C", Mode.MAJOR)
    minor = Key("C", Mode.MINOR)
    assert canonical_modal_source(major) is ModalSource.PARALLEL_NATURAL_MINOR
    assert canonical_modal_source(minor) is ModalSource.PARALLEL_MAJOR
    assert supported_borrowed_degrees(major) == (0, 1, 2, 3, 4, 5, 6)
    assert supported_borrowed_degrees(minor) == (0, 1, 2, 3, 5)
    assert borrowed_triad_pitch_classes(major, 3, ModalSource.PARALLEL_NATURAL_MINOR) == (
        5,
        8,
        0,
    )
    assert borrowed_chord_name(
        major,
        3,
        ModalSource.PARALLEL_NATURAL_MINOR,
        1,
    ) == "iv6[parallel_natural_minor]"


def test_modal_mixture_configuration_is_fail_closed() -> None:
    with pytest.raises(ValueError, match="minimum_borrowed_chords requires"):
        GenerationSpec(minimum_borrowed_chords=1)
    with pytest.raises(ValueError, match="preserved global cadential boundary"):
        GenerationSpec(
            bars=1,
            beats_per_bar=4,
            subdivisions_per_beat=1,
            modal_mixture_enabled=True,
            minimum_borrowed_chords=3,
        )


def test_solver_emits_verified_borrowed_triad_without_redefining_cadence() -> None:
    result = borrowed_piece()
    assert result.validation.valid, result.validation.issues
    assert result.validation.checked_rules == HARD_CONSTRAINT_IDS
    assert result.chord_degrees == (0, 3, 4, 0)
    assert result.modal_sources[-2:] == (None, None)

    beat = _borrowed_beat(result)
    source = result.modal_sources[beat]
    assert source is ModalSource.PARALLEL_NATURAL_MINOR
    assert result.tonicization_targets[beat] is None
    assert result.chord_kinds[beat] is ChordKind.TRIAD

    expected = borrowed_triad_pitch_classes(result.spec.tonal_key, result.chord_degrees[beat], source)
    pcs = (
        result.soprano[beat] % 12,
        result.alto[beat] % 12,
        result.tenor[beat] % 12,
        result.bass[beat] % 12,
    )
    assert set(pcs) == set(expected)
    assert len(set(pcs)) == 3
    assert result.bass[beat] % 12 == expected[result.chord_inversions[beat]]
    assert "parallel_natural_minor" in result.chord_form_names[beat]


def test_verifier_rejects_noncanonical_parallel_source() -> None:
    result = borrowed_piece()
    beat = _borrowed_beat(result)
    sources = list(result.modal_sources)
    sources[beat] = ModalSource.PARALLEL_MAJOR
    report = verify_result(replace(result, modal_sources=tuple(sources)))
    assert not report.valid
    assert "CM041" in report.failed_rules


def test_verifier_rejects_borrowed_inversion_mismatch() -> None:
    result = borrowed_piece()
    beat = _borrowed_beat(result)
    inversions = list(result.chord_inversions)
    inversions[beat] = (inversions[beat] + 1) % 3
    report = verify_result(replace(result, chord_inversions=tuple(inversions)))
    assert not report.valid
    assert "CM042" in report.failed_rules


def test_verifier_rejects_forged_borrowed_degree_identity() -> None:
    result = borrowed_piece()
    beat = _borrowed_beat(result)
    chords = list(result.chord_degrees)
    chords[beat] = (chords[beat] + 1) % 7
    report = verify_result(replace(result, chord_degrees=tuple(chords)))
    assert not report.valid
    assert "CM042" in report.failed_rules


def test_modal_source_tampering_breaks_semantic_provenance() -> None:
    result = borrowed_piece()
    beat = _borrowed_beat(result)
    payload = artifact_payload(result)
    payload["music"]["modal_sources"][beat] = None
    tampered = result_from_dict(payload)
    issues = verify_artifact_integrity(tampered, payload)
    assert "composition digest mismatch" in issues
    assert "artifact content digest mismatch" in issues


def test_absent_modal_source_metadata_remains_loadable_when_feature_is_off() -> None:
    legacy_spec = GenerationSpec(
        bars=1,
        beats_per_bar=4,
        subdivisions_per_beat=1,
        progression_graph=MIXTURE_CADENCE_GRAPH,
        max_time_seconds=30,
        workers=1,
        seed=2706,
    )
    legacy = ConstraintMusicSolver().generate(legacy_spec)
    assert isinstance(legacy, SatbGenerationResult)
    payload = legacy.to_dict()
    payload["music"].pop("modal_sources", None)
    loaded = result_from_dict(payload)
    assert isinstance(loaded, SatbGenerationResult)
    assert loaded.modal_sources == ()
    report = verify_result(loaded)
    assert report.valid, report.issues


def test_modal_source_distinctness_changes_only_the_new_context_axis() -> None:
    spec = GenerationSpec(
        bars=1,
        beats_per_bar=4,
        subdivisions_per_beat=1,
        progression_graph=MIXTURE_CADENCE_GRAPH,
        modal_mixture_enabled=True,
        max_time_seconds=30,
        workers=1,
        seed=2708,
        tension_curve=(0.05, 0.35, 0.82, 0.02),
    )
    results = ConstraintMusicSolver().generate_many(spec, 2, ("modal_source",))
    assert all(isinstance(result, SatbGenerationResult) for result in results)
    typed = tuple(result for result in results if isinstance(result, SatbGenerationResult))
    assert len(typed) == 2
    assert typed[0].modal_sources != typed[1].modal_sources
    assert typed[0].chord_degrees == typed[1].chord_degrees == (0, 3, 4, 0)
