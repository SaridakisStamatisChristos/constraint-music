from __future__ import annotations

import copy
import io
import json
import shutil
from pathlib import Path

import pytest
from mido import MidiFile
from research.cross_system_assurance_v1.feasibility import ROOT as NATIVE_ROOT
from research.cross_system_assurance_v1.midi_probe import parse_mido, parse_smf
from research.cross_system_delivery_v1.contract import (
    VOICES,
    inspect_input,
    request_for,
    validate_request,
)
from research.cross_system_delivery_v1.pilot import (
    ROOT,
    check,
    derive,
    inspect_delivery,
    inspect_pilot,
    report,
    source_events,
)
from research.cross_system_delivery_v1.renderer import read_rows, render

TEXT = "VOICE_ROWS_B_T_A_S\n60 64 67 67\n53 60 65 69\n55 62 67 71\n60 64 67 72\n"


def hand_events() -> list[list[object]]:
    # Hand-authored reference, deliberately distinct from the writer's row traversal.
    parts = {
        "Soprano": [67, 69, 71, 72],
        "Alto": [67, 65, 67, 67],
        "Tenor": [64, 60, 62, 64],
        "Bass": [60, 53, 55, 60],
    }
    return [
        [voice, 0, pitch, str(chord * 4), "4"]
        for voice, pitches in parts.items()
        for chord, pitch in enumerate(pitches)
    ]


@pytest.mark.parametrize("ppqn", [120, 480, 960])
def test_hand_constructed_voice_identity_unison_and_time_equivalence(ppqn: int) -> None:
    data = render(TEXT, request_for("C"), ppqn=ppqn)
    result = inspect_delivery(request_for("C"), hand_events(), data)
    assert result["symbolic_issues"] == []
    assert result["voice_event_relation"] == result["context_relation"] == "PASS"
    assert parse_smf(data) == parse_mido(data)
    assert result["division"] == ppqn


@pytest.mark.parametrize(
    "field,value",
    [
        ("harmony_constraint", "I-IV-V-I"),
        ("given_voice", [60]),
        ("tempo_bpm", 90),
        ("mode", "minor"),
        ("duration_quarters", 8),
        ("voices", list(reversed(VOICES))),
        ("schema_version", True),
        ("additional_property", True),
    ],
)
def test_unsupported_requests_are_rejected_without_silent_translation(
    field: str, value: object
) -> None:
    request = request_for("C")
    request[field] = value
    with pytest.raises(ValueError, match="unsupported"):
        validate_request(request)
    with pytest.raises(ValueError, match="unsupported"):
        render(TEXT, request)


@pytest.mark.parametrize(
    "text",
    [
        "",
        TEXT.replace("B_T_A_S", "S_A_T_B"),
        TEXT + "60 64 67 72\n",
        TEXT.replace("60 64 67 67", "60 64 67"),
        TEXT.replace("60 64 67 67", "60 64 67 128"),
    ],
)
def test_invalid_captures_are_blocked(text: str) -> None:
    with pytest.raises(ValueError):
        read_rows(text)


def mutate(data: bytes, fault: str) -> bytes:
    midi = MidiFile(file=io.BytesIO(data))
    if fault == "voice_channel":
        for message in midi.tracks[1]:
            if message.type in ("note_on", "note_off"):
                message.channel = 1
    elif fault == "voice_pitch":
        for message in midi.tracks[1]:
            if message.type in ("note_on", "note_off"):
                message.note -= 12
    elif fault == "duration":
        next(m for m in midi.tracks[1] if m.type == "note_off").time -= 1
    elif fault == "tempo":
        next(m for m in midi.tracks[0] if m.type == "set_tempo").tempo = 600000
    elif fault == "key":
        next(m for m in midi.tracks[0] if m.type == "key_signature").key = "G"
    elif fault == "meter":
        next(m for m in midi.tracks[0] if m.type == "time_signature").numerator = 3
    else:
        midi.tracks.pop()
    output = io.BytesIO()
    midi.save(file=output)
    return output.getvalue()


@pytest.mark.parametrize(
    "fault", ["voice_channel", "voice_pitch", "duration", "missing_voice", "tempo", "key", "meter"]
)
def test_delivery_faults_are_detected_against_original_source_and_request(fault: str) -> None:
    original = render(TEXT, request_for("C"))
    changed = mutate(original, fault)
    assert changed != original
    result = inspect_delivery(request_for("C"), hand_events(), changed)
    field = "context_relation" if fault in ("tempo", "key", "meter") else "voice_event_relation"
    assert result[field] == "FAIL"


