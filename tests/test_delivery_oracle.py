from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from hashlib import sha256

import pytest
from mido import Message, MetaMessage, MidiFile, MidiTrack
from research.oracle.delivery import (
    OracleNoteEvent,
    adjudicate_delivery,
    project_context,
    project_melody,
    project_satb,
)

from constraint_music import midi as midi_module
from constraint_music.delivery import DeliveryReport, RenderProfile, output_digest, verify_delivery
from constraint_music.midi import write_certified_midi, write_midi
from constraint_music.models import GenerationResult, RhythmState
from constraint_music.satb import SatbGenerationResult

_SATB_TRACKS = ("Soprano", "Alto", "Tenor", "Bass")


def _key_name(result: GenerationResult) -> str:
    key = result.spec.tonal_key
    display = key.tonic[0] + key.tonic[1:].replace("B", "b")
    return display if key.mode.value == "major" else display + "m"


def _expected_context(result: GenerationResult):
    destination = result.spec.modulation_destination
    destination_name = None
    if destination is not None:
        display = destination.tonic[0] + destination.tonic[1:].replace("B", "b")
        destination_name = (
            display if destination.mode.value == "major" else display + "m"
        )
    return project_context(
        tempo_bpm=result.spec.tempo_bpm,
        beats_per_bar=result.spec.beats_per_bar,
        initial_key=_key_name(result),
        destination_key=destination_name,
        modulation_boundary_beat=result.spec.modulation_boundary_beat,
    )


def _expected_events(
    result: GenerationResult,
    profile: RenderProfile,
) -> tuple[OracleNoteEvent, ...]:
    assert isinstance(result, SatbGenerationResult)
    events = list(project_satb(result.soprano, result.alto, result.tenor, result.bass))
    if profile is RenderProfile.MELODY_PLUS_SATB:
        events.extend(
            project_melody(
                result.melody,
                tuple(state.name.lower() for state in result.effective_rhythm),
                subdivisions_per_beat=result.spec.subdivisions_per_beat,
                channel=4,
            )
        )
    return tuple(sorted(events))


def _oracle_check(
    result: GenerationResult,
    path,
    profile: RenderProfile = RenderProfile.CERTIFIED_SATB,
):
    tracks = _SATB_TRACKS + (("Melody",) if profile is RenderProfile.MELODY_PLUS_SATB else ())
    return adjudicate_delivery(
        path.read_bytes(),
        allowed_tracks=tracks,
        expected_events=_expected_events(result, profile),
        expected_context=_expected_context(result),
    )


@pytest.mark.parametrize(
    "profile",
    [RenderProfile.CERTIFIED_SATB, RenderProfile.MELODY_PLUS_SATB],
)
def test_standard_library_oracle_accepts_each_certifying_profile(
    tmp_path,
    solved_piece: GenerationResult,
    profile: RenderProfile,
) -> None:
    assert isinstance(solved_piece, SatbGenerationResult)
    result = solved_piece
    if profile is RenderProfile.MELODY_PLUS_SATB:
        rhythm = (
            RhythmState.ONSET,
            RhythmState.TIE,
            RhythmState.REST,
            RhythmState.ONSET,
            RhythmState.ONSET,
            RhythmState.REST,
            RhythmState.ONSET,
            RhythmState.TIE,
        )
        result = replace(
            solved_piece,
            melody=(60, 60, 62, 64, 65, 67, 69, 69),
            rhythm=rhythm,
        )
    path = write_midi(result, tmp_path / f"{profile.value}.mid", profile=profile)
    decision = _oracle_check(result, path, profile)
    assert decision.accepted, decision.issues
    assert decision.observed is not None
    assert decision.observed.note_events == _expected_events(result, profile)
    assert decision.output_sha256 == output_digest(path)


