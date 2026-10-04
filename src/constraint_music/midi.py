from __future__ import annotations

from collections.abc import Iterable
from os import replace as atomic_replace
from pathlib import Path
from tempfile import NamedTemporaryFile

from mido import Message, MetaMessage, MidiFile, MidiTrack, bpm2tempo

from .delivery import TICKS_PER_BEAT, RenderProfile, verify_delivery
from .models import GenerationResult, RhythmState
from .satb import SatbGenerationResult


def write_midi(
    result: GenerationResult,
    path: str | Path,
    *,
    profile: str | RenderProfile | None = None,
) -> Path:
    selected = (
        RenderProfile.CERTIFIED_SATB
        if profile is None and isinstance(result, SatbGenerationResult)
        else RenderProfile.LEGACY_PREVIEW
        if profile is None
        else RenderProfile.parse(profile)
    )
    satb_profile = selected in {
        RenderProfile.CERTIFIED_SATB,
        RenderProfile.MELODY_PLUS_SATB,
    }
    if satb_profile and not isinstance(result, SatbGenerationResult):
        raise ValueError(f"{selected.value} requires complete SATB voices")
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    midi = MidiFile(type=1, ticks_per_beat=TICKS_PER_BEAT)
    _add_conductor_track(midi, result)
    if selected in {RenderProfile.CERTIFIED_SATB, RenderProfile.MELODY_PLUS_SATB}:
        assert isinstance(result, SatbGenerationResult)
        _add_satb_track(midi, "Soprano", 0, 52, result.soprano, result)
        _add_satb_track(midi, "Alto", 1, 48, result.alto, result)
        _add_satb_track(midi, "Tenor", 2, 42, result.tenor, result)
        _add_satb_track(midi, "Bass", 3, 43, result.bass, result)
        if selected is RenderProfile.MELODY_PLUS_SATB:
            _add_melody_track(midi, result, channel=4)
    else:
        _add_melody_track(midi, result)
        _add_bass_track(midi, result)
        _add_harmony_track(midi, result)
    midi.save(destination)
    return destination


def write_certified_midi(
    result: GenerationResult,
    path: str | Path,
    *,
    profile: str | RenderProfile = RenderProfile.CERTIFIED_SATB,
) -> Path:
    """Atomically publish MIDI only after independent parse-back equality."""

    selected = RenderProfile.parse(profile)
    if selected is RenderProfile.LEGACY_PREVIEW:
        raise ValueError("legacy-preview is not a certifying render profile")
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        prefix=f".{destination.stem}.", suffix=".mid", dir=destination.parent, delete=False
    ) as handle:
        temporary = Path(handle.name)
    try:
        write_midi(result, temporary, profile=selected)
        report = verify_delivery(result, temporary, selected)
        if not report.accepted:
            raise ValueError("MIDI delivery certification failed: " + "; ".join(report.issues))
        atomic_replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def _add_conductor_track(midi: MidiFile, result: GenerationResult) -> None:
    track = MidiTrack()
    midi.tracks.append(track)
    spec = result.spec
    track.append(MetaMessage("track_name", name="Constraint Music", time=0))
    track.append(MetaMessage("set_tempo", tempo=bpm2tempo(spec.tempo_bpm), time=0))
    track.append(
        MetaMessage(
            "time_signature",
            numerator=spec.beats_per_bar,
            denominator=4,
            time=0,
        )
    )
    track.append(MetaMessage("key_signature", key=_mido_key(result), time=0))
    if result.spec.modulation_enabled:
        destination = result.spec.modulation_destination
        boundary = result.spec.modulation_boundary_beat
        if destination is None or boundary is None:
            raise ValueError("enabled modulation requires destination and boundary")
        display = destination.tonic[0] + destination.tonic[1:].replace("B", "b")
        key_name = display if destination.mode.value == "major" else display + "m"
        track.append(
            MetaMessage(
                "key_signature",
                key=key_name,
                time=boundary * TICKS_PER_BEAT,
            )
        )
    track.append(MetaMessage("end_of_track", time=0))