def test_transposition_changes_source_and_context_together() -> None:
    rows = [[value + 7 for value in row] for row in read_rows(TEXT)]
    text = "VOICE_ROWS_B_T_A_S\n" + "\n".join(" ".join(map(str, row)) for row in rows) + "\n"
    events = hand_events()
    for event in events:
        event[2] += 7
    result = inspect_delivery(request_for("G"), events, render(text, request_for("G")))
    assert result["symbolic_issues"] == []
    assert result["voice_event_relation"] == result["context_relation"] == "PASS"
    mismatched = inspect_delivery(request_for("C"), events, render(text, request_for("G")))
    assert mismatched["context_relation"] == "FAIL"
    assert mismatched["symbolic_issues"]


def test_original_input_projection_checks_key_and_presets() -> None:
    for system in ("constraint-music", "music21", "diatony"):
        native = json.loads((NATIVE_ROOT / "native" / f"{system}.C" / "input.json").read_text())
        assert inspect_input(system, request_for("C"), native) == []
        assert inspect_input(system, request_for("G"), native)


def test_new_pilots_preserve_native_failures_and_qualify_only_adapted_delivery() -> None:
    result = check()
    assert result["delivery_feasibility_gate"] == "GO"
    assert result["qualified_external_engines"] == ["music21", "diatony"]
    assert result["native_profile_gate"] == "HOLD"
    assert result["held_out_slots"] == 0
    assert result["paired_generation_benchmark_completed"] is False
    assert result["new_slot_statuses"] == {"OUTPUT": 2}
    for key in ("C", "G"):
        native = inspect_pilot(ROOT, key)["native_inspection"]
        assert native["voice_event_relation"] == "UNOBSERVABLE"
        assert native["context_relation"] == "FAIL"
        assert native["unvoiced_event_relation"] == "PASS"
        assert len(source_events(ROOT / "pilots" / f"diatony.{key}")) == 16


def test_missing_duplicate_failed_or_unobservable_slots_do_not_qualify() -> None:
    rows = json.loads((ROOT / "observations.json").read_text())["rows"]
    with pytest.raises(ValueError, match="slots"):
        derive(ROOT, rows[:1])
    with pytest.raises(ValueError, match="slots"):
        derive(ROOT, [rows[0], rows[0]])
    for fault in ("HARNESS_ERROR", "UNOBSERVABLE", "UNVOICED_FAIL", "PARSER_DISAGREEMENT"):
        changed = copy.deepcopy(rows)
        if fault == "HARNESS_ERROR":
            changed[0]["status"] = fault
        elif fault == "UNOBSERVABLE":
            changed[0]["inspection"]["voice_event_relation"] = fault
        elif fault == "PARSER_DISAGREEMENT":
            changed[0]["inspection"]["parser_agreement"] = False
        else:
            changed[0]["inspection"]["symbolic_issues"] = ["SYMBOLIC_LENGTH"]
        assert derive(ROOT, changed)["delivery_feasibility_gate"] == "HOLD"


@pytest.mark.parametrize(
    "path",
    [
        "pilots/diatony.C/adapted.mid",
        "pilots/diatony.C/delivered.mid",
        "pilots/diatony.C/score.txt",
        "requests/C.json",
        "renderer.py",
    ],
)
def test_source_native_adapted_request_and_code_tampering_is_blocked(
    tmp_path: Path, path: str
) -> None:
    archive = tmp_path / "archive"
    shutil.copytree(ROOT, archive)
    evidence = archive / path
    evidence.write_bytes(evidence.read_bytes() + b"x")
    with pytest.raises(ValueError, match="hash mismatch"):
        check(archive)


def test_coordinated_request_copy_change_still_fails_external_binding(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    shutil.copytree(ROOT, archive)
    request = request_for("G")
    (archive / "pilots/diatony.C/request.json").write_text(json.dumps(request))
    with pytest.raises(ValueError, match="binding"):
        inspect_pilot(archive, "C")


def test_report_is_derived_from_archived_bytes() -> None:
    assert (ROOT / "FEASIBILITY_REPORT.md").read_text() == report()
