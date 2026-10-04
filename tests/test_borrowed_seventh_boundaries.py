from __future__ import annotations

from dataclasses import replace
from functools import cache

import pytest

from constraint_music.contract import HARD_CONSTRAINT_IDS
from constraint_music.modal_mixture import (
    ModalSource,
    borrowed_seventh_pitch_classes,
    borrowed_triad_pitch_classes,
    canonical_modal_source,
)
from constraint_music.models import GenerationSpec, ValidationReport
from constraint_music.modulation_runtime import ModulatedSatbGenerationResult, result_from_dict
from constraint_music.satb import SatbGenerationResult
from constraint_music.solver import (
    ConstraintMusicSolver,
    InternalVerificationError,
)
from constraint_music.theory import ChordKind
from constraint_music.verifier import verify_result


@cache
def boundary_piece() -> ModulatedSatbGenerationResult:
    graph = (
        (1,),
        (0, 2),
        (3,),
        (4,),
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
        minimum_seventh_chords=2,
        modal_mixture_enabled=True,
        minimum_borrowed_chords=4,
        modulation_enabled=True,
        modulation_destination_key="G",
        modulation_boundary_beat=3,
        avoid_parallel_perfects=False,
        workers=1,
        seed=2910,
        max_time_seconds=30,
        tension_curve=(0.05, 0.25, 0.1, 0.55, 0.45, 0.6, 0.9, 0.05),
    )
    result = ConstraintMusicSolver().generate(spec)
    assert isinstance(result, ModulatedSatbGenerationResult)
    return result


def _destination_borrowed_seventh_beat(result: ModulatedSatbGenerationResult) -> int:
    boundary = result.spec.modulation_boundary_beat
    assert boundary is not None
    for beat in range(boundary, result.spec.total_beats):
        if (
            result.modal_sources[beat] is not None
            and result.chord_kinds[beat] is ChordKind.SEVENTH
        ):
            return beat
    raise AssertionError("Expected a destination-region borrowed seventh")


def test_forged_modal_source_on_borrowed_seventh_fails_cm049() -> None:
    result = boundary_piece()
    beat = _destination_borrowed_seventh_beat(result)
    sources = list(result.modal_sources)
    sources[beat] = ModalSource.PARALLEL_MAJOR
    report = verify_result(replace(result, modal_sources=tuple(sources)))
    assert not report.valid
    assert "CM049" in report.failed_rules


def test_forged_borrowed_seventh_pitch_fails_cm050() -> None:
    result = boundary_piece()
    beat = _destination_borrowed_seventh_beat(result)
    forged = list(result.alto)
    forged[beat] += 1
    report = verify_result(replace(result, alto=tuple(forged)))
    assert not report.valid
    assert "CM050" in report.failed_rules


def test_unresolved_borrowed_seventh_fails_cm051() -> None:
    result = boundary_piece()
    beat = _destination_borrowed_seventh_beat(result)
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
        forged[beat + 1] = forged[beat]
        report = verify_result(replace(result, **{label: tuple(forged)}))
        assert not report.valid
        assert "CM051" in report.failed_rules
        break
    else:
        pytest.fail("Complete borrowed seventh must carry its chordal seventh")


def test_destination_source_interpretation_in_source_region_fails_closed() -> None:
    result = boundary_piece()
    beat = 1
    assert result.modal_sources[beat] is not None
    destination = result.spec.modulation_destination
    assert destination is not None
    source = canonical_modal_source(destination)
    wrong = borrowed_triad_pitch_classes(destination, result.chord_degrees[beat], source)
    voices = [list(result.soprano), list(result.alto), list(result.tenor), list(result.bass)]
    for voice, pc in zip(voices, (wrong[0], wrong[1], wrong[2], wrong[0]), strict=True):
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
    assert "CM042" in report.failed_rules or "CM046" in report.failed_rules


def test_borrowed_seventh_on_certified_pivot_fails_cm049() -> None:
    result = boundary_piece()
    boundary = result.spec.modulation_boundary_beat
    assert boundary is not None
    pivot = boundary - 1
    chords = list(result.chord_degrees)
    kinds = list(result.chord_kinds)
    sources = list(result.modal_sources)
    chords[pivot] = 1
    kinds[pivot] = ChordKind.SEVENTH
    sources[pivot] = canonical_modal_source(result.spec.tonal_key)
    report = verify_result(
        replace(
            result,
            chord_degrees=tuple(chords),
            chord_kinds=tuple(kinds),
            modal_sources=tuple(sources),
        )
    )
    assert not report.valid
    assert "CM049" in report.failed_rules
    assert "CM045" in report.failed_rules


def test_borrowed_seventh_on_destination_cadence_fails_closed() -> None:
    result = boundary_piece()
    beat = result.spec.total_beats - 2
    destination = result.spec.modulation_destination
    assert destination is not None
    sources = list(result.modal_sources)
    sources[beat] = canonical_modal_source(destination)
    report = verify_result(replace(result, modal_sources=tuple(sources)))
    assert not report.valid
    assert "CM049" in report.failed_rules
    assert "CM047" in report.failed_rules


def test_v27_v28_borrowed_triad_semantics_remain_valid() -> None:
    spec = GenerationSpec(
        bars=2,
        beats_per_bar=4,
        subdivisions_per_beat=1,
        require_authentic_cadence=False,
        modal_mixture_enabled=True,
        minimum_borrowed_chords=1,
        modulation_enabled=True,
        modulation_destination_key="G",
        modulation_boundary_beat=2,
        avoid_parallel_perfects=False,
        workers=1,
        seed=2911,
        max_time_seconds=30,
        tension_curve=(0.05, 0.15, 0.35, 0.55, 0.75, 0.9, 0.6, 0.1),
    )
    result = ConstraintMusicSolver().generate(spec)
    assert isinstance(result, ModulatedSatbGenerationResult)
    borrowed = [i for i, source in enumerate(result.modal_sources) if source is not None]
    assert borrowed
    assert all(result.chord_kinds[i] is ChordKind.TRIAD for i in borrowed)
    assert verify_result(result).valid
    loaded = result_from_dict(result.to_dict())
    assert isinstance(loaded, ModulatedSatbGenerationResult)
    assert verify_result(loaded).valid


def test_non_modulation_default_behavior_remains_verified() -> None:
    result = ConstraintMusicSolver().generate(
        GenerationSpec(
            bars=1,
            beats_per_bar=4,
            subdivisions_per_beat=1,
            workers=1,
            seed=2912,
            max_time_seconds=30,
        )
    )
    assert isinstance(result, SatbGenerationResult)
    assert not isinstance(result, ModulatedSatbGenerationResult)
    assert all(source is None for source in result.modal_sources)
    assert verify_result(result).valid


def test_solver_verifier_disagreement_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    def reject(_: object) -> ValidationReport:
        return ValidationReport(
            valid=False,
            issues=("[CM050] injected v2.9 verifier disagreement",),
            checked_rules=HARD_CONSTRAINT_IDS,
            failed_rules=("CM050",),
        )

    monkeypatch.setattr("constraint_music.solver.verify_result", reject)
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
        seed=2913,
        max_time_seconds=30,
        tension_curve=(0.55, 0.05),
    )
    with pytest.raises(InternalVerificationError, match="Solver/verifier contract breach"):
        ConstraintMusicSolver().generate(spec)
