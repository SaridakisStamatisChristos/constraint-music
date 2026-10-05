"""Standard-library-only oracle for the certified MIDI delivery boundary.

This module parses Standard MIDI Files directly from bytes.  It intentionally
does not use mido or any constraint_music code, so exporter and production
parse-back defects cannot silently redefine the expected delivery relation.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from hashlib import sha256

TICKS_PER_BEAT = 480

_MAJOR_KEYS = (
    "Cb",
    "Gb",
    "Db",
    "Ab",
    "Eb",
    "Bb",
    "F",
    "C",
    "G",
    "D",
    "A",
    "E",
    "B",
    "F#",
    "C#",
)
_MINOR_KEYS = (
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
)


@dataclass(frozen=True, order=True, slots=True)
class OracleNoteEvent:
    voice: str
    channel: int
    pitch: int
    onset_tick: int
    duration_ticks: int


@dataclass(frozen=True, order=True, slots=True)
class OracleContextEvent:
    onset_tick: int
    kind: str
    value: str


@dataclass(frozen=True, slots=True)
class OracleMidi:
    format_type: int
    ticks_per_beat: int
    note_events: tuple[OracleNoteEvent, ...]
    context_events: tuple[OracleContextEvent, ...]
    track_names: tuple[str, ...]
    issues: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DeliveryDecision:
    accepted: bool
    observed: OracleMidi | None
    issues: tuple[str, ...]
    output_sha256: str


class MidiParseError(ValueError):
    """The byte stream is not a structurally readable Standard MIDI File."""


class _Cursor:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.position = 0

    @property
    def remaining(self) -> int:
        return len(self.data) - self.position

    def read(self, length: int) -> bytes:
        if length < 0 or length > self.remaining:
            raise MidiParseError("unexpected end of MIDI data")
        start = self.position
        self.position += length
        return self.data[start : self.position]

    def byte(self) -> int:
        return self.read(1)[0]

    def uint16(self) -> int:
        return int.from_bytes(self.read(2), "big")

    def uint32(self) -> int:
        return int.from_bytes(self.read(4), "big")

    def vlq(self) -> int:
        value = 0
        for _ in range(4):
            current = self.byte()
            value = (value << 7) | (current & 0x7F)
            if current < 0x80:
                return value
        raise MidiParseError("variable-length quantity exceeds four bytes")


@dataclass(frozen=True, slots=True)
class _ChannelMessage:
    tick: int
    status: int
    data: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class _Track:
    names: tuple[str, ...]
    channel_messages: tuple[_ChannelMessage, ...]
    context_events: tuple[OracleContextEvent, ...]


def parse_midi_bytes(data: bytes, *, allowed_tracks: tuple[str, ...]) -> OracleMidi:
    """Parse note/context events without depending on the production MIDI stack."""

    cursor = _Cursor(data)
    if cursor.read(4) != b"MThd":
        raise MidiParseError("missing MThd header")
    header_length = cursor.uint32()
    if header_length < 6:
        raise MidiParseError("MIDI header is shorter than six bytes")
    header = _Cursor(cursor.read(header_length))
    format_type = header.uint16()
    track_count = header.uint16()
    division = header.uint16()
    if format_type not in {0, 1, 2}:
        raise MidiParseError(f"unsupported MIDI format {format_type}")
    if division & 0x8000:
        raise MidiParseError("SMPTE time division is outside the delivery contract")

    tracks: list[_Track] = []
    for _ in range(track_count):
        if cursor.read(4) != b"MTrk":
            raise MidiParseError("missing MTrk chunk")
        tracks.append(_parse_track(cursor.read(cursor.uint32())))
    if cursor.remaining:
        raise MidiParseError("trailing bytes follow declared MIDI tracks")

    allowed = set(allowed_tracks)
    seen: set[str] = set()
    all_names: list[str] = []
    note_events: list[OracleNoteEvent] = []
    context_events: list[OracleContextEvent] = []
    issues: list[str] = []
    for track_index, track in enumerate(tracks):
        all_names.extend(track.names)
        if len(track.names) > 1:
            issues.append(f"track {track_index}: multiple track-name declarations")
        name = track.names[0] if track.names else ""
        if name in allowed:
            if name in seen:
                issues.append(f"duplicate voice track {name!r}")
            seen.add(name)
        context_events.extend(track.context_events)

        active: dict[tuple[int, int], list[int]] = defaultdict(list)
        unexpected_reported = False
        for message in track.channel_messages:
            kind = message.status & 0xF0
            if kind not in {0x80, 0x90}:
                continue
            channel = message.status & 0x0F
            pitch = message.data[0]
            velocity = message.data[1]
            if name not in allowed:
                if not unexpected_reported:
                    label = name or f"<unnamed:{track_index}>"
                    issues.append(f"unexpected note events on track {label!r}")
                    unexpected_reported = True
                continue
            key = (channel, pitch)
            if kind == 0x90 and velocity > 0:
                if active[key]:
                    issues.append(
                        f"{name}: overlapping note-on for channel {channel} pitch {pitch}"
                    )
                active[key].append(message.tick)
                continue
            if not active[key]:
                issues.append(
                    f"{name}: unmatched note-off for channel {channel} pitch {pitch}"
                )
                continue
            onset = active[key].pop(0)
            note_events.append(
                OracleNoteEvent(name, channel, pitch, onset, message.tick - onset)
            )
        if name in allowed:
            for (channel, pitch), onsets in active.items():
                for onset in onsets:
                    issues.append(
                        f"{name}: unterminated note channel {channel} pitch {pitch} at {onset}"
                    )

    missing = sorted(allowed - seen)
    if missing:
        issues.append("missing voice tracks: " + ", ".join(missing))
    return OracleMidi(
        format_type,
        division,
        tuple(sorted(note_events)),
        tuple(sorted(context_events)),
        tuple(all_names),
        tuple(issues),
    )


def adjudicate_delivery(
    data: bytes,
    *,
    allowed_tracks: tuple[str, ...],
    expected_events: tuple[OracleNoteEvent, ...],
    expected_context: tuple[OracleContextEvent, ...],
    ticks_per_beat: int = TICKS_PER_BEAT,
) -> DeliveryDecision:
    digest = sha256(data).hexdigest()
    try:
        observed = parse_midi_bytes(data, allowed_tracks=allowed_tracks)
    except MidiParseError as exc:
        return DeliveryDecision(False, None, (str(exc),), digest)
    issues = list(observed.issues)
    if observed.ticks_per_beat != ticks_per_beat:
        issues.append(
            f"ticks_per_beat mismatch: expected {ticks_per_beat}, "
            f"got {observed.ticks_per_beat}"
        )
    if observed.note_events != tuple(sorted(expected_events)):
        issues.append("delivered note events do not equal the independent projection")
    if observed.context_events != tuple(sorted(expected_context)):
        issues.append("delivered context events do not equal the independent projection")
    return DeliveryDecision(not issues, observed, tuple(issues), digest)


def project_satb(
    soprano: tuple[int, ...],
    alto: tuple[int, ...],
    tenor: tuple[int, ...],
    bass: tuple[int, ...],
) -> tuple[OracleNoteEvent, ...]:
    lengths = {len(soprano), len(alto), len(tenor), len(bass)}
    if len(lengths) != 1:
        raise ValueError("SATB voices must have equal lengths")
    events: list[OracleNoteEvent] = []
    for name, channel, pitches in (
        ("Soprano", 0, soprano),
        ("Alto", 1, alto),
        ("Tenor", 2, tenor),
        ("Bass", 3, bass),
    ):
        events.extend(
            OracleNoteEvent(name, channel, pitch, beat * TICKS_PER_BEAT, TICKS_PER_BEAT)
            for beat, pitch in enumerate(pitches)
        )
    return tuple(sorted(events))


def project_melody(
    melody: tuple[int, ...],
    rhythm: tuple[str, ...],
    *,
    subdivisions_per_beat: int,
    channel: int,
) -> tuple[OracleNoteEvent, ...]:
    if len(melody) != len(rhythm):
        raise ValueError("melody and rhythm must have equal lengths")
    if subdivisions_per_beat < 1 or TICKS_PER_BEAT % subdivisions_per_beat:
        raise ValueError("subdivision must divide 480 ticks exactly")
    step_ticks = TICKS_PER_BEAT // subdivisions_per_beat
    events: list[OracleNoteEvent] = []
    step = 0
    while step < len(melody):
        if rhythm[step] != "onset":
            step += 1
            continue
        end = step + 1
        while end < len(rhythm) and rhythm[end] == "tie":
            end += 1
        events.append(
            OracleNoteEvent(
                "Melody",
                channel,
                melody[step],
                step * step_ticks,
                (end - step) * step_ticks,
            )
        )
        step = end
    return tuple(events)


def project_context(
    *,
    tempo_bpm: int,
    beats_per_bar: int,
    initial_key: str,
    destination_key: str | None = None,
    modulation_boundary_beat: int | None = None,
) -> tuple[OracleContextEvent, ...]:
    events = [
        OracleContextEvent(0, "tempo", str(round(60_000_000 / tempo_bpm))),
        OracleContextEvent(0, "meter", f"{beats_per_bar}/4"),
        OracleContextEvent(0, "key", initial_key),
    ]
    if destination_key is not None:
        if modulation_boundary_beat is None:
            raise ValueError("destination key requires a modulation boundary")
        events.append(
            OracleContextEvent(
                modulation_boundary_beat * TICKS_PER_BEAT,
                "key",
                destination_key,
            )
        )
    return tuple(sorted(events))


def _parse_track(data: bytes) -> _Track:
    cursor = _Cursor(data)
    tick = 0
    running_status: int | None = None
    names: list[str] = []
    messages: list[_ChannelMessage] = []
    contexts: list[OracleContextEvent] = []
    while cursor.remaining:
        tick += cursor.vlq()
        first = cursor.byte()
        first_data: int | None = None
        if first < 0x80:
            if running_status is None:
                raise MidiParseError("running status appears before channel status")
            status = running_status
            first_data = first
        else:
            status = first

        if status == 0xFF:
            running_status = None
            meta_type = cursor.byte()
            payload = cursor.read(cursor.vlq())
            if meta_type == 0x03:
                try:
                    names.append(payload.decode("utf-8"))
                except UnicodeDecodeError as exc:
                    raise MidiParseError("track name is not UTF-8") from exc
            elif meta_type == 0x51:
                if len(payload) != 3:
                    raise MidiParseError("tempo meta event must contain three bytes")
                contexts.append(
                    OracleContextEvent(tick, "tempo", str(int.from_bytes(payload, "big")))
                )
            elif meta_type == 0x58:
                if len(payload) != 4:
                    raise MidiParseError("time-signature event must contain four bytes")
                contexts.append(
                    OracleContextEvent(tick, "meter", f"{payload[0]}/{1 << payload[1]}")
                )
            elif meta_type == 0x59:
                contexts.append(OracleContextEvent(tick, "key", _decode_key(payload)))
            continue
        if status in {0xF0, 0xF7}:
            running_status = None
            cursor.read(cursor.vlq())
            continue
        if not 0x80 <= status <= 0xEF:
            raise MidiParseError(f"unsupported system status 0x{status:02x}")
        running_status = status
        width = 1 if status & 0xF0 in {0xC0, 0xD0} else 2
        payload = (() if first_data is None else (first_data,)) + tuple(
            cursor.byte() for _ in range(width - (first_data is not None))
        )
        if any(value >= 0x80 for value in payload):
            raise MidiParseError("channel message contains a non-data byte")
        messages.append(_ChannelMessage(tick, status, payload))
    return _Track(tuple(names), tuple(messages), tuple(contexts))


def _decode_key(payload: bytes) -> str:
    if len(payload) != 2:
        raise MidiParseError("key-signature event must contain two bytes")
    sharps = int.from_bytes(payload[:1], "big", signed=True)
    if not -7 <= sharps <= 7 or payload[1] not in {0, 1}:
        raise MidiParseError("key-signature payload is outside the SMF domain")
    names = _MINOR_KEYS if payload[1] else _MAJOR_KEYS
    return names[sharps + 7]
