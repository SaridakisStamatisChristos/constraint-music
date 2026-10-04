from __future__ import annotations

import pytest

from constraint_music.models import GenerationSpec
from constraint_music.secondary_leading_tone import (
    SecondaryLeadingToneSeventhQuality,
    secondary_leading_tone_seventh_name,
    secondary_leading_tone_seventh_pitch_classes,
    secondary_leading_tone_seventh_qualities,
    secondary_leading_tone_seventh_support_degree,
    supported_secondary_leading_tone_seventh_targets,
    supported_secondary_leading_tone_seventh_variants,
)
from constraint_music.secondary_leading_tone_complete_compiler import (
    secondary_seventh_outer_pitch_classes,
)
from constraint_music.secondary_leading_tone_seventh_runtime import _v212_chord_rows
from constraint_music.theory import ChordKind, Key, Mode

TONICS = (
    "C",
    "C#",
    "D",
    "D#",
    "E",
    "F",
    "F#",
    "G",
    "G#",
    "A",
    "A#",
    "B",
)


@pytest.mark.parametrize("mode", [Mode.MAJOR, Mode.MINOR])
@pytest.mark.parametrize("tonic", TONICS)
def test_every_progression_reachable_major_or_minor_target_is_certified(
    tonic: str,
    mode: Mode,
) -> None:
    spec = GenerationSpec(
        key=tonic,
        mode=mode,
        require_authentic_cadence=False,
        harmony_vocabulary="triads+sevenths",
        secondary_leading_tone_seventh_enabled=True,
    )
    key = spec.tonal_key
    expected_targets = tuple(
        degree
        for degree in range(1, 7)
        if key.triad_quality(degree) in {"major", "minor"}
        and any(degree in targets for targets in spec.progression_graph)
    )
    assert supported_secondary_leading_tone_seventh_targets(
        key,
        spec.progression_graph,
    ) == expected_targets


@pytest.mark.parametrize("mode", [Mode.MAJOR, Mode.MINOR])
@pytest.mark.parametrize("tonic", TONICS)
def test_every_certified_quality_has_all_four_inversions_and_exact_spelling(
    tonic: str,
    mode: Mode,
) -> None:
    spec = GenerationSpec(
        key=tonic,
        mode=mode,
        require_authentic_cadence=False,
        harmony_vocabulary="triads+sevenths",
        secondary_leading_tone_seventh_enabled=True,
    )
    key = spec.tonal_key
    rows = _v212_chord_rows(
        key,
        spec.progression_graph,
        True,
        False,
        False,
        False,
        True,
    )

    for target, quality, support in supported_secondary_leading_tone_seventh_variants(
        key,
        spec.progression_graph,
    ):
        assert target in spec.progression_graph[support]
        tones = secondary_leading_tone_seventh_pitch_classes(key, target, quality)
        intervals = tuple((tone - tones[0]) % 12 for tone in tones)
        expected_intervals = (
            (0, 3, 6, 9)
            if quality is SecondaryLeadingToneSeventhQuality.FULLY_DIMINISHED
            else (0, 3, 6, 10)
        )
        assert intervals == expected_intervals
        assert len(set(tones)) == 4

        inversions = {
            row[2]
            for row in rows
            if row[0] == support
            and row[1] == int(ChordKind.SEVENTH)
            and row[3] == target
            and set(row[5:]) == set(tones)
        }
        assert inversions == {0, 1, 2, 3}
        for inversion in range(4):
            name = secondary_leading_tone_seventh_name(
                key,
                target,
                inversion,
                quality,
            )
            assert name.endswith(f"/{key.chord_name(target)}")


def test_quality_policy_tracks_temporary_tonic_quality_not_home_mode() -> None:
    for tonic in TONICS:
        for mode in (Mode.MAJOR, Mode.MINOR):
            key = Key(tonic, mode)
            for target in range(1, 7):
                target_quality = key.triad_quality(target)
                qualities = secondary_leading_tone_seventh_qualities(key, target)
                if target_quality == "major":
                    assert qualities == (
                        SecondaryLeadingToneSeventhQuality.FULLY_DIMINISHED,
                        SecondaryLeadingToneSeventhQuality.HALF_DIMINISHED,
                    )
                elif target_quality == "minor":
                    assert qualities == (
                        SecondaryLeadingToneSeventhQuality.FULLY_DIMINISHED,
                    )
                else:
                    assert qualities == ()


def test_structural_support_no_longer_requires_diatonic_overlap() -> None:
    spec = GenerationSpec(
        key="C",
        mode=Mode.MAJOR,
        require_authentic_cadence=False,
        harmony_vocabulary="triads+sevenths",
        secondary_leading_tone_seventh_enabled=True,
    )
    key = spec.tonal_key

    # vii°7/iii was excluded by the old v2.11 two-tone-overlap workaround.
    target = 2
    support = secondary_leading_tone_seventh_support_degree(
        key,
        target,
        spec.progression_graph,
        SecondaryLeadingToneSeventhQuality.FULLY_DIMINISHED,
    )
    assert target in spec.progression_graph[support]
    tones = set(
        secondary_leading_tone_seventh_pitch_classes(
            key,
            target,
            SecondaryLeadingToneSeventhQuality.FULLY_DIMINISHED,
        )
    )
    assert len(tones & set(key.triad_pitch_classes(support))) < 2
    assert tones <= secondary_seventh_outer_pitch_classes(spec, 0)
