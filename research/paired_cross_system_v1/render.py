"""Declared Diatony renderer, independent from the byte/event relation checker."""

from __future__ import annotations

import io
from fractions import Fraction
from typing import Any

from mido import Message, MetaMessage, MidiFile, MidiTrack

from .contract import VOICES


def render(request: dict[str, Any], events: list[list[Any]]) -> bytes:
    midi = MidiFile(type=1, ticks_per_beat=480)
    midi.tracks.append(
        MidiTrack(
            [
                MetaMessage("key_signature", key=request["key"]),
                MetaMessage("time_signature", numerator=4, denominator=4),
                MetaMessage("set_tempo", tempo=round(60_000_000 / request["tempo_bpm"])),
                MetaMessage("end_of_track"),
            ]
        )
    )
    for channel, voice in enumerate(VOICES):
        track = MidiTrack([MetaMessage("track_name", name=voice)])
        timed = []
        for v, p, a, d in events:
            if v != voice:
                continue
            start, end = Fraction(a) * 480, (Fraction(a) + Fraction(d)) * 480
            if start.denominator != 1 or end.denominator != 1:
                raise ValueError("unsupported MIDI time grid")
            timed.extend(
                [
                    (int(start), 1, Message("note_on", channel=channel, note=p, velocity=64)),
                    (int(end), 0, Message("note_off", channel=channel, note=p, velocity=0)),
                ]
            )
        cursor = 0
        for tick, _, message in sorted(timed, key=lambda row: row[:2]):
            track.append(message.copy(time=tick - cursor))
            cursor = tick
        track.append(MetaMessage("end_of_track"))
        midi.tracks.append(track)
    output = io.BytesIO()
    midi.save(file=output)
    return output.getvalue()
