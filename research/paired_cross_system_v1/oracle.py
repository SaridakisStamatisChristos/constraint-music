"""Independent shared tonal/event oracle; imports no generator/checking music library."""

from __future__ import annotations

import itertools
from collections import Counter
from fractions import Fraction
from typing import Any

from research.cross_system_assurance_v1.midi_probe import parse_mido, parse_smf

from .contract import KEYS, VOICES, admission, canonical, content_hash

SCALE = (0, 2, 4, 5, 7, 9, 11)


def semantics(request: dict[str, Any], events: list[list[Any]]) -> list[str]:
    """Events: [voice, pitch, onset_quarters, duration_quarters]; exact rational times."""
    issues: set[str] = set()
    if admission(request) != "SUPPORTED":
        return ["UNSUPPORTED_REQUEST"]
    tonic = KEYS[request["key"]][0]
    endpoint = 4 * len(request["degrees"])
    parts: dict[str, list[tuple[int, Fraction, Fraction]]] = {v: [] for v in VOICES}
    try:
        for event in events:
            if not isinstance(event, list) or len(event) != 4:
                return ["EVENT_SHAPE"]
            voice, pitch, onset, duration = event
            if voice not in parts or type(pitch) is not int or not 0 <= pitch <= 127:
                return ["VOICE_OR_PITCH"]
            a, d = Fraction(onset), Fraction(duration)
            if (
                type(onset) is not str
                or type(duration) is not str
                or str(a) != onset
                or str(d) != duration
                or a.denominator != 1
            ):
                return ["EVENT_SHAPE"]
            if d not in (1, 4) or a < 0 or a + d > endpoint:
                issues.add("DURATION_OR_BOUNDS")
            if pitch % 12 not in {(tonic + p) % 12 for p in SCALE}:
                issues.add("SCALE")
            parts[voice].append((pitch, a, d))
    except (TypeError, ValueError, ZeroDivisionError):
        return ["EVENT_SHAPE"]
    for values in parts.values():
        cursor = Fraction(0)
        for _, a, d in sorted(values, key=lambda row: row[1]):
            if a != cursor or d <= 0:
                issues.add("GAP_OVERLAP")
            cursor = a + d
        if cursor != endpoint:
            issues.add("LENGTH")
    snapshots: list[list[int]] = []
    for quarter in range(endpoint):
        pitches = []
        for voice in VOICES:
            active = [p for p, a, d in parts[voice] if a <= quarter < a + d]
            if len(active) != 1:
                issues.add("VOICE_COVERAGE")
                break
            pitches.append(active[0])
        if len(pitches) != 4:
            continue
        if pitches != sorted(pitches, reverse=True):
            issues.add("CROSSING")
        degree = request["degrees"][quarter // 4]
        triad = {(tonic + SCALE[(degree + x) % 7]) % 12 for x in (0, 2, 4)}
        if {p % 12 for p in pitches} != triad:
            issues.add("TRIAD_COMPLETENESS_OR_CONTENT")
        if pitches[-1] % 12 != (tonic + SCALE[degree]) % 12:
            issues.add("ROOT_POSITION")
        if quarter % 4 == 0:
            snapshots.append(pitches)
        elif snapshots and pitches != snapshots[-1]:
            issues.add("CHORD_VOICING_CHANGED")
    if len(snapshots) == len(request["degrees"]):
        for index, (left, right) in enumerate(itertools.pairwise(snapshots)):
            for i in range(4):
                for j in range(i + 1, 4):
                    interval_a, interval_b = (left[i] - left[j]) % 12, (right[i] - right[j]) % 12
                    if (
                        interval_a == interval_b
                        and interval_a in (0, 7)
                        and (right[i] - left[i]) * (right[j] - left[j]) > 0
                    ):
                        issues.add("PARALLEL_PERFECT")
            if request["degrees"][index : index + 2] == [4, 0]:
                for a, b in zip(left, right, strict=False):
                    if a % 12 == (tonic + 11) % 12 and b != a + 1:
                        issues.add("CADENTIAL_LEADING_TONE")
    return sorted(issues)


def delivery(
    request: dict[str, Any],
    events: list[list[Any]],
    data: bytes,
    system: str,
    *,
    native: bool = False,
) -> dict[str, Any]:
    try:
        parsed = parse_smf(data)
        if parsed != parse_mido(data):
            return {"status": "BLOCKED", "issues": ["PARSER_DISAGREEMENT"]}
    except (ValueError, TypeError, OSError, EOFError, KeyError, IndexError) as exc:
        return {"status": "BLOCKED", "issues": ["SMF_PARSE"], "error_type": type(exc).__name__}
    if native and system == "diatony":
        actual = Counter((p, a, d) for _, _, p, a, d in parsed["events"])
        expected = Counter((p, a, d) for _, p, a, d in events)
        return {
            "status": "UNOBSERVABLE",
            "issues": ["NATIVE_VOICE_IDENTITY", "NATIVE_CONTEXT"],
            "unvoiced_relation": "PASS" if actual == expected else "FAIL",
        }
    mapping = {(i + 1, 0 if system == "music21" else i): voice for i, voice in enumerate(VOICES)}
    observed = Counter(
        (mapping.get((track, ch)), p, a, d) for track, ch, p, a, d in parsed["events"]
    )
    expected_events = Counter(tuple(e) for e in events)
    context = sorted(
        [
            ["0", "key", f"{KEYS[request['key']][1]}:0"],
            ["0", "meter", "4/4"],
            ["0", "tempo", str(round(60_000_000 / request["tempo_bpm"]))],
        ]
    )
    issues = []
    if observed != expected_events:
        issues.append("EXACT_VOICED_EVENTS")
    if parsed["context"] != context:
        issues.append("KEY_METER_TEMPO")
    return {
        "status": "REJECT" if issues else "PASS",
        "issues": issues,
        "parsed_notes": len(parsed["events"]),
        "division": parsed["division"],
        "parser_agreement": True,
    }


def evaluate(
    expected: dict[str, Any], artifact: dict[str, Any], data: bytes, system: str
) -> dict[str, Any]:
    """Separate trusted request; digests are admission checks, never semantic evidence."""
    eligibility = admission(expected)
    if eligibility != "SUPPORTED":
        return {"status": eligibility, "boundary": "request", "issues": ["REQUEST_ADMISSION"]}
    try:
        if set(artifact) != {"request", "events", "events_sha256"}:
            raise ValueError("artifact fields")
        if canonical(artifact["request"]) != canonical(expected):
            return {
                "status": "REJECT",
                "boundary": "request",
                "issues": ["EXTERNAL_REQUEST_BINDING"],
            }
        if artifact["events_sha256"] != content_hash(artifact["events"]):
            return {"status": "REJECT", "boundary": "artifact", "issues": ["EVENT_INTEGRITY"]}
        issues = semantics(expected, artifact["events"])
        if issues:
            return {"status": "REJECT", "boundary": "artifact", "issues": issues}
        result = delivery(expected, artifact["events"], data, system)
        return {"status": result["status"], "boundary": "delivery", "issues": result["issues"]}
    except (ValueError, KeyError, TypeError):
        return {"status": "BLOCKED", "boundary": "artifact", "issues": ["ARTIFACT_ADMISSION"]}
