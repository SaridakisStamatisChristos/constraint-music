from __future__ import annotations

from dataclasses import replace
from functools import cache

import pytest

from constraint_music.contract import HARD_CONSTRAINT_IDS
from constraint_music.models import GenerationSpec, RhythmState
from constraint_music.modulation_runtime import result_from_dict
from constraint_music.provenance import artifact_payload, verify_artifact_integrity
from constraint_music.satb import SatbGenerationResult
from constraint_music.secondary_leading_tone import (
    SecondaryLeadingToneSeventhQuality,
    secondary_leading_tone_seventh_name,
    secondary_leading_tone_seventh_pitch_class_variants,
    secondary_leading_tone_seventh_pitch_classes,
    secondary_leading_tone_seventh_qualities,
    secondary_leading_tone_seventh_support_degree,
)
from constraint_music.secondary_leading_tone_seventh_runtime import (
    _v212_chord_rows,
    reconstruct_secondary_leading_tone_seventh,
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
        seed=4121,
        max_time_seconds=30,
        tension_curve=(0.8, 0.1),
    )
    result = ConstraintMusicSolver().generate(spec)
    assert isinstance(result, SatbGenerationResult)
    return result


def _voice_pitch_classes(result: SatbGenerationResult, beat: int) -> tuple[int, ...]:
    return tuple(
        voice[beat] % 12
        for voice in (result.soprano, result.alto, result.tenor, result.bass)
    )


def _secondary_seventh_beat(result: SatbGenerationResult) -> int:
    for beat in range(result.spec.total_beats):
        if reconstruct_secondary_leading_tone_seventh(result, beat) is not None:
            return beat
    raise AssertionError("Expected a secondary leading-tone seventh chord")


def _synthetic_vii7_v(
    quality: SecondaryLeadingToneSeventhQuality,
    inversion: int,
) -> SatbGenerationResult:
    """Build a two-chord C-major vii(quality)7/V -> V artifact."""
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
    key = spec.tonal_key
    target = 4
    support = secondary_leading_tone_seventh_support_degree(
        key,
        target,
        spec.progression_graph,
        quality,
    )
    tones = secondary_leading_tone_seventh_pitch_classes(key, target, quality)

    # Exact SATB templates, S/A/T/B. The chromatic tendency members resolve to
    # G-major target tones in the same voice and the stable third supplies the
    # doubled target root. These fixtures deliberately cover every inversion.
    if quality is SecondaryLeadingToneSeventhQuality.FULLY_DIMINISHED:
        beat0_by_inversion = {
            0: (69, 63, 60, 54),  # A Eb C F#
            1: (66, 63, 60, 57),  # F# Eb C A
            2: (69, 63, 54, 48),  # A Eb F# C
            3: (69, 60, 54, 51),  # A C F# Eb
        }
    else:
        beat0_by_inversion = {
            0: (69, 64, 60, 54),  # A E C F#
            1: (66, 64, 60, 57),  # F# E C A
            2: (69, 64, 54, 48),  # A E F# C
            3: (69, 60, 54, 52),  # A C F# E
        }
    beat0 = beat0_by_inversion[inversion]

    root, third, diminished_fifth, chordal_seventh = tones
    fifth_delta = -1
    seventh_delta = (
        -1
        if quality is SecondaryLeadingToneSeventhQuality.FULLY_DIMINISHED
        else -2
    )
    beat1: list[int] = []
    for note in beat0:
        pc = note % 12
        if pc == root:
            beat1.append(note + 1)
        elif pc == diminished_fifth:
            beat1.append(note + fifth_delta)
        elif pc == chordal_seventh:
            beat1.append(note + seventh_delta)
        elif pc == third:
            beat1.append(note - 2)
        else:  # pragma: no cover - fixture invariant
            raise AssertionError("Unexpected secondary-seventh pitch class")

    soprano = (beat0[0], beat1[0])
    alto = (beat0[1], beat1[1])
    tenor = (beat0[2], beat1[2])
    bass = (beat0[3], beat1[3])
    target_triad = key.triad_pitch_classes(target)

    assert set(note % 12 for note in beat1) == set(target_triad)
    assert all(bass[i] < tenor[i] < alto[i] < soprano[i] for i in range(2))

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
        chord_inversions=(inversion, target_triad.index(bass[1] % 12)),
        tonicization_targets=(target, None),
        modal_sources=(None, None),
    )


def test_v212_quality_policy_pitch_classes_and_names_are_exact() -> None:
    key = Key("C", Mode.MAJOR)
    assert secondary_leading_tone_seventh_qualities(key, 4) == (
        SecondaryLeadingToneSeventhQuality.FULLY_DIMINISHED,
        SecondaryLeadingToneSeventhQuality.HALF_DIMINISHED,
    )
    assert secondary_leading_tone_seventh_pitch_classes(key, 4) == (6, 9, 0, 3)
    assert secondary_leading_tone_seventh_pitch_classes(
        key,
        4,
        SecondaryLeadingToneSeventhQuality.HALF_DIMINISHED,
    ) == (6, 9, 0, 4)
    assert secondary_leading_tone_seventh_name(key, 4, 0) == "vii°7/V"
    assert secondary_leading_tone_seventh_name(key, 4, 1) == "vii°65/V"
    assert secondary_leading_tone_seventh_name(key, 4, 2) == "vii°43/V"
    assert secondary_leading_tone_seventh_name(key, 4, 3) == "vii°42/V"
    assert secondary_leading_tone_seventh_name(
        key,
        4,
        3,
        SecondaryLeadingToneSeventhQuality.HALF_DIMINISHED,
    ) == "viiø42/V"


