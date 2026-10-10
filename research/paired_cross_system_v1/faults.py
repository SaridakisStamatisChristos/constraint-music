"""Predeclared, deterministic, boundary-specific mutations with no-op eligibility."""

from __future__ import annotations

import copy
import io
from typing import Any

from mido import MidiFile

from .contract import KEYS, content_hash
from .render import render

FAULTS = (
    "request_key",
    "request_tempo",
    "coordinated_request",
    "chromatic_pitch",
    "missing_triad",
    "crossing",
    "artifact_duration",
    "midi_pitch",
    "midi_duration",
    "midi_channel",
    "midi_tempo",
    "midi_truncated",
)


def scaled(data: bytes) -> bytes:
    midi = MidiFile(file=io.BytesIO(data))
    midi.ticks_per_beat *= 2
    for track in midi.tracks:
        for message in track:
            message.time *= 2
    output = io.BytesIO()
    midi.save(file=output)
    return output.getvalue()


def mutate(name: str, artifact: dict[str, Any], data: bytes) -> tuple[dict[str, Any], bytes]:
    original_data = data
    changed = copy.deepcopy(artifact)
    request, events = changed["request"], changed["events"]
    if name in ("request_key", "coordinated_request"):
        old = request["key"]
        request["key"] = "G" if old != "G" else "C"
        if name == "coordinated_request":
            shift = KEYS[request["key"]][0] - KEYS[old][0]
            for event in events:
                event[1] += shift
            changed["events_sha256"] = content_hash(events)
            data = render(request, events)
    elif name == "request_tempo":
        request["tempo_bpm"] = 90 if request["tempo_bpm"] != 90 else 120
    elif name in ("chromatic_pitch", "missing_triad", "crossing", "artifact_duration"):
        if name == "chromatic_pitch":
            tonic = KEYS[request["key"]][0]
            scale = {(tonic + p) % 12 for p in (0, 2, 4, 5, 7, 9, 11)}
            candidate = next(p for p in range(128) if p % 12 not in scale)
            events[0][1] = candidate
        elif name == "missing_triad":
            bass = next(e[1] for e in events if e[0] == "Bass" and e[2] == "0")
            for event in events:
                if int(event[2]) < 4:
                    event[1] = bass
        elif name == "crossing":
            bass = next(e[1] for e in events if e[0] == "Bass" and e[2] == "0")
            for event in events:
                if event[0] == "Soprano" and int(event[2]) < 4:
                    event[1] = bass - 12
        else:
            events[0][3] = "3" if events[0][3] == "4" else "2"
        # Repair integrity to require actual semantic reconstruction.
        changed["events_sha256"] = content_hash(events)
        data = render(request, events)
    elif name == "midi_truncated":
        data = data[:-3]
    else:
        midi = MidiFile(file=io.BytesIO(data))
        if name == "midi_tempo":
            next(m for track in midi.tracks for m in track if m.type == "set_tempo").tempo += 1
        elif name == "midi_duration":
            next(m for m in midi.tracks[1] if m.type == "note_off" and m.time > 0).time -= 1
        elif name == "midi_channel":
            for message in midi.tracks[1]:
                if message.type in ("note_on", "note_off"):
                    message.channel = (message.channel + 1) % 16
        elif name == "midi_pitch":
            messages = [m for m in midi.tracks[1] if m.type in ("note_on", "note_off")]
            pitch = messages[0].note
            # Mutate all matching on/off pairs in this voice; exact relation still fails.
            for message in messages:
                if message.note == pitch:
                    message.note += 1
        else:
            raise ValueError("unknown fault")
        output = io.BytesIO()
        midi.save(file=output)
        data = output.getvalue()
    if changed == artifact and data == original_data:
        raise ValueError("no-op mutation")
    return changed, data
