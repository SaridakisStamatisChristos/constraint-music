from __future__ import annotations

from dataclasses import replace
from functools import cache

from constraint_music.modal_mixture import canonical_modal_source
from constraint_music.models import GenerationSpec
from constraint_music.modulation_runtime import ModulatedSatbGenerationResult
from constraint_music.satb import SatbGenerationResult
from constraint_music.secondary_leading_tone import (
    secondary_leading_tone_seventh_pitch_classes,
)
from constraint_music.secondary_leading_tone_seventh_runtime import (
    _exact_applied_dominant,
    reconstruct_secondary_leading_tone_seventh,
)
from constraint_music.solver import ConstraintMusicSolver
from constraint_music.verifier import verify_result


@cache
def _secondary_piece() -> SatbGenerationResult:
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
            seed=5121,
            max_time_seconds=30,
            tension_curve=(0.8, 0.1),
        )
    )
    assert isinstance(result, SatbGenerationResult)
    return result


@cache
def _mixed_piece() -> SatbGenerationResult:
    result = ConstraintMusicSolver().generate(
        GenerationSpec(
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
            seed=5122,
            max_time_seconds=30,
            tension_curve=(0.8, 0.2, 0.7, 0.3, 0.1),
        )
    )
    assert isinstance(result, SatbGenerationResult)
    return result


@cache
def _modulated_piece() -> ModulatedSatbGenerationResult:
    graph = (
        (1, 2),
        (0, 4),
        (3,),
        (1,),
        (0,),
        (5,),
        (6,),
    )
    result = ConstraintMusicSolver().generate(
        GenerationSpec(
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
            seed=5123,
            max_time_seconds=30,
            tension_curve=(0.05, 0.15, 0.1, 0.8, 0.35, 0.45, 0.9, 0.05),
        )
    )
    assert isinstance(result, ModulatedSatbGenerationResult)
    return result


def _secondary_beat(result: SatbGenerationResult) -> int:
    for beat in range(result.spec.total_beats):
        if reconstruct_secondary_leading_tone_seventh(result, beat) is not None:
            return beat
    raise AssertionError("Expected a reconstructed secondary leading-tone seventh")


def test_modal_source_overlap_still_fails_closed() -> None:
    result = _secondary_piece()
    beat = _secondary_beat(result)
    sources = list(result.modal_sources)
    sources[beat] = canonical_modal_source(result.spec.active_key_at_beat(beat))
    report = verify_result(replace(result, modal_sources=tuple(sources)))
    assert not report.valid
    assert "CM055" in report.failed_rules


def test_secondary_seventh_still_cannot_occupy_legacy_cadence_anchor() -> None:
    result = _secondary_piece()
    forged_spec = replace(
        result.spec,
        minimum_secondary_leading_tone_seventh_chords=0,
        require_authentic_cadence=True,
    )
    report = verify_result(replace(result, spec=forged_spec))
    assert not report.valid
    assert "CM055" in report.failed_rules


def test_diminished_fifth_resolution_is_quality_and_target_aware() -> None:
    result = _secondary_piece()
    beat = _secondary_beat(result)
    reconstruction = reconstruct_secondary_leading_tone_seventh(result, beat)
    assert reconstruction is not None
    _quality, tones = reconstruction
    diminished_fifth = tones[2]
    for label in ("soprano", "alto", "tenor", "bass"):
        voice = getattr(result, label)
        if voice[beat] % 12 != diminished_fifth:
            continue
        forged = list(voice)
        forged[beat + 1] = forged[beat] + 1
        report = verify_result(replace(result, **{label: tuple(forged)}))
        assert not report.valid
        assert "CM057" in report.failed_rules
        return
    raise AssertionError("Complete secondary seventh must carry its diminished fifth")


def test_applied_and_secondary_seventh_minima_remain_functionally_distinct() -> None:
    result = _mixed_piece()
    applied_count = sum(
        _exact_applied_dominant(result, beat)
        for beat in range(result.spec.total_beats)
    )
    secondary_count = sum(
        reconstruct_secondary_leading_tone_seventh(result, beat) is not None
        for beat in range(result.spec.total_beats)
    )
    assert applied_count >= result.spec.minimum_applied_dominants
    assert secondary_count >= result.spec.minimum_secondary_leading_tone_seventh_chords
    assert verify_result(result).valid


def test_post_modulation_secondary_seventh_uses_persistent_destination_key() -> None:
    result = _modulated_piece()
    beat = _secondary_beat(result)
    boundary = result.spec.modulation_boundary_beat
    destination = result.spec.modulation_destination
    assert boundary is not None
    assert destination is not None
    assert beat >= boundary

    target = result.tonicization_targets[beat]
    assert target is not None
    reconstruction = reconstruct_secondary_leading_tone_seventh(result, beat)
    assert reconstruction is not None
    quality, expected = reconstruction
    assert expected == secondary_leading_tone_seventh_pitch_classes(
        destination,
        target,
        quality,
    )
    assert verify_result(result).valid


def test_post_modulation_stale_global_interpretation_fails_closed() -> None:
    result = _modulated_piece()
    beat = _secondary_beat(result)
    target = result.tonicization_targets[beat]
    reconstruction = reconstruct_secondary_leading_tone_seventh(result, beat)
    assert target is not None
    assert reconstruction is not None
    quality, _expected = reconstruction

    stale = secondary_leading_tone_seventh_pitch_classes(
        result.spec.tonal_key,
        target,
        quality,
    )
    voices = [
        list(result.soprano),
        list(result.alto),
        list(result.tenor),
        list(result.bass),
    ]
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