def test_half_diminished_is_restricted_to_major_targets() -> None:
    key = Key("C", Mode.MAJOR)
    assert key.triad_quality(1) == "minor"
    assert secondary_leading_tone_seventh_qualities(key, 1) == (
        SecondaryLeadingToneSeventhQuality.FULLY_DIMINISHED,
    )
    with pytest.raises(ValueError, match="not eligible"):
        secondary_leading_tone_seventh_pitch_classes(
            key,
            1,
            SecondaryLeadingToneSeventhQuality.HALF_DIMINISHED,
        )


def test_row_model_contains_every_certified_quality_and_inversion() -> None:
    spec = GenerationSpec(
        harmony_vocabulary="triads+sevenths",
        secondary_leading_tone_seventh_enabled=True,
    )
    key = spec.tonal_key
    target = 4
    rows = _v212_chord_rows(
        key,
        spec.progression_graph,
        True,
        False,
        False,
        False,
        True,
    )
    for quality, tones in secondary_leading_tone_seventh_pitch_class_variants(key, target):
        support = secondary_leading_tone_seventh_support_degree(
            key,
            target,
            spec.progression_graph,
            quality,
        )
        inversions = {
            row[2]
            for row in rows
            if row[0] == support
            and row[1] == int(ChordKind.SEVENTH)
            and row[3] == target
            and set(row[5:]) == set(tones)
        }
        assert inversions == {0, 1, 2, 3}


@pytest.mark.parametrize(
    "quality",
    [
        SecondaryLeadingToneSeventhQuality.FULLY_DIMINISHED,
        SecondaryLeadingToneSeventhQuality.HALF_DIMINISHED,
    ],
)
@pytest.mark.parametrize("inversion", [0, 1, 2, 3])
def test_verifier_accepts_every_certified_vii7_v_form(
    quality: SecondaryLeadingToneSeventhQuality,
    inversion: int,
) -> None:
    result = _synthetic_vii7_v(quality, inversion)
    reconstruction = reconstruct_secondary_leading_tone_seventh(result, 0)
    assert reconstruction is not None
    assert reconstruction[0] is quality
    report = verify_result(result)
    assert report.valid, report.issues
    assert report.checked_rules == HARD_CONSTRAINT_IDS


def test_solver_emits_an_independently_reconstructed_secondary_seventh() -> None:
    result = secondary_seventh_piece()
    assert result.validation.valid, result.validation.issues
    assert result.validation.checked_rules == HARD_CONSTRAINT_IDS
    beat = _secondary_seventh_beat(result)
    reconstruction = reconstruct_secondary_leading_tone_seventh(result, beat)
    assert reconstruction is not None
    quality, expected = reconstruction
    assert quality in {
        SecondaryLeadingToneSeventhQuality.FULLY_DIMINISHED,
        SecondaryLeadingToneSeventhQuality.HALF_DIMINISHED,
    }
    assert set(_voice_pitch_classes(result, beat)) == set(expected)
    assert len(set(_voice_pitch_classes(result, beat))) == 4
    assert result.chord_inversions[beat] in {0, 1, 2, 3}
    assert result.bass[beat] % 12 == expected[result.chord_inversions[beat]]


def test_verifier_rejects_inversion_metadata_that_does_not_match_bass() -> None:
    result = _synthetic_vii7_v(
        SecondaryLeadingToneSeventhQuality.FULLY_DIMINISHED,
        3,
    )
    inversions = list(result.chord_inversions)
    inversions[0] = 0
    report = verify_result(replace(result, chord_inversions=tuple(inversions)))
    assert not report.valid
    assert "CM056" in report.failed_rules


def test_verifier_rejects_missing_or_duplicated_secondary_seventh_tone() -> None:
    result = _synthetic_vii7_v(
        SecondaryLeadingToneSeventhQuality.FULLY_DIMINISHED,
        3,
    )
    alto = list(result.alto)
    alto[0] = result.soprano[0]
    report = verify_result(replace(result, alto=tuple(alto)))
    assert not report.valid
    assert "CM056" in report.failed_rules


def test_verifier_rejects_wrong_quality_specific_seventh_resolution() -> None:
    result = _synthetic_vii7_v(
        SecondaryLeadingToneSeventhQuality.HALF_DIMINISHED,
        3,
    )
    bass = list(result.bass)
    bass[1] = bass[0] - 1
    report = verify_result(replace(result, bass=tuple(bass)))
    assert not report.valid
    assert "CM057" in report.failed_rules


def test_verifier_rejects_wrong_local_leading_tone_resolution() -> None:
    result = _synthetic_vii7_v(
        SecondaryLeadingToneSeventhQuality.FULLY_DIMINISHED,
        0,
    )
    bass = list(result.bass)
    bass[1] = bass[0] + 2
    report = verify_result(replace(result, bass=tuple(bass)))
    assert not report.valid
    assert "CM057" in report.failed_rules


def test_secondary_seventh_cannot_counterfeit_applied_dominant_minimum() -> None:
    result = _synthetic_vii7_v(
        SecondaryLeadingToneSeventhQuality.FULLY_DIMINISHED,
        0,
    )
    forged_spec = replace(
        result.spec,
        tonicization_enabled=True,
        minimum_applied_dominants=1,
    )
    report = verify_result(replace(result, spec=forged_spec))
    assert not report.valid
    assert "CM037" in report.failed_rules


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
