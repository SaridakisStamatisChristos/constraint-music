from __future__ import annotations

from dataclasses import replace
from functools import cache

from constraint_music.contract import HARD_CONSTRAINT_IDS
from constraint_music.models import GenerationResult, GenerationSpec
from constraint_music.provenance import artifact_payload, verify_artifact_integrity
from constraint_music.satb import SatbGenerationResult, result_from_dict
from constraint_music.solver import ConstraintMusicSolver
from constraint_music.theory import ChordKind
from constraint_music.verifier import verify_result

FORCED_DOMINANT_GRAPH: tuple[tuple[int, ...], ...] = (
    (0, 4),
    (1,),
    (2,),
    (3,),
    (0,),
    (5,),
    (0,),
)


@cache
def dominant_seventh_piece() -> SatbGenerationResult:
    spec = GenerationSpec(
        bars=1,
        beats_per_bar=4,
        subdivisions_per_beat=1,
        progression_graph=FORCED_DOMINANT_GRAPH,
        harmony_vocabulary="triads+sevenths",
        minimum_seventh_chords=1,
        max_time_seconds=20,
        workers=1,
        seed=2505,
        tension_curve=(0.05, 0.8, 0.02),
    )
    result = ConstraintMusicSolver().generate(spec)
    assert isinstance(result, SatbGenerationResult)
    return result


def test_expanded_solver_emits_verified_dominant_seventh() -> None:
    result = dominant_seventh_piece()
    assert result.validation.valid, result.validation.issues
    assert result.validation.checked_rules == HARD_CONSTRAINT_IDS
    assert result.chord_degrees == (0, 0, 4, 0)
    assert result.chord_kinds[2] is ChordKind.SEVENTH
    assert result.chord_kinds[-1] is ChordKind.TRIAD

    key = result.spec.tonal_key
    seventh = key.seventh_pitch_classes(4)
    pcs = {
        result.soprano[2] % 12,
        result.alto[2] % 12,
        result.tenor[2] % 12,
        result.bass[2] % 12,
    }
    assert pcs == set(seventh)
    assert result.bass[2] % 12 == seventh[result.chord_inversions[2]]
    assert result.chord_form_names[2].startswith("V")


def test_verifier_rejects_false_inversion_metadata() -> None:
    result = dominant_seventh_piece()
    inversions = list(result.chord_inversions)
    inversions[2] = (inversions[2] + 1) % 3
    report = verify_result(replace(result, chord_inversions=tuple(inversions)))
    assert not report.valid
    assert "CM034" in report.failed_rules


def test_verifier_rejects_unresolved_chordal_seventh() -> None:
    result = dominant_seventh_piece()
    seventh_pc = result.spec.tonal_key.seventh_pitch_classes(4)[3]
    for field_name in ("soprano", "alto", "tenor", "bass"):
        voice = list(getattr(result, field_name))
        if voice[2] % 12 != seventh_pc:
            continue
        voice[3] = voice[2]
        report = verify_result(replace(result, **{field_name: tuple(voice)}))
        assert not report.valid
        assert "CM035" in report.failed_rules
        return
    raise AssertionError("Generated V7 has no chordal seventh carrier")


def test_verifier_rejects_dominant_seventh_wrong_target() -> None:
    result = dominant_seventh_piece()
    chords = list(result.chord_degrees)
    chords[3] = 4
    report = verify_result(replace(result, chord_degrees=tuple(chords)))
    assert not report.valid
    assert "CM036" in report.failed_rules


def test_harmonic_form_tampering_breaks_semantic_provenance() -> None:
    result = dominant_seventh_piece()
    payload = artifact_payload(result)
    payload["music"]["chord_inversions"][2] = (
        int(payload["music"]["chord_inversions"][2]) + 1
    ) % 3
    tampered = result_from_dict(payload)
    issues = verify_artifact_integrity(tampered, payload)
    assert "composition digest mismatch" in issues
    assert "artifact content digest mismatch" in issues


def test_v24_satb_payload_without_harmonic_form_metadata_is_non_certifying(
    solved_piece: GenerationResult,
) -> None:
    assert isinstance(solved_piece, SatbGenerationResult)
    payload = solved_piece.to_dict()
    music = payload["music"]
    music.pop("chord_kinds", None)
    music.pop("chord_inversions", None)
    music.pop("chord_form_names", None)

    legacy = result_from_dict(payload)
    assert isinstance(legacy, SatbGenerationResult)
    assert legacy.chord_kinds == ()
    assert legacy.chord_inversions == ()
    report = verify_result(legacy)
    assert not report.valid
    assert "CM027" in report.failed_rules


def test_harmonic_form_distinctness_changes_kind_or_inversion() -> None:
    spec = GenerationSpec(
        bars=1,
        beats_per_bar=4,
        subdivisions_per_beat=1,
        require_authentic_cadence=False,
        harmony_vocabulary="triads+sevenths",
        max_time_seconds=15,
        workers=1,
        seed=2506,
        tension_curve=(0.05, 0.7, 0.05),
    )
    first, second = ConstraintMusicSolver().generate_many(
        spec,
        2,
        distinct_on=("harmonic_form",),
    )
    assert isinstance(first, SatbGenerationResult)
    assert isinstance(second, SatbGenerationResult)
    assert (first.chord_kinds, first.chord_inversions) != (
        second.chord_kinds,
        second.chord_inversions,
    )
    # The legacy harmony dimension remains only the degree sequence; it is not redefined here.
