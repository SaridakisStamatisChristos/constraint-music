"""Atomic native MIDI export with request binding and independent parse-back."""

from __future__ import annotations

from collections import Counter
from io import BytesIO
from os import replace
from pathlib import Path
from tempfile import NamedTemporaryFile

from mido import Message, MetaMessage, MidiFile, MidiTrack, bpm2tempo

from .models import VOICES, HarmonizationRequest, HarmonizationResult
from .verifier import verify_harmonization

TICKS = 480


def verify_midi(request: HarmonizationRequest, rows: object, data: bytes) -> tuple[str, ...]:
    issues = verify_harmonization(request, rows)
    if issues:
        return issues
    assert isinstance(rows, (list, tuple))
    try:
        # mido accepts bytes after the declared tracks. Require an exact SMF
        # envelope before note reconstruction, rather than ignoring extra data.
        if data[:4] != b"MThd" or data[4:8] != (6).to_bytes(4, "big"):
            return ("MIDI_HEADER",)
        cursor = 14
        for _ in range(5):
            if data[cursor : cursor + 4] != b"MTrk":
                return ("MIDI_TRACK_CHUNK",)
            size = int.from_bytes(data[cursor + 4 : cursor + 8], "big")
            cursor += 8 + size
            if cursor > len(data):
                return ("MIDI_TRACK_LENGTH",)
        if cursor != len(data):
            return ("MIDI_TRAILING_DATA",)
        midi = MidiFile(file=BytesIO(data))
        if midi.type != 1 or midi.ticks_per_beat != TICKS or len(midi.tracks) != 5:
            return ("MIDI_PROFILE",)
        if any(
            not track
            or track[-1].type != "end_of_track"
            or sum(m.type == "end_of_track" for m in track) != 1
            for track in midi.tracks
        ):
            return ("MIDI_END_OF_TRACK",)
        contexts = []
        elapsed = 0
        for message in midi.tracks[0]:
            elapsed += message.time
            if message.type in ("set_tempo", "time_signature", "key_signature"):
                contexts.append((elapsed, message))
            elif message.type not in ("track_name", "end_of_track"):
                return ("MIDI_CONDUCTOR_EVENT",)
        if elapsed != 0 or len(contexts) != 3 or any(t != 0 for t, _ in contexts):
            return ("MIDI_CONTEXT",)
        by_type = {m.type: m for _, m in contexts}
        if set(by_type) != {"set_tempo", "time_signature", "key_signature"}:
            return ("MIDI_CONTEXT",)
        if by_type["set_tempo"].tempo != bpm2tempo(request.tempo_bpm) or (
            by_type["time_signature"].numerator != request.beats_per_bar
            or by_type["time_signature"].denominator != 4
            or by_type["key_signature"].key != request.key
        ):
            return ("MIDI_CONTEXT",)
        actual: Counter[tuple[int, int, int, int]] = Counter()
        for voice, track in enumerate(midi.tracks[1:]):
            clock, names = 0, []
            active: dict[int, int] = {}
            for message in track:
                clock += message.time
                if message.type == "track_name":
                    names.append((clock, message.name))
                elif message.type in ("note_on", "note_off"):
                    if message.channel != voice:
                        return ("MIDI_VOICE",)
                    if message.type == "note_on" and message.velocity > 0:
                        if message.note in active:
                            return ("MIDI_OVERLAP",)
                        active[message.note] = clock
                    else:
                        if message.note not in active:
                            return ("MIDI_NOTE_PAIR",)
                        start = active.pop(message.note)
                        if clock <= start:
                            return ("MIDI_NOTE_DURATION",)
                        actual[voice, message.note, start, clock - start] += 1
                elif message.type == "program_change":
                    if message.channel != voice or clock != 0:
                        return ("MIDI_PROGRAM",)
                elif message.type != "end_of_track":
                    return ("MIDI_EXTRA_EVENT",)
            if active or names != [(0, VOICES[voice])] or clock != len(rows) * TICKS:
                return ("MIDI_VOICE_OR_UNTERMINATED_NOTE",)
        expected = Counter(
            (v, pitch, index * TICKS, TICKS)
            for index, row in enumerate(rows)
            for v, pitch in enumerate(row)
        )
        return () if actual == expected else ("MIDI_SCORE_RELATION",)
    except (ValueError, OSError, KeyError, IndexError, EOFError, TypeError):
        return ("MIDI_PARSE",)


def write_midi(result: HarmonizationResult, path: str | Path) -> Path:
    issues = verify_harmonization(result.request, result.rows)
    if issues:
        raise ValueError("Invalid harmonization: " + "; ".join(issues))
    midi = MidiFile(type=1, ticks_per_beat=TICKS)
    conductor = MidiTrack()
    midi.tracks.append(conductor)
    conductor.extend(
        [
            MetaMessage("track_name", name="Constraint Music request-bound SATB"),
            MetaMessage("set_tempo", tempo=bpm2tempo(result.request.tempo_bpm)),
            MetaMessage("time_signature", numerator=result.request.beats_per_bar, denominator=4),
            MetaMessage("key_signature", key=result.request.key),
            MetaMessage("end_of_track"),
        ]
    )
    for voice, name in enumerate(VOICES):
        track = MidiTrack()
        midi.tracks.append(track)
        track.append(MetaMessage("track_name", name=name))
        track.append(Message("program_change", channel=voice, program=(52, 48, 42, 43)[voice]))
        for row in result.rows:
            track.append(Message("note_on", channel=voice, note=row[voice], velocity=80))
            track.append(
                Message("note_off", channel=voice, note=row[voice], velocity=0, time=TICKS)
            )
        track.append(MetaMessage("end_of_track"))
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=destination.parent, suffix=".mid", delete=False) as handle:
        temporary = Path(handle.name)
    try:
        midi.save(temporary)
        problems = verify_midi(result.request, result.rows, temporary.read_bytes())
        if problems:
            raise ValueError("MIDI certification failed: " + "; ".join(problems))
        replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination
