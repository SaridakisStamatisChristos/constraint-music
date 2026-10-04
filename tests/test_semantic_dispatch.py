from __future__ import annotations

from dataclasses import replace
from functools import cache

import pytest

import constraint_music.borrowed_seventh_runtime as borrowed_runtime
import constraint_music.secondary_leading_tone_runtime as secondary_runtime
import constraint_music.secondary_leading_tone_seventh_runtime as secondary_seventh_runtime
from constraint_music.modal_mixture import ModalSource
from constraint_music.models import GenerationSpec, RhythmState
from constraint_music.satb import SatbGenerationResult
from constraint_music.secondary_leading_tone import (
    SecondaryLeadingToneSeventhQuality,
    secondary_leading_tone_seventh_support_degree,
)
from constraint_music.solver import ConstraintMusicSolver
from constraint_music.theory import ChordKind
from constraint_music.verifier import verify_result


@cache
def _secondary_triad_piece() -> SatbGenerationResult:
    result = ConstraintMusicSolver().generate(
        GenerationSpec(
            bars=1,
            beats_per_bar=2,
            subdivisions_per_beat=1,
            require_authentic_cadence=False,
            secondary_leading_tone_enabled=True,
            minimum_secondary_leading_tone_chords=1,
            avoid_parallel_perfects=False,
            workers=1,
            seed=6101,
            max_time_seconds=30,
            tension_curve=(0.75, 0.1),
        )
    )
    assert isinstance(result, SatbGenerationResult)
    return result


@cache
def _borrowed_seventh_piece() -> SatbGenerationResult:
    result = ConstraintMusicSolver().generate(
        GenerationSpec(
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
            seed=6102,
            max_time_seconds=30,
            tension_curve=(0.55, 0.05),
        )
    )
    assert isinstance(result, SatbGenerationResult)
    return result


def _third_inversion_secondary_seventh() -> SatbGenerationResult:
    spec = GenerationSpec(
        bars=1,
        beats_per_bar=2,
        subdivisions_per_beat=1,
        require_authentic_cadence=False,
        harmony_vocabulary="triads+sevenths",
        secondary_leading_tone_seventh_enabled=True,
        minimum_secondary_leading_tone_seventh_chords=1,
        avoid_parallel_perfects=False,
        resolve_leading_tone=False,
        bass_high=59,
        tension_curve=(0.8, 0.1),
    )
    target = 4
    support = secondary_leading_tone_seventh_support_degree(
        spec.tonal_key,
        target,
        spec.progression_graph,
        SecondaryLeadingToneSeventhQuality.FULLY_DIMINISHED,
    )
    soprano = (69, 67)
    alto = (60, 59)
    tenor = (54, 55)
    bass = (51, 50)
    return SatbGenerationResult(
        spec=spec,
        melody=soprano,
        bass=bass,
        chord_degrees=(support, target),
        target_tension=(80, 10),
        actual_tension=(80, 10),
        objective_value=0.0,
        solver_status="SYNTHETIC",
        wall_time_seconds=0.0,
        rhythm=(RhythmState.ONSET, RhythmState.ONSET),
        soprano=soprano,
        alto=alto,
        tenor=tenor,
        chord_kinds=(ChordKind.SEVENTH, ChordKind.TRIAD),
        chord_inversions=(3, 2),
        tonicization_targets=(target, None),
        modal_sources=(None, None),
    )


@pytest.mark.parametrize(
    "message",
    [
        "Beat 0: borrowed harmony must be triadic",
        "wording changed completely",
    ],
)
def test_borrowed_dispatch_never_filters_by_diagnostic_text(
    monkeypatch: pytest.MonkeyPatch,
    message: str,
) -> None:
    result = _borrowed_seventh_piece()
    sentinel = ("CM041", message)
    monkeypatch.setattr(
        borrowed_runtime,
        "satb_verification_issues",
        lambda _result, *, semantic_dispatch=None: (sentinel,),
    )

    issues = borrowed_runtime.borrowed_seventh_satb_verification_issues(result)

    assert sentinel in issues


def test_secondary_dispatch_never_filters_by_diagnostic_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _secondary_triad_piece()
    sentinels = (
        ("CM037", "Beat 0: old applied-dominant wording"),
        ("CM038", "cosmetic replacement"),
    )
    monkeypatch.setattr(
        secondary_runtime,
        "borrowed_seventh_satb_verification_issues",
        lambda _result, *, semantic_dispatch=None: sentinels,
    )

    issues = secondary_runtime.secondary_leading_tone_satb_verification_issues(result)

    assert all(sentinel in issues for sentinel in sentinels)


def test_secondary_seventh_dispatch_never_filters_by_diagnostic_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _third_inversion_secondary_seventh()
    sentinels = (
        ("CM033", "Chord inversions must be encoded in 0..2"),
        ("CM040", "soprano beat 0: old tendency wording"),
    )
    monkeypatch.setattr(
        secondary_seventh_runtime,
        "secondary_leading_tone_satb_verification_issues",
        lambda _result, *, semantic_dispatch=None: sentinels,
    )

    issues = secondary_seventh_runtime.secondary_leading_tone_seventh_satb_verification_issues(
        result
    )

    assert all(sentinel in issues for sentinel in sentinels)


def test_false_secondary_target_and_kind_do_not_disable_generic_obligations() -> None:
    result = _secondary_triad_piece()
    beat = next(
        index for index, target in enumerate(result.tonicization_targets) if target is not None
    )

    targets = list(result.tonicization_targets)
    targets[beat] = 0
    wrong_target = verify_result(replace(result, tonicization_targets=tuple(targets)))
    assert "CM037" in wrong_target.failed_rules

    kinds = list(result.chord_kinds)
    kinds[beat] = ChordKind.SEVENTH
    wrong_kind = verify_result(replace(result, chord_kinds=tuple(kinds)))
    assert "CM038" in wrong_kind.failed_rules


def test_false_borrowed_source_does_not_disable_source_obligations() -> None:
    result = _borrowed_seventh_piece()
    beat = next(index for index, source in enumerate(result.modal_sources) if source is not None)
    sources = list(result.modal_sources)
    sources[beat] = (
        ModalSource.PARALLEL_MAJOR
        if sources[beat] is ModalSource.PARALLEL_NATURAL_MINOR
        else ModalSource.PARALLEL_NATURAL_MINOR
    )

    report = verify_result(replace(result, modal_sources=tuple(sources)))

    assert "CM041" in report.failed_rules


def test_third_inversion_requires_exact_secondary_seventh_reconstruction() -> None:
    result = _third_inversion_secondary_seventh()
    assert verify_result(result).valid

    forged_bass = (52, result.bass[1])
    report = verify_result(replace(result, bass=forged_bass))

    assert not report.valid
    assert "CM033" in report.failed_rules
    assert "CM056" in report.failed_rules


def test_resolution_remains_separate_from_local_semantic_dispatch() -> None:
    result = _third_inversion_secondary_seventh()
    assert (
        secondary_seventh_runtime.reconstruct_secondary_leading_tone_seventh(result, 0)
        is not None
    )
    broken_resolution = replace(result, bass=(result.bass[0], result.bass[0] - 3))

    report = verify_result(broken_resolution)

    assert "CM057" in report.failed_rules
