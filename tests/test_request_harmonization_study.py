from __future__ import annotations

import copy
import json
import math
import zipfile

import pytest
from research.check_paired_v3 import check_development_replay, same_summary
from research.paired_cross_system_v3.corpus import sample
from research.paired_cross_system_v3.runner import ROOT, SYSTEMS, check_phase, derive
from research.paired_cross_system_v3.statistics import paired


def test_sealed_development_captures_and_reference_replay():
    check_development_replay()
    rows = check_phase("development")
    assert len(rows) == (8 + 4) * len(SYSTEMS) * 2
    assert not any(r["status"] in ("BLOCKED", "HARNESS_ERROR") for r in rows)
    assert (
        sum(
            r.get("inspection", {}).get("native_pass", False)
            for r in rows
            if r["system"] == "constraint-music"
        )
        == 16
    )


def test_sampling_development_uses_new_seed():
    corpus = sample("development")
    assert corpus["sampling_seed"] == 20261012
    assert len(corpus["primary"]) == 8
    # Do not generate heldout in tests: source/receipt must be committed first.
    assert len(corpus["unsupported"]) == 4


@pytest.mark.parametrize("fault", ("request", "seed", "budget", "score", "bytes", "events"))
def test_new_native_capture_corruption_blocks_inspection(fault):
    rows = json.loads((ROOT / "development/attempts.json").read_text())
    selected = next(
        r for r in rows if r["system"] == "constraint-music" and r["status"] == "OUTPUT"
    )
    request = next(
        e["request"]
        for e in sample("development")["primary"]
        if e["request"]["request_id"] == selected["request_id"]
    )
    slot = f"{selected['request_id']}.{selected['system']}.{selected['seed']}"
    with zipfile.ZipFile(ROOT / "development/evidence.zip") as archive:
        files = {n: archive.read(f"{slot}/{n}") for n in selected["files"]}
    if fault in ("request", "seed", "budget"):
        raw = json.loads(files["native_input.json"])
        if fault == "request":
            raw["harmonization_request"]["tempo_bpm"] = 99
        elif fault == "seed":
            raw["seed"] = 100
        else:
            raw["max_time_seconds"] = 100
        files["native_input.json"] = json.dumps(raw).encode()
    elif fault == "score":
        raw = json.loads(files["native_score.json"])
        raw["request"]["tempo_bpm"] = 99
        files["native_score.json"] = json.dumps(raw).encode()
    elif fault == "bytes":
        files["native.mid"] = b"bad MIDI"
    else:
        raw = json.loads(files["events.json"])
        raw[0][1] += 1
        files["events.json"] = json.dumps(raw).encode()
    assert derive("constraint-music", request, selected["seed"], files)["status"] == "BLOCKED"


def test_three_comparison_correction_and_margin_are_prespecified():
    outcome = paired([True] * 128, [False] * 128)
    assert outcome["bonferroni_p"] == 3 * outcome["exact_mcnemar_two_sided_p"]
    assert outcome["confidence"] == 1 - 0.05 / 3
    assert outcome["practical_margin"] == 0.10
    assert outcome["superiority_gate"]
    assert not paired([True] * 128, [True] * 128)["superiority_gate"]


def test_portable_interval_rounding_for_all_three_comparisons_is_narrow():
    for system in SYSTEMS[1:]:
        expected = {"paired_comparisons": {system: {"conservative_paired_ci": [0.2, 0.4]}}}
        actual = copy.deepcopy(expected)
        actual["paired_comparisons"][system]["conservative_paired_ci"][0] += 4 * math.ulp(0.2)
        assert same_summary(actual, expected)
        actual["paired_comparisons"][system]["conservative_paired_ci"][0] += 1e-10
        assert not same_summary(actual, expected)
    assert not same_summary({"count": True}, {"count": 1})