@pytest.mark.parametrize(
    "first_beat",
    [
        pytest.param((72, 67, 64, 48), id="diatonic-root"),
        pytest.param((71, 65, 62, 43), id="diatonic-seventh"),
        pytest.param((73, 67, 64, 46), id="applied-dominant"),
        pytest.param((72, 68, 63, 44), id="borrowed-seventh"),
        pytest.param((70, 67, 64, 61), id="fully-diminished-root"),
        pytest.param((70, 67, 61, 64), id="fully-diminished-first"),
        pytest.param((70, 64, 61, 67), id="fully-diminished-second"),
        pytest.param((67, 64, 61, 70), id="fully-diminished-third"),
        pytest.param((71, 67, 64, 61), id="half-diminished-root"),
        pytest.param((71, 67, 61, 64), id="half-diminished-first"),
        pytest.param((71, 64, 61, 67), id="half-diminished-second"),
        pytest.param((67, 64, 61, 71), id="half-diminished-third"),
    ],
)
def test_oracle_preserves_exact_register_across_form_and_inversion_corpus(
    tmp_path,
    solved_piece: GenerationResult,
    first_beat: tuple[int, int, int, int],
) -> None:
    assert isinstance(solved_piece, SatbGenerationResult)
    soprano, alto, tenor, bass = first_beat
    result = replace(
        solved_piece,
        soprano=(soprano, *solved_piece.soprano[1:]),
        alto=(alto, *solved_piece.alto[1:]),
        tenor=(tenor, *solved_piece.tenor[1:]),
        bass=(bass, *solved_piece.bass[1:]),
    )
    path = write_midi(
        result,
        tmp_path / "form.mid",
        profile=RenderProfile.CERTIFIED_SATB,
    )
    decision = _oracle_check(result, path)
    assert decision.accepted, decision.issues


def test_oracle_and_production_reject_note_identity_and_context_mutations(
    tmp_path,
    solved_piece: GenerationResult,
) -> None:
    assert isinstance(solved_piece, SatbGenerationResult)

    def pitch(midi: MidiFile) -> None:
        track = next(item for item in midi.tracks if item.name == "Alto")
        note_on = next(item for item in track if item.type == "note_on" and item.velocity)
        original = note_on.note
        note_on.note += 1
        next(
            item for item in track if item.type == "note_off" and item.note == original
        ).note += 1

    def channel(midi: MidiFile) -> None:
        track = next(item for item in midi.tracks if item.name == "Tenor")
        note_on = next(item for item in track if item.type == "note_on" and item.velocity)
        note_off = next(
            item for item in track if item.type == "note_off" and item.note == note_on.note
        )
        note_on.channel = note_off.channel = 9

    def onset(midi: MidiFile) -> None:
        track = next(item for item in midi.tracks if item.name == "Bass")
        next(item for item in track if item.type == "note_on" and item.velocity).time += 1

    def duration(midi: MidiFile) -> None:
        track = next(item for item in midi.tracks if item.name == "Soprano")
        next(item for item in track if item.type == "note_off").time += 1

    def rename(midi: MidiFile) -> None:
        track = next(item for item in midi.tracks if item.name == "Alto")
        next(item for item in track if item.type == "track_name").name = "Viola"

    def missing(midi: MidiFile) -> None:
        index = next(index for index, item in enumerate(midi.tracks) if item.name == "Tenor")
        midi.tracks.pop(index)

    def duplicate(midi: MidiFile) -> None:
        track = next(item for item in midi.tracks if item.name == "Bass")
        midi.tracks.append(deepcopy(track))

    def extra(midi: MidiFile) -> None:
        midi.tracks.append(
            MidiTrack(
                [
                    MetaMessage("track_name", name="Undeclared", time=0),
                    Message("note_on", channel=9, note=60, velocity=64, time=0),
                    Message("note_off", channel=9, note=60, velocity=0, time=120),
                ]
            )
        )

    def resolution(midi: MidiFile) -> None:
        midi.ticks_per_beat += 1

    def tempo(midi: MidiFile) -> None:
        conductor = midi.tracks[0]
        next(item for item in conductor if item.type == "set_tempo").tempo += 1

    def meter(midi: MidiFile) -> None:
        conductor = midi.tracks[0]
        next(item for item in conductor if item.type == "time_signature").numerator = 3

    def key(midi: MidiFile) -> None:
        conductor = midi.tracks[0]
        next(item for item in conductor if item.type == "key_signature").key = "G"

    mutations = {
        "pitch": pitch,
        "channel": channel,
        "onset": onset,
        "duration": duration,
        "rename": rename,
        "missing": missing,
        "duplicate": duplicate,
        "extra": extra,
        "resolution": resolution,
        "tempo": tempo,
        "meter": meter,
        "key": key,
    }
    for name, mutate in mutations.items():
        path = write_midi(
            solved_piece,
            tmp_path / f"{name}.mid",
            profile=RenderProfile.CERTIFIED_SATB,
        )
        midi = MidiFile(path)
        mutate(midi)
        midi.save(path)
        oracle = _oracle_check(solved_piece, path)
        production = verify_delivery(solved_piece, path, RenderProfile.CERTIFIED_SATB)
        assert not oracle.accepted, name
        assert not production.accepted, name


