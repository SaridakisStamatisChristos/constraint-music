"""Render captured Diatony B/T/A/S rows; never sort pitches or change musical events.

This writer imports no generator or MIDI parser. Four chord rows and whole-note
rhythm are the pinned capture profile, not a general Diatony interchange format.
"""

from __future__ import annotations

import struct
from typing import Any

from .contract import VOICES, validate_request


def read_rows(text: str) -> list[list[int]]:
    lines = text.splitlines()
    if len(lines) != 5 or lines[0] != "VOICE_ROWS_B_T_A_S":
        raise ValueError("invalid Diatony capture header/row count")
    rows = [[int(value) for value in line.split()] for line in lines[1:]]
    if any(len(row) != 4 or any(not 0 <= value <= 127 for value in row) for row in rows):
        raise ValueError("invalid Diatony capture pitches")
    return rows


def _vlq(value: int) -> bytes:
    if not 0 <= value <= 0x0FFFFFFF:
        raise ValueError("invalid MIDI delta")
    result = [value & 127]
    value >>= 7
    while value:
        result.insert(0, (value & 127) | 128)
        value >>= 7
    return bytes(result)


def _track(payload: bytes) -> bytes:
    return b"MTrk" + struct.pack(">I", len(payload)) + payload


def render(text: str, request: dict[str, Any], *, ppqn: int = 120) -> bytes:
    validate_request(request)
    rows = read_rows(text)
    if type(ppqn) is not int or not 1 <= ppqn <= 32767:
        raise ValueError("invalid PPQN")
    key = 0 if request["key"] == "C" else 1
    # Context comes from the external request, not the exporter or score labels.
    context = (
        b"\x00\xff\x51\x03\x07\xa1\x20"
        + b"\x00\xff\x58\x04\x04\x02\x18\x08"
        + bytes([0, 255, 89, 2, key, 0])
        + b"\x00\xff\x2f\x00"
    )
    tracks = [_track(context)]
    for channel, voice in enumerate(VOICES):
        name = voice.encode("ascii")
        payload = bytes([0, 255, 3, len(name)]) + name
        for row in rows:
            pitch = row[3 - channel]  # Public return_solution order: B, T, A, S.
            payload += bytes([0, 144 + channel, pitch, 64])
            payload += _vlq(4 * ppqn) + bytes([128 + channel, pitch, 0])
        tracks.append(_track(payload + b"\x00\xff\x2f\x00"))
    return b"MThd" + struct.pack(">IHHH", 6, 1, 5, ppqn) + b"".join(tracks)
