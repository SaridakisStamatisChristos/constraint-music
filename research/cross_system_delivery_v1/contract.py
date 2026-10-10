"""Small shared request envelope, with explicit limits on native input mapping."""

from __future__ import annotations

from typing import Any

VOICES = ("Soprano", "Alto", "Tenor", "Bass")


def request_for(key: str) -> dict[str, Any]:
    if key not in ("C", "G"):
        raise ValueError("unsupported key")
    return {
        "schema_version": 1,
        "request_id": f"delivery-envelope-v1.{key}",
        "key": key,
        "mode": "major",
        "voices": list(VOICES),
        "duration_quarters": 16,
        "meter": "4/4",
        "tempo_bpm": 120,
        "allowed_note_durations_quarters": [1, 4],
        "rests": False,
        "ties": False,
        "harmony_constraint": None,
        "given_voice": None,
    }


def validate_request(request: dict[str, Any]) -> None:
    # No silent weakening, coercion, unknown fields, or claim of broader support.
    import json

    expected = request_for(request.get("key", ""))
    if json.dumps(request, sort_keys=True) != json.dumps(expected, sort_keys=True):
        raise ValueError("unsupported shared request")


def inspect_input(system: str, request: dict[str, Any], native: dict[str, Any]) -> list[str]:
    """Check inspected input fields; defaults are disclosed, never caller-supplied facts."""
    validate_request(request)
    issues = []
    if native.get("key") != request["key"]:
        issues.append("INPUT_KEY")
    if system == "constraint-music":
        if (
            native.get("mode") != "major"
            or native.get("bars") != 4
            or native.get("beats_per_bar") != 4
            or native.get("subdivisions_per_beat") != 1
            or native.get("rhythm_enabled") is not False
            or native.get("tempo_bpm") != 120
        ):
            issues.append("INPUT_ENVELOPE")
    elif system == "music21":
        basses = {"C": ["C3", "F3", "G3", "C3"], "G": ["G2", "C3", "D3", "G2"]}
        if (
            native.get("bass") != basses[request["key"]]
            or native.get("meter") != "4/4"
            or native.get("quarter_length") != 4
            or native.get("chorale_output") is not True
        ):
            issues.append("INPUT_ENVELOPE")
    elif system == "diatony":
        if native.get("degrees") != [0, 3, 4, 0] or native.get("inversions") != [0] * 4:
            issues.append("INPUT_ENVELOPE")
    else:
        raise ValueError("unknown input profile")
    return issues
