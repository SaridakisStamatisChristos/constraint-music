"""Versioned shared requests and support admission; no generator imports."""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any

VOICES = ("Soprano", "Alto", "Tenor", "Bass")
KEYS = {
    "C": (0, 0),
    "G": (7, 1),
    "D": (2, 2),
    "A": (9, 3),
    "E": (4, 4),
    "F": (5, -1),
    "Bb": (10, -2),
    "Eb": (3, -3),
}
SYSTEMS = ("constraint-music", "music21", "diatony")


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def content_hash(value: Any) -> str:
    return sha256(canonical(value).encode()).hexdigest()


def make_request(identity: str, key: str, degrees: list[int], tempo: int = 120) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "request_id": identity,
        "key": key,
        "mode": "major",
        "degrees": degrees,
        "chord_quarters": 4,
        "meter": "4/4",
        "tempo_bpm": tempo,
        "allowed_note_quarters": [1, 4],
        "constant_voicing_per_chord": True,
        "root_position": True,
        "complete_triads": True,
        "noncrossing": True,
        "parallel_perfects": False,
        "cadential_leading_tone_resolution": True,
        "rests": False,
        "ties": False,
        "given_voice": None,
        "voices": list(VOICES),
    }


def admission(request: dict[str, Any]) -> str:
    """SUPPORTED/UNSUPPORTED/BLOCKED, before calling any engine."""
    try:
        prototype = make_request("x", "C", [0, 4, 0])
        if set(request) != set(prototype):
            return "BLOCKED"
        if type(request["schema_version"]) is not int or request["schema_version"] != 1:
            return "BLOCKED"
        if not isinstance(request["request_id"], str) or not request["request_id"]:
            return "BLOCKED"
        degrees = request["degrees"]
        if not isinstance(degrees, list) or not 3 <= len(degrees) <= 6:
            return "UNSUPPORTED"
        if any(type(d) is not int or not 0 <= d <= 6 for d in degrees):
            return "BLOCKED"
        if type(request["tempo_bpm"]) is not int or request["tempo_bpm"] not in (90, 108, 120, 132):
            return "UNSUPPORTED"
        if request["key"] not in KEYS:
            return "UNSUPPORTED"
        expected = make_request(
            request["request_id"], request["key"], degrees, request["tempo_bpm"]
        )
        return "SUPPORTED" if canonical(request) == canonical(expected) else "UNSUPPORTED"
    except (KeyError, TypeError, ValueError):
        return "BLOCKED"
