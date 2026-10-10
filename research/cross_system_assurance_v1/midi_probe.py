"""Independent finite SMF parser plus a mido differential reference.

Scope: synchronous SMF 0/1 with PPQN, channel notes, and tempo/key/meter metadata.
This inspects actual bytes; voice identity is never inferred by sorting pitches.
"""

from __future__ import annotations

import io
import struct
from collections import defaultdict, deque
from fractions import Fraction
from typing import Any

from mido import MidiFile


def _vlq(data: bytes, index: int) -> tuple[int, int]:
    value = 0
    for _ in range(4):
        if index >= len(data):
            raise ValueError("truncated VLQ")
        byte = data[index]
        index += 1
        value = (value << 7) | (byte & 127)
        if byte < 128:
            return value, index
    raise ValueError("oversized VLQ")


def _normalize(
    division: int, events: list[tuple[int, int, int, int, int]], context: list[tuple[int, str, str]]
) -> dict[str, Any]:
    return {
        "division": division,
        "events": sorted(
            [
                track,
                channel,
                pitch,
                str(Fraction(onset, division)),
                str(Fraction(duration, division)),
            ]
            for track, channel, pitch, onset, duration in events
        ),
        "context": sorted(
            [str(Fraction(tick, division)), kind, value] for tick, kind, value in context
        ),
    }


def parse_smf(data: bytes) -> dict[str, Any]:
    if len(data) < 14 or data[:4] != b"MThd":
        raise ValueError("invalid SMF header")
    header_len = int.from_bytes(data[4:8], "big")
    if header_len != 6:
        raise ValueError("unsupported header size")
    fmt, track_count, division = struct.unpack(">HHH", data[8:14])
    if fmt not in (0, 1) or not track_count or not division or division & 32768:
        raise ValueError("unsupported SMF format/division")
    if fmt == 0 and track_count != 1:
        raise ValueError("invalid format-zero track count")
    cursor = 14
    events: list[tuple[int, int, int, int, int]] = []
    context: list[tuple[int, str, str]] = []
    for track in range(track_count):
        if data[cursor : cursor + 4] != b"MTrk" or cursor + 8 > len(data):
            raise ValueError("missing track")
        length = int.from_bytes(data[cursor + 4 : cursor + 8], "big")
        chunk = data[cursor + 8 : cursor + 8 + length]
        if len(chunk) != length:
            raise ValueError("truncated track")
        cursor += 8 + length
        index = tick = 0
        running = None
        ended = False
        active: dict[tuple[int, int], deque[int]] = defaultdict(deque)
        while index < len(chunk):
            delta, index = _vlq(chunk, index)
            tick += delta
            if index == len(chunk):
                raise ValueError("missing event")
            status = chunk[index]
            if status >= 128:
                index += 1
            elif running is not None:
                status = running
            else:
                raise ValueError("missing running status")
            if status == 255:
                running = None
                if index == len(chunk):
                    raise ValueError("missing meta type")
                kind = chunk[index]
                size, index = _vlq(chunk, index + 1)
                payload = chunk[index : index + size]
                if len(payload) != size:
                    raise ValueError("truncated meta event")
                index += size
                if kind == 47:
                    if size or index != len(chunk):
                        raise ValueError("invalid end of track")
                    ended = True
                elif kind == 81:
                    if size != 3:
                        raise ValueError("invalid tempo")
                    context.append((tick, "tempo", str(int.from_bytes(payload, "big"))))
                elif kind == 88:
                    if size != 4 or payload[1] > 7:
                        raise ValueError("invalid meter")
                    context.append((tick, "meter", f"{payload[0]}/{2 ** payload[1]}"))
                elif kind == 89:
                    if size != 2:
                        raise ValueError("invalid key")
                    sf = int.from_bytes(payload[:1], "big", signed=True)
                    if not -7 <= sf <= 7 or payload[1] not in (0, 1):
                        raise ValueError("invalid key value")
                    context.append((tick, "key", f"{sf}:{payload[1]}"))
            elif status in (240, 247):
                running = None
                size, index = _vlq(chunk, index)
                if index + size > len(chunk):
                    raise ValueError("truncated sysex")
                index += size
            elif 128 <= status < 240:
                running = status
                size = 1 if status >> 4 in (12, 13) else 2
                payload = chunk[index : index + size]
                if len(payload) != size or any(x >= 128 for x in payload):
                    raise ValueError("invalid channel payload")
                index += size
                channel = status & 15
                if status >> 4 == 9 and payload[1] > 0:
                    active[channel, payload[0]].append(tick)
                elif status >> 4 == 8 or (status >> 4 == 9 and payload[1] == 0):
                    queue = active[channel, payload[0]]
                    if not queue:
                        raise ValueError("orphan note off")
                    onset = queue.popleft()
                    if tick <= onset:
                        raise ValueError("nonpositive note duration")
                    events.append((track, channel, payload[0], onset, tick - onset))
            else:
                raise ValueError("unsupported system event")
        if not ended or any(active.values()):
            raise ValueError("unterminated track/notes")
    if cursor != len(data):
        raise ValueError("trailing bytes")
    return _normalize(division, events, context)


def parse_mido(data: bytes) -> dict[str, Any]:
    midi = MidiFile(file=io.BytesIO(data))
    events = []
    context = []
    major = ["Cb", "Gb", "Db", "Ab", "Eb", "Bb", "F", "C", "G", "D", "A", "E", "B", "F#", "C#"]
    minor = [
        "Abm",
        "Ebm",
        "Bbm",
        "Fm",
        "Cm",
        "Gm",
        "Dm",
        "Am",
        "Em",
        "Bm",
        "F#m",
        "C#m",
        "G#m",
        "D#m",
        "A#m",
    ]
    for track, messages in enumerate(midi.tracks):
        tick = 0
        active: dict[tuple[int, int], deque[int]] = defaultdict(deque)
        for message in messages:
            tick += message.time
            if message.type == "note_on" and message.velocity:
                active[message.channel, message.note].append(tick)
            elif message.type in ("note_off", "note_on"):
                queue = active[message.channel, message.note]
                if not queue:
                    raise ValueError("orphan note off")
                onset = queue.popleft()
                events.append((track, message.channel, message.note, onset, tick - onset))
            elif message.type == "set_tempo":
                context.append((tick, "tempo", str(message.tempo)))
            elif message.type == "time_signature":
                context.append((tick, "meter", f"{message.numerator}/{message.denominator}"))
            elif message.type == "key_signature":
                values, mode = (minor, 1) if message.key.endswith("m") else (major, 0)
                context.append((tick, "key", f"{values.index(message.key) - 7}:{mode}"))
        if any(active.values()):
            raise ValueError("unterminated notes")
    return _normalize(midi.ticks_per_beat, events, context)
