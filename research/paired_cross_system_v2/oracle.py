"""Event-grid checks independent of generators and the feasibility witness search."""

from __future__ import annotations

from collections import Counter
from typing import Any

from research.cross_system_assurance_v1.midi_probe import parse_mido, parse_smf
from research.paired_cross_system_v1.oracle import delivery as relation

from .contract import KEYS, RANGES, SCALE, VOICES, admission


def semantics(request: dict[str, Any], events: list) -> list[str]:
    if admission(request) != "SUPPORTED":
        return ["UNSUPPORTED_REQUEST"]
    issues: set[str] = set()
    n = len(request["degrees"])
    if len(events) != 4 * n:
        return ["EVENT_COUNT"]
    grid = {}
    for row in events:
        if not isinstance(row, list) or len(row) != 4:
            return ["EVENT_SHAPE"]
        voice, pitch, onset, duration = row
        if voice not in VOICES or type(pitch) is not int or not 0 <= pitch <= 127:
            return ["VOICE_OR_PITCH"]
        if type(onset) is not str or onset not in [str(i) for i in range(n)] or duration != "1":
            return ["EVENT_TIME"]
        cell = (voice, int(onset))
        if cell in grid:
            return ["DUPLICATE_VOICE_TIME"]
        grid[cell] = pitch
    if set(grid) != {(v, i) for v in VOICES for i in range(n)}:
        return ["VOICE_COVERAGE"]
    tonic = KEYS[request["key"]][0]
    rows = [[grid[v, i] for v in VOICES] for i in range(n)]
    for i, pitches in enumerate(rows):
        degree = request["degrees"][i]
        tones = (0, 2, 4, 6) if request["sevenths"][i] else (0, 2, 4)
        expected = {(tonic + SCALE[(degree + t) % 7]) % 12 for t in tones}
        if {p % 12 for p in pitches} != expected:
            issues.add("CHORD_CONTENT_OR_COMPLETENESS")
        if pitches[-1] != request["bass"][i]:
            issues.add("GIVEN_BASS_OR_INVERSION")
        if request["given_soprano"][i] is not None and pitches[0] != request["given_soprano"][i]:
            issues.add("GIVEN_SOPRANO")
        if any(not lo <= p <= hi for p, (lo, hi) in zip(pitches, RANGES, strict=True)):
            issues.add("RANGE")
        if any(pitches[j] <= pitches[j + 1] for j in range(3)):
            issues.add("CROSSING_OR_UNISON")
        if pitches[0] - pitches[1] > 12 or pitches[1] - pitches[2] > 12:
            issues.add("UPPER_SPACING")
        if i + 1 == n:
            continue
        right = rows[i + 1]
        for a in range(4):
            for b in range(a + 1, 4):
                if (
                    (pitches[a] - pitches[b]) % 12 == (right[a] - right[b]) % 12
                    and (pitches[a] - pitches[b]) % 12 in (0, 7)
                    and (right[a] - pitches[a]) * (right[b] - pitches[b]) > 0
                ):
                    issues.add("PARALLEL_PERFECT")
        for a, b in zip(pitches, right, strict=True):
            if (
                request["degrees"][i : i + 2] == [4, 0]
                and a % 12 == (tonic + 11) % 12
                and b != a + 1
            ):
                issues.add("LEADING_TONE")
            if request["sevenths"][i] and a % 12 == (tonic + 5) % 12 and b - a not in (-1, -2):
                issues.add("SEVENTH_RESOLUTION")
    return sorted(issues)


def delivery(
    request: dict[str, Any], events: list, data: bytes, system: str, *, native=False
) -> dict:
    if native and system == "diatony":
        try:
            parsed = parse_smf(data)
            if parsed != parse_mido(data):
                raise ValueError("parser disagreement")
            actual = Counter((p, a, d) for _, _, p, a, d in parsed["events"])
            # Native Diatony uses four-quarter chords, one anonymous track/channel.
            expected = Counter((p, str(4 * int(a)), "4") for _, p, a, _ in events)
            return {
                "status": "UNOBSERVABLE",
                "issues": ["VOICE_IDENTITY_CONTEXT_TIME_PROFILE"],
                "native_unvoiced_relation": "PASS" if actual == expected else "FAIL",
            }
        except (ValueError, OSError, KeyError, IndexError, EOFError) as exc:
            return {"status": "BLOCKED", "issues": ["SMF_PARSE"], "error": type(exc).__name__}
    # The archived byte checker uses only context and event identity, not tonal content.
    return relation(request, events, data, system if native else "constraint-music")
