from __future__ import annotations

from mido import Message, MetaMessage, MidiFile, MidiTrack

from constraint_music.delivery import RenderProfile, project_result, verify_delivery
from constraint_music.midi import write_midi
from constraint_music.models import GenerationResult


def test_certified_satb_round_trip_is_exact(
    tmp_path, solved_piece: GenerationResult
) -> None:
    path = write_midi(
        solved_piece,
        tmp_path / "certified.mid",
        profile=RenderProfile.CERTIFIED_SATB,
    )
    report = verify_delivery(solved_piece, path, RenderProfile.CERTIFIED_SATB)
    assert report.accepted, report.issues
    assert len(report.observed_events) == solved_piece.spec.total_beats * 4


def test_changed_delivered_pitch_is_rejected(
    tmp_path, solved_piece: GenerationResult
) -> None:
    path = write_midi(
        solved_piece,
        tmp_path / "tampered.mid",
        profile=RenderProfile.CERTIFIED_SATB,
    )
    midi = MidiFile(path)
    alto = next(track for track in midi.tracks if track.name == "Alto")
    note_on = next(message for message in alto if message.type == "note_on" and message.velocity)
    original = note_on.note
    note_on.note = original + 1
    note_off = next(
        message
        for message in alto
        if message.type == "note_off" and message.note == original
    )
    note_off.note = original + 1
    midi.save(path)
    report = verify_delivery(solved_piece, path, RenderProfile.CERTIFIED_SATB)
    assert not report.accepted
    assert any("projected note events" in issue for issue in report.issues)


def test_melody_plus_satb_round_trip_is_exact(
    tmp_path, solved_piece: GenerationResult
) -> None:
    path = write_midi(
        solved_piece,
        tmp_path / "combined.mid",
        profile=RenderProfile.MELODY_PLUS_SATB,
    )
    report = verify_delivery(solved_piece, path, RenderProfile.MELODY_PLUS_SATB)
    assert report.accepted, report.issues
    assert report.observed_events == project_result(
        solved_piece, RenderProfile.MELODY_PLUS_SATB
    )


def test_changed_note_duration_is_rejected(
    tmp_path, solved_piece: GenerationResult
) -> None:
    path = write_midi(
        solved_piece,
        tmp_path / "duration.mid",
        profile=RenderProfile.CERTIFIED_SATB,
    )
    midi = MidiFile(path)
    soprano = next(track for track in midi.tracks if track.name == "Soprano")
    first_note_off = next(message for message in soprano if message.type == "note_off")
    first_note_off.time += 1
    midi.save(path)
    report = verify_delivery(solved_piece, path, RenderProfile.CERTIFIED_SATB)
    assert not report.accepted
    assert any("projected note events" in issue for issue in report.issues)


def test_undeclared_note_track_is_rejected(
    tmp_path, solved_piece: GenerationResult
) -> None:
    path = write_midi(
        solved_piece,
        tmp_path / "extra-track.mid",
        profile=RenderProfile.CERTIFIED_SATB,
    )
    midi = MidiFile(path)
    track = MidiTrack(
        [
            MetaMessage("track_name", name="Undeclared", time=0),
            Message("note_on", note=60, velocity=64, channel=9, time=0),
            Message("note_off", note=60, velocity=0, channel=9, time=120),
        ]
    )
    midi.tracks.append(track)
    midi.save(path)
    report = verify_delivery(solved_piece, path, RenderProfile.CERTIFIED_SATB)
    assert not report.accepted
    assert any("unexpected note events" in issue for issue in report.issues)


def test_changed_tempo_is_rejected(tmp_path, solved_piece: GenerationResult) -> None:
    path = write_midi(
        solved_piece,
        tmp_path / "tempo.mid",
        profile=RenderProfile.CERTIFIED_SATB,
    )
    midi = MidiFile(path)
    conductor = midi.tracks[0]
    tempo = next(message for message in conductor if message.type == "set_tempo")
    tempo.tempo += 1
    midi.save(path)
    report = verify_delivery(solved_piece, path, RenderProfile.CERTIFIED_SATB)
    assert not report.accepted
    assert any("context events mismatch" in issue for issue in report.issues)
