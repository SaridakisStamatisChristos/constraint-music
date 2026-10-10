"""Replay the controlled spelling experiment against the archived v1 counterexample."""

from __future__ import annotations

import json
import zipfile
from hashlib import sha256
from pathlib import Path

from research.paired_cross_system_v1.native import reconstruct
from research.paired_cross_system_v1.oracle import delivery, semantics


def check() -> dict:
    root = Path(__file__).with_name("diagnostic")
    result = json.loads((root / "result.json").read_text())
    index = json.loads((root / "index.json").read_text())
    if sha256((root / "evidence.zip").read_bytes()).hexdigest() != index["archive_sha256"]:
        raise ValueError("diagnostic archive hash mismatch")
    if sha256((root / "result.json").read_bytes()).hexdigest() != index["result_sha256"]:
        raise ValueError("diagnostic result hash mismatch")
    with zipfile.ZipFile(root / "evidence.zip") as archive:
        if len(archive.namelist()) != 8 or len(set(archive.namelist())) != 8:
            raise ValueError("diagnostic member count")
        for name in ("legacy", "corrected"):
            files = {
                p.split("/")[-1]: archive.read(p)
                for p in archive.namelist()
                if p.startswith(name + "/")
            }
            events = json.loads(files["events.json"])
            native = json.loads(files["native_input.json"])
            if reconstruct("music21", files) != events or events != result[name]["events"]:
                raise ValueError("diagnostic native events mismatch")
            request = native["request"]
            if (
                native != result[name]["native_input"]
                or semantics(request, events) != result[name]["issues"]
                or delivery(request, events, files["native.mid"], "music21")
                != result[name]["delivery"]
            ):
                raise ValueError("diagnostic verdict differs")
    legacy, corrected = result["legacy"], result["corrected"]
    if legacy["native_input"]["request"] != corrected["native_input"]["request"]:
        raise ValueError("controlled request changed")
    a, b = legacy["native_input"]["bass_spellings"], corrected["native_input"]["bass_spellings"]
    if [i for i in range(len(a)) if a[i] != b[i]] != [2] or (a[2], b[2]) != ("G#3", "A-3"):
        raise ValueError("controlled spelling difference changed")
    with zipfile.ZipFile(
        root.parent.parent / "paired_cross_system_v1/heldout/evidence.zip"
    ) as archive:
        original = json.loads(
            archive.read("attempts/heldout.extended-submediant.Eb.music21/artifact.json")
        )
    if original["events"] != legacy["events"] or legacy["issues"] != [
        "TRIAD_COMPLETENESS_OR_CONTENT"
    ]:
        raise ValueError("legacy replay does not reproduce v1")
    if corrected["issues"] or corrected["delivery"]["status"] != "PASS":
        raise ValueError("corrected replay failed")
    return {
        "cause": "adapter enharmonic bass spelling",
        "midi_pitch_unchanged": 56,
        "frozen_v1_reproduced": True,
        "corrected_full_pass": True,
    }
