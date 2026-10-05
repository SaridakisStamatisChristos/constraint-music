"""Canonical delivery projections and independent MIDI parse-back checking."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from pathlib import Path

from mido import MidiFile

from .models import GenerationResult, RhythmState
from .satb import SatbGenerationResult
from .theory import Key

TICKS_PER_BEAT = 480


class RenderProfile(StrEnum):
    CERTIFIED_SATB = "certified-satb"
    MELODY_PLUS_SATB = "melody-plus-satb"
    LEGACY_PREVIEW = "legacy-preview"

    @classmethod
    def parse(cls, value: str | RenderProfile) -> RenderProfile:
        return value if isinstance(value, cls) else cls(value)


@dataclass(frozen=True, order=True, slots=True)
class NoteEvent:
    voice: str
    channel: int
    pitch: int
    onset_tick: int
    duration_ticks: int


@dataclass(frozen=True, order=True, slots=True)
class ContextEvent:
    """A delivery-level tempo, meter, or tonal-context declaration."""

    onset_tick: int
    kind: str
    value: str


@dataclass(frozen=True, slots=True)
class DeliveryReport:
    accepted: bool
    profile: RenderProfile
    expected_events: tuple[NoteEvent, ...]
    observed_events: tuple[NoteEvent, ...]
    issues: tuple[str, ...] = ()


_SATB_VOICES = (
    ("Soprano", 0, "soprano"),
    ("Alto", 1, "alto"),
    ("Tenor", 2, "tenor"),
    ("Bass", 3, "bass"),
)


def project_result(
    result: GenerationResult, profile: str | RenderProfile
) -> tuple[NoteEvent, ...]:
    selected = RenderProfile.parse(profile)
    events: list[NoteEvent] = []
    if selected in {RenderProfile.CERTIFIED_SATB, RenderProfile.MELODY_PLUS_SATB}:
        if not isinstance(result, SatbGenerationResult):
            raise ValueError(f"{selected.value} requires a complete SatbGenerationResult")
        for voice, channel, attribute in _SATB_VOICES:
            pitches = getattr(result, attribute)
            if len(pitches) != result.spec.total_beats:
                raise ValueError(f"{voice} projection does not match total_beats")
            events.extend(
                NoteEvent(voice, channel, pitch, beat * TICKS_PER_BEAT, TICKS_PER_BEAT)
                for beat, pitch in enumerate(pitches)
            )
    if selected in {RenderProfile.MELODY_PLUS_SATB, RenderProfile.LEGACY_PREVIEW}:
        events.extend(_melody_projection(result, channel=4 if events else 0))
    return tuple(sorted(events))


def expected_context_events(result: GenerationResult) -> tuple[ContextEvent, ...]:
    events = [
        ContextEvent(0, "tempo", str(round(60_000_000 / result.spec.tempo_bpm))),
        ContextEvent(0, "meter", f"{result.spec.beats_per_bar}/4"),
        ContextEvent(0, "key", _mido_key(result.spec.tonal_key)),
    ]
    if result.spec.modulation_enabled:
        destination = result.spec.modulation_destination
        boundary = result.spec.modulation_boundary_beat
        if destination is None or boundary is None:
            raise ValueError("enabled modulation requires destination and boundary")
        events.append(
            ContextEvent(boundary * TICKS_PER_BEAT, "key", _mido_key(destination))
        )
    return tuple(sorted(events))


def parse_midi_projection(
    path: str | Path, profile: str | RenderProfile
) -> tuple[tuple[NoteEvent, ...], tuple[ContextEvent, ...], tuple[str, ...]]:
    selected = RenderProfile.parse(profile)
    midi = MidiFile(path)
    issues: list[str] = []
    if midi.ticks_per_beat != TICKS_PER_BEAT:
        issues.append(
            f"ticks_per_beat mismatch: expected {TICKS_PER_BEAT}, got {midi.ticks_per_beat}"
        )

    allowed_tracks = {
        RenderProfile.CERTIFIED_SATB: {item[0] for item in _SATB_VOICES},
        RenderProfile.MELODY_PLUS_SATB: {item[0] for item in _SATB_VOICES} | {"Melody"},
        RenderProfile.LEGACY_PREVIEW: {"Melody"},
    }[selected]
    seen_tracks: set[str] = set()
    events: list[NoteEvent] = []
    context_events: list[ContextEvent] = []

    for track_index, track in enumerate(midi.tracks):
        track_names = [message.name for message in track if message.type == "track_name"]
        if len(track_names) > 1:
            issues.append(f"track {track_index}: multiple track-name declarations")
        track_name = track_names[0] if track_names else ""
        if track_name in allowed_tracks:
            if track_name in seen_tracks:
                issues.append(f"duplicate voice track {track_name!r}")
            seen_tracks.add(track_name)

        absolute = 0
        active: dict[tuple[int, int], list[int]] = defaultdict(list)
        unexpected_notes_reported = False
        for message in track:
            absolute += message.time
            if message.type == "track_name":
                continue
            if message.type == "key_signature":
                context_events.append(ContextEvent(absolute, "key", message.key))
                continue
            if message.type == "set_tempo":
                context_events.append(ContextEvent(absolute, "tempo", str(message.tempo)))
                continue
            if message.type == "time_signature":
                context_events.append(
                    ContextEvent(
                        absolute,
                        "meter",
                        f"{message.numerator}/{message.denominator}",
                    )
                )
                continue
            if track_name not in allowed_tracks:
                if message.type in {"note_on", "note_off"} and not unexpected_notes_reported:
                    label = track_name or f"<unnamed:{track_index}>"
                    issues.append(f"unexpected note events on track {label!r}")
                    unexpected_notes_reported = True
                continue
            if message.type == "note_on" and message.velocity > 0:
                key = (message.channel, message.note)
                if active[key]:
                    issues.append(
                        f"{track_name}: overlapping note-on for channel {key[0]} "
                        f"pitch {key[1]}"
                    )
                active[key].append(absolute)
            elif message.type == "note_off" or (
                message.type == "note_on" and message.velocity == 0
            ):
                key = (message.channel, message.note)
                if not active[key]:
                    issues.append(
                        f"{track_name}: unmatched note-off for channel {key[0]} pitch {key[1]}"
                    )
                    continue
                onset = active[key].pop(0)
                events.append(
                    NoteEvent(track_name, key[0], key[1], onset, absolute - onset)
                )
        if track_name in allowed_tracks:
            for (channel, pitch), onsets in active.items():
                for onset in onsets:
                    issues.append(
                        f"{track_name}: unterminated note channel {channel} "
                        f"pitch {pitch} at {onset}"
                    )

    missing = sorted(allowed_tracks - seen_tracks)
    if missing:
        issues.append("missing voice tracks: " + ", ".join(missing))
    return tuple(sorted(events)), tuple(sorted(context_events)), tuple(issues)


def verify_delivery(
    result: GenerationResult,
    path: str | Path,
    profile: str | RenderProfile = RenderProfile.CERTIFIED_SATB,
) -> DeliveryReport:
    selected = RenderProfile.parse(profile)
    expected = project_result(result, selected)
    observed, observed_context, parse_issues = parse_midi_projection(path, selected)
    issues = list(parse_issues)
    if observed != expected:
        missing = sorted(set(expected) - set(observed))
        extra = sorted(set(observed) - set(expected))
        if missing:
            issues.append(f"missing/changed projected note events: {missing[:8]!r}")
        if extra:
            issues.append(f"extra/changed projected note events: {extra[:8]!r}")
        if not missing and not extra:
            issues.append("projected note-event multiplicity or ordering mismatch")
    expected_context = expected_context_events(result)
    if observed_context != expected_context:
        issues.append(
            "delivery context events mismatch: "
            f"expected {expected_context!r}, got {observed_context!r}"
        )
    return DeliveryReport(not issues, selected, expected, observed, tuple(issues))


def output_digest(path: str | Path) -> str:
    return sha256(Path(path).read_bytes()).hexdigest()


def _melody_projection(result: GenerationResult, channel: int) -> tuple[NoteEvent, ...]:
    rhythm = result.effective_rhythm
    step_ticks = TICKS_PER_BEAT // result.spec.subdivisions_per_beat
    events: list[NoteEvent] = []
    step = 0
    while step < len(result.melody):
        state = rhythm[step]
        if state is not RhythmState.ONSET:
            step += 1
            continue
        end = step + 1
        while end < len(rhythm) and rhythm[end] is RhythmState.TIE:
            end += 1
        events.append(
            NoteEvent(
                "Melody",
                channel,
                result.melody[step],
                step * step_ticks,
                (end - step) * step_ticks,
            )
        )
        step = end
    return tuple(events)


def _mido_key(key: Key) -> str:
    display = key.tonic[0] + key.tonic[1:].replace("B", "b")
    return display if key.mode.value == "major" else display + "m"