def _add_melody_track(
    midi: MidiFile, result: GenerationResult, *, channel: int = 0
) -> None:
    track = MidiTrack()
    midi.tracks.append(track)
    track.append(MetaMessage("track_name", name="Melody", time=0))
    track.append(Message("program_change", channel=channel, program=0, time=0))
    step_ticks = TICKS_PER_BEAT // result.spec.subdivisions_per_beat
    rhythm = result.effective_rhythm
    events: list[tuple[int, int, Message]] = []
    step = 0
    while step < len(result.melody):
        state = rhythm[step]
        if state != RhythmState.ONSET:
            step += 1
            continue
        end_step = step + 1
        while end_step < len(rhythm) and rhythm[end_step] == RhythmState.TIE:
            end_step += 1
        note = result.melody[step]
        start = step * step_ticks
        end = end_step * step_ticks
        beat = step // result.spec.subdivisions_per_beat
        accent = 12 if beat % result.spec.beats_per_bar == 0 else 0
        velocity = min(112, 78 + accent + result.actual_tension[beat] // 10)
        events.append(
            (start, 1, Message("note_on", note=note, velocity=velocity, channel=channel, time=0))
        )
        events.append(
            (end, 0, Message("note_off", note=note, velocity=0, channel=channel, time=0))
        )
        step = end_step
    _append_absolute_events(track, events)


def _add_satb_track(
    midi: MidiFile,
    name: str,
    channel: int,
    program: int,
    pitches: tuple[int, ...],
    result: GenerationResult,
) -> None:
    track = MidiTrack()
    midi.tracks.append(track)
    track.append(MetaMessage("track_name", name=name, time=0))
    track.append(Message("program_change", channel=channel, program=program, time=0))
    events: list[tuple[int, int, Message]] = []
    for beat, pitch in enumerate(pitches):
        start = beat * TICKS_PER_BEAT
        end = (beat + 1) * TICKS_PER_BEAT
        velocity = 72 + (8 if beat % result.spec.beats_per_bar == 0 else 0)
        events.append(
            (start, 1, Message("note_on", note=pitch, velocity=velocity, channel=channel, time=0))
        )
        events.append(
            (end, 0, Message("note_off", note=pitch, velocity=0, channel=channel, time=0))
        )
    _append_absolute_events(track, events)


def _add_bass_track(midi: MidiFile, result: GenerationResult) -> None:
    track = MidiTrack()
    midi.tracks.append(track)
    track.append(MetaMessage("track_name", name="Bass", time=0))
    track.append(Message("program_change", channel=1, program=32, time=0))
    events: list[tuple[int, int, Message]] = []
    for beat, note in enumerate(result.bass):
        start = beat * TICKS_PER_BEAT
        end = (beat + 1) * TICKS_PER_BEAT
        velocity = 78 + (8 if beat % result.spec.beats_per_bar == 0 else 0)
        events.append(
            (start, 1, Message("note_on", note=note, velocity=velocity, channel=1, time=0))
        )
        events.append((end, 0, Message("note_off", note=note, velocity=0, channel=1, time=0)))
    _append_absolute_events(track, events)


def _add_harmony_track(midi: MidiFile, result: GenerationResult) -> None:
    track = MidiTrack()
    midi.tracks.append(track)
    track.append(MetaMessage("track_name", name="Harmony", time=0))
    track.append(Message("program_change", channel=2, program=48, time=0))
    key = result.spec.tonal_key
    events: list[tuple[int, int, Message]] = []
    for beat, degree in enumerate(result.chord_degrees):
        start = beat * TICKS_PER_BEAT
        end = (beat + 1) * TICKS_PER_BEAT
        notes = _closed_voicing(key.triad_pitch_classes(degree), low=55, high=74)
        velocity = 42 + result.actual_tension[beat] // 7
        for note in notes:
            events.append(
                (start, 1, Message("note_on", note=note, velocity=velocity, channel=2, time=0))
            )
            events.append((end, 0, Message("note_off", note=note, velocity=0, channel=2, time=0)))
    _append_absolute_events(track, events)


def _closed_voicing(pitch_classes: Iterable[int], low: int, high: int) -> tuple[int, ...]:
    output: list[int] = []
    cursor = low
    for pitch_class in pitch_classes:
        candidates = [note for note in range(cursor, high + 1) if note % 12 == pitch_class]
        if not candidates:
            candidates = [note for note in range(low, high + 1) if note % 12 == pitch_class]
        note = min(candidates, key=lambda value: abs(value - cursor))
        output.append(note)
        cursor = note + 1
    return tuple(output)


def _append_absolute_events(track: MidiTrack, events: list[tuple[int, int, Message]]) -> None:
    previous_tick = 0
    for tick, _priority, message in sorted(
        events, key=lambda item: (item[0], item[1], item[2].note)
    ):
        message.time = tick - previous_tick
        track.append(message)
        previous_tick = tick
    track.append(MetaMessage("end_of_track", time=0))


def _mido_key(result: GenerationResult) -> str:
    tonic = result.spec.tonal_key.tonic
    display = tonic[0] + tonic[1:].replace("B", "b")
    return display if result.spec.mode.value == "major" else display + "m"
