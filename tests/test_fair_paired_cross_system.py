"""Independent reference values, shared obligations and raw-evidence replay."""

from __future__ import annotations

import copy
import json
import math
import zipfile
from pathlib import Path

import pytest
from research.check_paired_v2 import same_summary
from research.paired_cross_system_v1.render import render
from research.paired_cross_system_v2 import runner
from research.paired_cross_system_v2.contract import VOICES, admission
from research.paired_cross_system_v2.corpus import sample
from research.paired_cross_system_v2.diagnostic import check as check_diagnostic
from research.paired_cross_system_v2.oracle import delivery, semantics
from research.paired_cross_system_v2.reference import accepts
from research.paired_cross_system_v2.statistics import clopper_pearson, paired


@pytest.fixture
def cases():
    return sample("development")["primary"]


def events(entry):
    return sorted(
        [v, p, str(i), "1"]
        for i, row in enumerate(entry["witness"])
        for v, p in zip(VOICES, row, strict=True)
    )


def test_controlled_spelling_error_is_adapter_error():
    assert check_diagnostic() == {
        "cause": "adapter enharmonic bass spelling",
        "midi_pitch_unchanged": 56,
        "frozen_v1_reproduced": True,
        "corrected_full_pass": True,
    }


@pytest.mark.parametrize("index", range(8))
def test_feasibility_witness_and_rendered_bytes(cases, index):
    entry = cases[index]
    score = events(entry)
    assert admission(entry["request"]) == "SUPPORTED"
    assert semantics(entry["request"], score) == []
    assert accepts(entry["request"], score)
    for system in ("constraint-music", "music21", "diatony"):
        assert (
            delivery(entry["request"], score, render(entry["request"], score), system)["status"]
            == "PASS"
        )


def test_independent_semantics_agree_on_pitch_mutations(cases):
    for entry in cases:
        baseline = events(entry)
        for i in range(len(baseline)):
            for change in (-12, -1, 1, 12):
                score = copy.deepcopy(baseline)
                score[i][1] += change
                assert accepts(entry["request"], score) == (not semantics(entry["request"], score))


@pytest.mark.parametrize(
    "fault", ("pitch", "missing", "duplicate", "duration", "onset", "voice", "crossing")
)
def test_planted_score_faults_rejected(cases, fault):
    entry = cases[0]
    score = events(entry)
    if fault == "pitch":
        score[0][1] += 1
    elif fault == "missing":
        score.pop()
    elif fault == "duplicate":
        score[-1] = score[0]
    elif fault == "duration":
        score[0][3] = "2"
    elif fault == "onset":
        score[0][2] = "00"
    elif fault == "voice":
        score[0][0] = "Anonymous"
    else:
        soprano = next(x for x in score if x[0] == "Soprano" and x[2] == "0")
        alto = next(x for x in score if x[0] == "Alto" and x[2] == "0")
        soprano[1] = alto[1]
    assert semantics(entry["request"], score)


def test_given_voice_checked_against_external_request(cases):
    entry = copy.deepcopy(cases[0])
    score = events(entry)
    index = next(i for i, x in enumerate(entry["request"]["given_soprano"]) if x is not None)
    entry["request"]["given_soprano"][index] += 1
    assert "GIVEN_SOPRANO" in semantics(entry["request"], score)
    assert not accepts(entry["request"], score)


def test_delivered_byte_pitch_corruption_detected(cases):
    entry = cases[0]
    score = events(entry)
    altered = copy.deepcopy(score)
    altered[0][1] += 1
    assert (
        delivery(entry["request"], score, render(entry["request"], altered), "music21")["status"]
        == "REJECT"
    )
    assert delivery(entry["request"], score, b"MThd", "diatony")["status"] == "BLOCKED"


