"""Boundary witnesses and replay completeness for the prospective paired study."""

from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path

import pytest
from research.paired_cross_system_v1.analysis import derive, report
from research.paired_cross_system_v1.contract import admission, content_hash, make_request
from research.paired_cross_system_v1.controls import controls
from research.paired_cross_system_v1.corpus import corpus
from research.paired_cross_system_v1.faults import FAULTS, mutate
from research.paired_cross_system_v1.oracle import evaluate, semantics
from research.paired_cross_system_v1.reference import valid
from research.paired_cross_system_v1.runner import ROOT, inspect, launch


@pytest.mark.parametrize("control", controls(), ids=lambda c: c[0])
def test_hand_positive_and_ppqn_controls(control):
    _, request, artifact, data = control
    assert valid(request, artifact["events"])
    assert semantics(request, artifact["events"]) == []
    assert evaluate(request, artifact, data, "constraint-music")["status"] == "PASS"


@pytest.mark.parametrize("fault", FAULTS)
def test_repaired_faults_and_coordinated_request_bind_to_external_request(fault):
    _, request, artifact, data = controls()[0]
    original = copy.deepcopy(artifact)
    changed, output = mutate(fault, artifact, data)
    assert artifact == original
    assert changed != artifact or output != data
    if fault in ("chromatic_pitch", "missing_triad", "crossing", "artifact_duration"):
        assert changed["events_sha256"] == content_hash(changed["events"])
        assert not valid(request, changed["events"])
        assert semantics(request, changed["events"])
    verdict = evaluate(request, changed, output, "constraint-music")
    assert verdict["status"] in ("REJECT", "BLOCKED")
    if fault in ("request_key", "request_tempo", "coordinated_request"):
        assert verdict["boundary"] == "request"
    elif fault.startswith("midi_"):
        assert verdict["boundary"] == "delivery"
    else:
        assert verdict["boundary"] == "artifact"


@pytest.mark.parametrize(
    "kind",
    (
        "gap",
        "overlap",
        "leading",
        "root",
        "noncanonical",
        "fractional",
        "missing",
        "voice",
        "pitch",
        "duration",
    ),
)
def test_semantic_reference_agreement_on_negative_scores(kind):
    _, request, artifact, _ = controls()[0]
    events = copy.deepcopy(artifact["events"])
    if kind == "gap":
        events[0][2] = "1"
    elif kind == "overlap":
        events.append(copy.deepcopy(events[0]))
    elif kind == "leading":
        for e in events:
            if e[0] == "Alto" and e[2] == "8":
                e[1] = 67
    elif kind == "root":
        for e in events:
            if e[0] == "Bass" and e[2] == "0":
                e[1] = 52
    elif kind == "noncanonical":
        events[0][3] = "4/1"
    elif kind == "fractional":
        events[0][2] = "1/2"
    elif kind == "missing":
        events.pop()
    elif kind == "voice":
        events[0][0] = "unknown"
    elif kind == "pitch":
        events[0][1] = True
    else:
        events[0][3] = "-4"
    assert semantics(request, events)
    assert not valid(request, events)


def test_quarter_attacks_remain_distinct_from_whole_notes():
    _, request, artifact, data = controls()[0]
    quarter_events = sorted(
        [[v, p, str(int(a) + step), "1"] for v, p, a, _ in artifact["events"] for step in range(4)]
    )
    assert not semantics(request, quarter_events)
    assert valid(request, quarter_events)
    changed = {
        "request": request,
        "events": quarter_events,
        "events_sha256": content_hash(quarter_events),
    }
    verdict = evaluate(request, changed, data, "constraint-music")
    assert verdict["status"] == "REJECT"
    assert verdict["issues"] == ["EXACT_VOICED_EVENTS"]


def test_parallel_octaves_rejected_by_both_implementations():
    request = make_request("parallel", "C", [0, 3, 0])
    frames = [[79, 72, 64, 60], [84, 77, 69, 65], [79, 72, 64, 60]]
    events = [
        [v, p, str(i * 4), "4"]
        for i, frame in enumerate(frames)
        for v, p in zip(request["voices"], frame, strict=True)
    ]
    assert "PARALLEL_PERFECT" in semantics(request, events)
    assert not valid(request, events)


def test_split_family_key_support_and_slot_declarations():
    cases = corpus()
    dev = [c for c in cases if c["phase"] == "development"]
    held = [c for c in cases if c["phase"] == "heldout" and c["eligible"]]
    assert len({c["request"]["request_id"] for c in cases}) == len(cases)
    assert len(dev) == 4 and len(held) == 12
    assert not {c["family"] for c in dev} & {c["family"] for c in held}
    assert not {c["request"]["key"] for c in dev} & {c["request"]["key"] for c in held}
    assert all(
        admission(c["request"]) == ("SUPPORTED" if c["eligible"] else "UNSUPPORTED") for c in cases
    )
    request = make_request("admission", "C", [0, 4, 0])
    request["unknown"] = True
    assert admission(request) == "BLOCKED"


