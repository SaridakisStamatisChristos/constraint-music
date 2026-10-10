"""A narrow common task with fixed bass and optional soprano anchors."""

from __future__ import annotations

from typing import Any

from research.paired_cross_system_v1.contract import KEYS, SYSTEMS, VOICES, canonical, content_hash

__all__ = ["KEYS", "SYSTEMS", "VOICES", "admission", "canonical", "content_hash", "make_request"]
RANGES = ((60, 84), (55, 74), (48, 67), (48, 59))
SCALE = (0, 2, 4, 5, 7, 9, 11)


def make_request(
    identity: str,
    key: str,
    degrees: list[int],
    inversions: list[int],
    sevenths: list[bool],
    given: list[int | None],
    tempo: int = 108,
) -> dict[str, Any]:
    tonic = KEYS[key][0]
    return {
        "schema_version": 2,
        "request_id": identity,
        "key": key,
        "mode": "major",
        "degrees": degrees,
        "inversions": inversions,
        "sevenths": sevenths,
        "bass": [
            48 + (tonic + SCALE[(d + 2 * inv) % 7]) % 12
            for d, inv in zip(degrees, inversions, strict=True)
        ],
        "given_soprano": given,
        "chord_quarters": 1,
        "meter": "4/4",
        "tempo_bpm": tempo,
        "voice_ranges": [list(x) for x in RANGES],
        "strict_noncrossing": True,
        "max_adjacent_upper_spacing": 12,
        "complete_chords": True,
        "parallel_perfects": False,
        "cadential_leading_tone_resolution": True,
        "seventh_step_down": True,
        "rests": False,
        "ties": False,
    }


def admission(request: dict[str, Any]) -> str:
    try:
        n = len(request["degrees"])
        if n not in (8, 12) or request["key"] not in KEYS or request["mode"] != "major":
            return "UNSUPPORTED"
        if any(len(request[k]) != n for k in ("inversions", "sevenths", "bass", "given_soprano")):
            return "BLOCKED"
        if any(type(d) is not int or not 0 <= d <= 6 for d in request["degrees"]):
            return "BLOCKED"
        if any(type(i) is not int or i not in (0, 1, 2) for i in request["inversions"]):
            return "UNSUPPORTED"
        if any(
            type(s) is not bool or (s and d != 4)
            for d, s in zip(request["degrees"], request["sevenths"], strict=True)
        ):
            return "UNSUPPORTED"
        if request["sevenths"][-1] or any(
            s and request["degrees"][i + 1] != 0 for i, s in enumerate(request["sevenths"][:-1])
        ):
            return "UNSUPPORTED"
        if any(
            p is not None and (type(p) is not int or not 60 <= p <= 84)
            for p in request["given_soprano"]
        ):
            return "BLOCKED"
        if request["tempo_bpm"] not in (90, 108, 120, 132):
            return "UNSUPPORTED"
        expected = make_request(
            request["request_id"],
            request["key"],
            request["degrees"],
            request["inversions"],
            request["sevenths"],
            request["given_soprano"],
            request["tempo_bpm"],
        )
        return "SUPPORTED" if canonical(request) == canonical(expected) else "UNSUPPORTED"
    except (KeyError, TypeError, ValueError, IndexError):
        return "BLOCKED"