def test_unsupported_admission_does_not_launch(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        raise AssertionError("unsupported worker launched")

    monkeypatch.setattr(runner.subprocess, "Popen", forbidden)
    for i, entry in enumerate(sample("development")["unsupported"]):
        row = runner.launch("music21", entry["request"], 7, Path("unused"), tmp_path / str(i))
        assert row["status"] == "UNSUPPORTED"
        assert set(row["files"]) == {"request.json", "process.json"}


# Independent SciPy 1.17.0 binomtest.proportion_ci(method='exact') reference values.
# SciPy is deliberately not a dependency of the standard-library replay.
@pytest.mark.parametrize(
    "k,n,lo,hi",
    [
        (0, 128, 0.0, 0.038874029072690025),
        (1, 128, 0.00004898015171123739, 0.05473237320645429),
        (16, 128, 0.06239938853563283, 0.2152434377356784),
        (64, 128, 0.38738750746154105, 0.6126124925384588),
        (127, 128, 0.9452676267935457, 0.9999510198482887),
        (128, 128, 0.96112597092731, 1.0),
        (7, 50, 0.04427506364339067, 0.30370249858129145),
    ],
)
def test_exact_confidence_bounds_against_independent_reference(k, n, lo, hi):
    actual = clopper_pearson(k, n, 0.0125)
    assert actual == pytest.approx((lo, hi), abs=1e-11)


def test_paired_inference_uses_discordance_and_handles_zero():
    tied = paired([True] * 128, [True] * 128)
    assert tied["difference"] == 0 and tied["exact_mcnemar_two_sided_p"] == 1
    assert tied["conservative_paired_ci"] == pytest.approx([-0.03887402907269, 0.03887402907269])
    assert not tied["superiority_gate"]
    result = paired([True] * 128, [False] * 16 + [True] * 112)
    assert result["left_only"] == 16 and result["right_only"] == 0
    assert result["exact_mcnemar_two_sided_p"] == pytest.approx(2 / 2**16)
    assert not result["superiority_gate"]  # Significant != practical superiority.
    reverse = paired([False] * 16 + [True] * 112, [True] * 128)
    assert reverse["difference"] == -result["difference"]
    assert reverse["conservative_paired_ci"] == pytest.approx(
        [-x for x in reversed(result["conservative_paired_ci"])]
    )


def test_large_difference_meets_predeclared_gate():
    result = paired([True] * 128, [False] * 64 + [True] * 64)
    assert result["superiority_gate"]
    assert result["conservative_paired_ci"][0] > 0.10
    assert math.isfinite(result["exact_mcnemar_two_sided_p"])


@pytest.mark.parametrize("left,right", [([], []), ([True], []), ([1], [True])])
def test_invalid_paired_observations_blocked(left, right):
    with pytest.raises(ValueError):
        paired(left, right)


def test_development_raw_outputs_replay():
    rows = runner.check_phase("development")
    assert len(rows) == 72
    assert not any(row["status"] in ("HARNESS_ERROR", "BLOCKED") for row in rows)


def test_frozen_heldout_replay_and_report():
    if not (runner.ROOT / "heldout/index.json").exists():
        pytest.skip("heldout intentionally unavailable before protocol freeze")
    from research.paired_cross_system_v2.report import report

    runner.verify_freeze()
    summary = runner.analyze()
    assert same_summary(summary, json.loads((runner.ROOT / "summary.json").read_text()))
    assert summary["primary_n"] == 128 and summary["attempt_n"] == 792
    assert report(summary) == (runner.ROOT / "REPORT.md").read_text()


def test_archive_duplicate_attempt_not_accepted(monkeypatch, tmp_path):
    source = runner.ROOT / "development"
    destination = tmp_path / "development"
    destination.mkdir()
    for name in ("index.json", "attempts.json", "corpus.json", "evidence.zip"):
        (destination / name).write_bytes((source / name).read_bytes())
    rows = json.loads((destination / "attempts.json").read_text())
    rows.append(rows[0])
    runner.save(destination / "attempts.json", rows)
    index = json.loads((destination / "index.json").read_text())
    index["attempts_sha256"] = runner.digest((destination / "attempts.json").read_bytes())
    runner.save(destination / "index.json", index)
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="duplicate, missing"):
        runner.check_phase("development")


def test_native_normalization_cannot_repair_pitch(cases):
    entry = cases[4]
    with zipfile.ZipFile(runner.ROOT / "development/evidence.zip") as archive:
        slot = "development.004.constraint-music.7/"
        files = {
            p.removeprefix(slot): archive.read(p) for p in archive.namelist() if p.startswith(slot)
        }
    normalized = json.loads(files["events.json"])
    normalized[0][1] += 1
    files["events.json"] = json.dumps(normalized).encode()
    with pytest.raises(ValueError, match="native capture differs"):
        runner.inspect("constraint-music", entry["request"], files)


def test_portable_summary_allows_only_tiny_ci_rounding():
    original = {
        "paired_comparisons": {
            "diatony": {"conservative_paired_ci": [-0.2172283604579312, 0.1270438328116611]}
        }
    }
    changed = copy.deepcopy(original)
    changed["paired_comparisons"]["diatony"]["conservative_paired_ci"][1] = 0.12704383281166098
    assert same_summary(changed, original)
    changed["paired_comparisons"]["diatony"]["conservative_paired_ci"][1] += 1e-10
    assert not same_summary(changed, original)


@pytest.mark.parametrize("changed", ({"n": True}, {"n": 127}, {"n": 128, "extra": 0}))
def test_portable_summary_keeps_counts_types_and_structure_exact(changed):
    assert not same_summary(changed, {"n": 128})