def test_overlapping_same_pitch_note_on_is_rejected_even_when_fifo_pairs_match(
    tmp_path,
    solved_piece: GenerationResult,
) -> None:
    assert isinstance(solved_piece, SatbGenerationResult)
    result = replace(solved_piece, soprano=(60,) * solved_piece.spec.total_beats)
    path = write_midi(result, tmp_path / "overlap.mid", profile=RenderProfile.CERTIFIED_SATB)
    midi = MidiFile(path)
    track = next(item for item in midi.tracks if item.name == "Soprano")
    first_off = next(index for index, item in enumerate(track) if item.type == "note_off")
    second_on = next(
        index
        for index, item in enumerate(track[first_off + 1 :], start=first_off + 1)
        if item.type == "note_on" and item.velocity
    )
    assert second_on == first_off + 1
    note_off = track[first_off]
    note_on = track[second_on]
    note_on.time = note_off.time
    note_off.time = 0
    track[first_off], track[second_on] = note_on, note_off
    midi.save(path)

    oracle = _oracle_check(result, path)
    production = verify_delivery(result, path, RenderProfile.CERTIFIED_SATB)
    assert not oracle.accepted
    assert any("overlapping note-on" in issue for issue in oracle.issues)
    assert not production.accepted
    assert any("overlapping note-on" in issue for issue in production.issues)


def test_modulation_key_change_tick_is_independently_observed(
    tmp_path,
    solved_piece: GenerationResult,
) -> None:
    spec = replace(
        solved_piece.spec,
        modulation_enabled=True,
        modulation_destination_key="G",
        modulation_boundary_beat=2,
        require_authentic_cadence=False,
    )
    result = replace(solved_piece, spec=spec)
    path = write_midi(result, tmp_path / "modulated.mid", profile=RenderProfile.CERTIFIED_SATB)
    assert _oracle_check(result, path).accepted

    midi = MidiFile(path)
    key_changes = [item for item in midi.tracks[0] if item.type == "key_signature"]
    assert len(key_changes) == 2
    key_changes[1].time += 1
    midi.save(path)
    assert not _oracle_check(result, path).accepted
    assert not verify_delivery(result, path, RenderProfile.CERTIFIED_SATB).accepted


def test_oracle_rejects_truncated_midi_without_uncaught_parser_error(
    tmp_path,
    solved_piece: GenerationResult,
) -> None:
    path = write_midi(
        solved_piece,
        tmp_path / "truncated.mid",
        profile=RenderProfile.CERTIFIED_SATB,
    )
    data = path.read_bytes()[:-7]
    decision = adjudicate_delivery(
        data,
        allowed_tracks=_SATB_TRACKS,
        expected_events=_expected_events(solved_piece, RenderProfile.CERTIFIED_SATB),
        expected_context=_expected_context(solved_piece),
    )
    assert not decision.accepted
    assert decision.observed is None


def test_atomic_publication_preserves_existing_output_on_verification_failure(
    tmp_path,
    solved_piece: GenerationResult,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "piece.mid"
    destination.write_bytes(b"previous-certified-output")
    rejected = DeliveryReport(
        False,
        RenderProfile.CERTIFIED_SATB,
        (),
        (),
        ("injected delivery fault",),
    )
    monkeypatch.setattr(midi_module, "verify_delivery", lambda *_args, **_kwargs: rejected)
    with pytest.raises(ValueError, match="injected delivery fault"):
        write_certified_midi(solved_piece, destination)
    assert destination.read_bytes() == b"previous-certified-output"
    assert not tuple(tmp_path.glob(".piece.*.mid"))


def test_atomic_publication_cleans_temporary_output_on_replace_failure(
    tmp_path,
    solved_piece: GenerationResult,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "piece.mid"
    destination.write_bytes(b"previous-certified-output")

    def fail_replace(_source, _destination) -> None:
        raise OSError("injected replace fault")

    monkeypatch.setattr(midi_module, "atomic_replace", fail_replace)
    with pytest.raises(OSError, match="injected replace fault"):
        write_certified_midi(solved_piece, destination)
    assert destination.read_bytes() == b"previous-certified-output"
    assert not tuple(tmp_path.glob(".piece.*.mid"))


def test_certified_publication_replaces_atomically_and_binds_exact_bytes(
    tmp_path,
    solved_piece: GenerationResult,
) -> None:
    destination = tmp_path / "piece.mid"
    destination.write_bytes(b"stale")
    write_certified_midi(solved_piece, destination)
    decision = _oracle_check(solved_piece, destination)
    assert decision.accepted, decision.issues
    assert output_digest(destination) == sha256(destination.read_bytes()).hexdigest()
    assert not tuple(tmp_path.glob(".piece.*.mid"))
