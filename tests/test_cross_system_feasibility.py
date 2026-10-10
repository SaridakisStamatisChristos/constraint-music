from __future__ import annotations

import copy
import io
import json
from pathlib import Path

import pytest
from mido import Message, MetaMessage, MidiFile, MidiTrack
from research.cross_system_assurance_v1.feasibility import (
    ROOT,
    check,
    inspect_score,
    summarize,
)
from research.cross_system_assurance_v1.midi_probe import parse_mido, parse_smf


def midi_bytes(*, ppqn: int = 480, pitch: int = 60, duration: int = 480) -> bytes:
    midi = MidiFile(type=1, ticks_per_beat=ppqn)
    midi.tracks.append(
        MidiTrack(
            [
                MetaMessage("set_tempo", tempo=500000),
                MetaMessage("key_signature", key="G"),
                MetaMessage("time_signature", numerator=4, denominator=4),
                MetaMessage("end_of_track"),
            ]
        )
    )
    midi.tracks.append(
        MidiTrack(
            [
                Message("note_on", channel=2, note=pitch, velocity=64),
                Message("note_on", channel=2, note=pitch + 4, velocity=64),
                Message("note_off", channel=2, note=pitch, time=duration),
                Message("note_on", channel=2, note=pitch + 4, velocity=0),
                MetaMessage("end_of_track"),
            ]
        )
    )
    output = io.BytesIO()
    midi.save(file=output)
    return output.getvalue()


def test_parsers_agree_including_running_status_velocity_zero_and_context() -> None:
    data = midi_bytes()
    observed = parse_smf(data)
    assert observed == parse_mido(data)
    assert observed["events"] == [[1, 2, 60, "0", "1"], [1, 2, 64, "0", "1"]]
    assert ["0", "key", "1:0"] in observed["context"]


def test_ppqn_scaling_is_declared_rational_equivalence() -> None:
    a = parse_smf(midi_bytes())
    b = parse_smf(midi_bytes(ppqn=960, duration=960))
    assert a["events"] == b["events"]
    assert a["context"] == b["context"]
    assert a["division"] != b["division"]


def test_pitch_and_duration_faults_change_observed_relation() -> None:
    baseline = parse_smf(midi_bytes())
    assert parse_smf(midi_bytes(pitch=61))["events"] != baseline["events"]
    assert parse_smf(midi_bytes(duration=479))["events"] != baseline["events"]


@pytest.mark.parametrize("fault", ["truncated", "trailing", "smpte", "missing_end", "orphan"])
def test_malformed_smf_is_blocked(fault: str) -> None:
    data = midi_bytes()
    if fault == "truncated":
        data = data[:-1]
    elif fault == "trailing":
        data += b"x"
    elif fault == "smpte":
        data = data[:12] + b"\x80\x01" + data[14:]
    elif fault == "missing_end":
        data = data[:-4]
        # Repair the declared track length so this exercises missing EOT, not truncation.
        track = data.rfind(b"MTrk")
        size = len(data) - track - 8
        data = data[: track + 4] + size.to_bytes(4, "big") + data[track + 8 :]
    else:
        data = data.replace(bytes([0x92, 60, 64]), bytes([0x82, 60, 64]), 1)
    with pytest.raises(ValueError):
        parse_smf(data)


def score() -> dict[str, object]:
    return {
        "events": [
            [voice, i, pitch, "0", "16"]
            for i, (voice, pitch) in enumerate(
                [("Soprano", 74), ("Alto", 71), ("Tenor", 67), ("Bass", 55)]
            )
        ]
    }


def test_semantic_oracle_reconstructs_without_generator_validity() -> None:
    valid = score()
    assert inspect_score("C", valid) == []
    bad = copy.deepcopy(valid)
    bad["events"][0][2] = 73
    bad["valid"] = True
    assert "SYMBOLIC_KEY_PITCH" in inspect_score("C", bad)
    bad = copy.deepcopy(valid)
    bad["events"][0][2] = 60
    assert "SYMBOLIC_CROSSING" in inspect_score("C", bad)
    bad = copy.deepcopy(valid)
    bad["events"][0][4] = "15"
    assert "SYMBOLIC_LENGTH" in inspect_score("C", bad)
    bad = copy.deepcopy(valid)
    bad["events"][0][3] = "1"
    assert "SYMBOLIC_GAP_OVERLAP_DURATION" in inspect_score("C", bad)


def test_semantic_transposition_metamorphism() -> None:
    transformed = copy.deepcopy(score())
    for event in transformed["events"]:
        event[2] += 7
    assert inspect_score("G", transformed) == []
    assert inspect_score("C", transformed) != []


def test_archive_is_derived_from_all_six_native_pilots() -> None:
    result = check()
    assert result["comparability_gate"] == "HOLD"
    assert result["qualified_external_candidates"] == ["music21"]
    assert result["held_out_slots"] == 0
    assert result["statuses"] == {"OUTPUT": 6}


def test_missing_duplicate_slots_and_unobservable_are_not_passes() -> None:
    payload = json.loads((ROOT / "observations.json").read_text())
    support = json.loads((ROOT / "support.json").read_text())
    with pytest.raises(ValueError, match="slots"):
        summarize(payload["rows"][:-1], support)
    duplicated = [*payload["rows"][:-1], payload["rows"][0]]
    with pytest.raises(ValueError, match="slots"):
        summarize(duplicated, support)
    support["candidate_scope_ready"]["diatony"] = True
    assert summarize(payload["rows"], support)["comparability_gate"] == "HOLD"


def test_hash_tampering_fails_archive_validation(tmp_path: Path) -> None:
    import shutil

    shutil.copytree(ROOT, tmp_path / "archive")
    archive = tmp_path / "archive"
    evidence = archive / "native/music21.C/delivered.mid"
    evidence.write_bytes(evidence.read_bytes() + b"x")
    with pytest.raises(ValueError, match="hash mismatch"):
        check(archive)


def test_report_is_derived_without_hand_entered_result_tables() -> None:
    from research.cross_system_assurance_v1.report import render

    assert (ROOT / "FEASIBILITY_REPORT.md").read_text() == render()


def test_development_debug_evidence_and_collection_rows_are_preserved() -> None:
    from research.cross_system_assurance_v1.feasibility import digest

    archive = ROOT / "debug_attempts/v0"
    payload = json.loads((archive / "observations.json").read_text())
    assert len(payload["rows"]) == 6
    for row in payload["rows"]:
        for filename, expected in row["hashes"].items():
            assert digest(archive / "native" / row["id"] / filename) == expected
    original = json.loads((ROOT / "debug_attempts/serialization/observations.json").read_text())
    current = json.loads((ROOT / "observations.json").read_text())
    assert original["rows"] == current["rows"]
    assert original["protocol_hashes"]["feasibility.py"] == digest(
        ROOT / "debug_attempts/serialization/collection_feasibility.py.txt"
    )
