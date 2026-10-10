"""Scalar reconstruction of musical obligations; imports no compiler or solver."""

from __future__ import annotations

from itertools import pairwise

from .models import HarmonizationRequest


def verify_harmonization(request: HarmonizationRequest, rows: object) -> tuple[str, ...]:
    if not isinstance(rows, (tuple, list)) or len(rows) != len(request.chords):
        return ("SHAPE",)
    if any(
        not isinstance(row, (tuple, list))
        or len(row) != 4
        or any(type(p) is not int or not 0 <= p <= 127 for p in row)
        for row in rows
    ):
        return ("PITCH_OR_SHAPE",)
    tonic = {"C": 0, "G": 7, "D": 2, "A": 9, "E": 4, "F": 5, "Bb": 10, "Eb": 3}[request.key]
    scale = (0, 2, 4, 5, 7, 9, 11)
    issues: set[str] = set()
    for i, (row, chord, given) in enumerate(
        zip(rows, request.chords, request.given_voices, strict=True)
    ):
        tones = [
            (tonic + scale[(chord.degree + offset) % 7]) % 12
            for offset in (0, 2, 4, 6)[: 4 if chord.seventh else 3]
        ]
        if {pitch % 12 for pitch in row} != set(tones):
            issues.add("CHORD_CONTENT_OR_COMPLETENESS")
        if row[3] % 12 != tones[chord.inversion]:
            issues.add("INVERSION")
        for pitch, anchor, (low, high) in zip(row, given, request.ranges, strict=True):
            if anchor is not None and pitch != anchor:
                issues.add("GIVEN_VOICE")
            if not low <= pitch <= high:
                issues.add("RANGE")
        if any(a <= b for a, b in pairwise(row)):
            issues.add("VOICE_ORDER")
        if row[0] - row[1] > request.max_upper_spacing or (
            row[1] - row[2] > request.max_upper_spacing
        ):
            issues.add("UPPER_SPACING")
        if i + 1 == len(rows):
            continue
        following = rows[i + 1]
        for a in range(4):
            for b in range(a + 1, 4):
                before = (row[a] - row[b]) % 12
                after = (following[a] - following[b]) % 12
                if (
                    before == after
                    and before in (0, 7)
                    and ((following[a] - row[a]) * (following[b] - row[b]) > 0)
                ):
                    issues.add("PARALLEL_PERFECT")
        for before_pitch, after_pitch in zip(row, following, strict=True):
            if (
                chord.degree == 4
                and request.chords[i + 1].degree == 0
                and (before_pitch % 12 == (tonic + 11) % 12 and after_pitch != before_pitch + 1)
            ):
                issues.add("LEADING_TONE")
            if (
                chord.seventh
                and before_pitch % 12 == tones[3]
                and (after_pitch - before_pitch not in (-1, -2))
            ):
                issues.add("SEVENTH_RESOLUTION")
    return tuple(sorted(issues))