def test_missing_native_bytes_are_recorded_blocked():
    request = make_request("bad-output", "C", [0, 4, 0])
    result = inspect(request, "music21", {})
    assert result["evaluation"]["status"] == "BLOCKED"
    assert result["native_delivery"]["status"] == "UNOBSERVABLE"


def test_unsupported_never_launches_engine(monkeypatch, tmp_path):
    request = make_request("unsupported", "C", [0, 4, 0])
    request["ties"] = True
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: pytest.fail("engine was launched"))
    assert launch("music21", request, Path("absent-binary"), tmp_path) == ("UNSUPPORTED", 0.0)
    assert json.loads((tmp_path / "request.json").read_text()) == request


def test_outer_timeout_kills_process_group_and_retains_logs(monkeypatch, tmp_path):
    from research.paired_cross_system_v1 import runner

    killed = []

    class Process:
        pid = 12345
        returncode = None

        def communicate(self, timeout=None):
            if timeout is not None:
                assert timeout == 30
                raise subprocess.TimeoutExpired("test-command", timeout)
            return b"partial stdout", b"partial stderr"

    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: Process())
    monkeypatch.setattr(runner.os, "killpg", lambda pid, sig: killed.append((pid, sig)))
    request = make_request("timeout", "C", [0, 4, 0])
    assert launch("music21", request, Path("absent-binary"), tmp_path)[0] == "TIMEOUT"
    assert killed == [(12345, runner.signal.SIGKILL)]
    assert (tmp_path / "worker_stdout.txt").read_bytes() == b"partial stdout"
    assert (tmp_path / "worker_stderr.txt").read_bytes() == b"partial stderr"


@pytest.mark.skipif(
    not (ROOT / "heldout/fault_index.json").exists(), reason="prospective archive not collected"
)
def test_frozen_archive_derived_counts_and_report():
    summary = derive()
    assert summary["observed"]["heldout_attempts"] == 48
    assert summary["observed"]["heldout_primary_attempts"] == 36
    assert summary["observed"]["fault_slots"] == 432
    assert summary["observed"]["ppqn_control_slots"] == 36
    assert all(s["primary_attempts"] == 12 for s in summary["systems"].values())
    assert len(summary["paired"]) == 3
    assert all(len(p["illustrative_family_bootstrap_means"]) == 4 for p in summary["paired"])
    assert sum(summary["faults"]["statuses"].values()) == 432
    assert json.loads((ROOT / "summary.json").read_text()) == summary
    assert (ROOT / "REPORT.md").read_text() == report(summary)


@pytest.mark.skipif(
    not (ROOT / "heldout/fault_index.json").exists(), reason="prospective archive not collected"
)
def test_duplicate_planned_attempt_detected_after_repaired_row_hash(tmp_path):
    import shutil

    from research.paired_cross_system_v1.runner import check_phase, digest, read_rows

    root = tmp_path / "study"
    shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns("__pycache__"))
    path = root / "heldout/attempts.jsonl"
    rows = read_rows(path)
    rows[0] = rows[1]
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
    index_path = root / "heldout/index.json"
    index = json.loads(index_path.read_text())
    index["rows_sha256"] = digest(path.read_bytes())
    index_path.write_text(json.dumps(index))
    with pytest.raises(ValueError, match="attempt slots missing/duplicate"):
        check_phase(root, "heldout")


@pytest.mark.skipif(
    not (ROOT / "heldout/fault_index.json").exists(), reason="prospective archive not collected"
)
def test_changed_mutation_bytes_detected_after_repaired_archive_hash(tmp_path):
    import shutil
    import zipfile

    from research.paired_cross_system_v1.runner import check_faults, check_phase, digest

    root = tmp_path / "study"
    shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns("__pycache__"))
    attempts = check_phase(root, "heldout")
    path = root / "heldout/fault_bytes.zip"
    with zipfile.ZipFile(path) as archive:
        members = {name: archive.read(name) for name in archive.namelist()}
    victim = next(name for name in members if name.endswith(".mid"))
    members[victim] += b"changed"
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in members.items():
            archive.writestr(name, data)
    index_path = root / "heldout/fault_index.json"
    index = json.loads(index_path.read_text())
    index["fault_bytes.zip"] = digest(path.read_bytes())
    index_path.write_text(json.dumps(index))
    with pytest.raises(ValueError, match="mutant hash mismatch"):
        check_faults(root, attempts)
