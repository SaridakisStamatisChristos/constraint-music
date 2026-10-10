"""Portable replay of the prospectively frozen request-bound v3 study."""

from __future__ import annotations

import json
import math
import zipfile
from hashlib import sha256
from typing import Any

from research.paired_cross_system_v2.diagnostic import check as check_diagnostic
from research.paired_cross_system_v3.report import report
from research.paired_cross_system_v3.runner import ROOT, SYSTEMS, analyze, check_phase


def check_development_replay() -> None:
    from constraint_music.harmonization import HarmonizationResult, verify_harmonization
    from constraint_music.harmonization.midi import verify_midi
    from research.paired_cross_system_v2.contract import VOICES
    from research.paired_cross_system_v2.oracle import delivery, semantics
    from research.paired_cross_system_v2.reference import accepts
    from research.paired_cross_system_v3.adapter import bound_request

    source = ROOT.parent / "paired_cross_system_v2/heldout/corpus.json"
    captured = json.loads((ROOT / "development_v2_replay.json").read_text())
    archive_path = ROOT / "development_v2_replay.zip"
    if sha256(source.read_bytes()).hexdigest() != captured["source_corpus_sha256"]:
        raise ValueError("development source corpus differs")
    if sha256(archive_path.read_bytes()).hexdigest() != captured["archive_sha256"]:
        raise ValueError("development replay archive differs")
    requests = {
        e["request"]["request_id"]: e["request"] for e in json.loads(source.read_text())["primary"]
    }
    attempts = captured["attempts"]
    planned = {(name, seed) for name in requests for seed in (7, 19)}
    if len(attempts) != len(planned) or {(a["request_id"], a["seed"]) for a in attempts} != planned:
        raise ValueError("development attempt slots differ")
    if (captured["primary_n"], captured["pass_both_runs"]) != (128, 128):
        raise ValueError("development count differs")
    with zipfile.ZipFile(archive_path) as archive:
        expected_members = set()
        for attempt in attempts:
            name, seed = attempt["request_id"], attempt["seed"]
            request = requests[name]
            if attempt["pass"] is not True or set(attempt["files"]) != {
                "native_score.json",
                "native.mid",
                "adapted.mid",
                "events.json",
            }:
                raise ValueError("development capture fields differ")
            files = {}
            for filename, digest in attempt["files"].items():
                member = f"{name}.{seed}/{filename}"
                expected_members.add(member)
                files[filename] = archive.read(member)
                if sha256(files[filename]).hexdigest() != digest:
                    raise ValueError("development member differs")
            score = HarmonizationResult.from_dict(json.loads(files["native_score.json"]))
            bound = bound_request(request)
            events = json.loads(files["events.json"])
            reconstructed = sorted(
                [v, p, str(i), "1"]
                for i, row in enumerate(score.rows)
                for v, p in zip(VOICES, row, strict=True)
            )
            if (
                score.request != bound
                or reconstructed != events
                or (
                    verify_harmonization(bound, score.rows)
                    or verify_midi(bound, score.rows, files["native.mid"])
                )
            ):
                raise ValueError("development native reconstruction differs")
            if semantics(request, events) or not accepts(request, events):
                raise ValueError("development semantic references disagree")
            for filename in ("native.mid", "adapted.mid"):
                if (
                    delivery(request, events, files[filename], "constraint-music")["status"]
                    != "PASS"
                ):
                    raise ValueError("development delivered relation failed")
        if (
            len(archive.namelist()) != len(expected_members)
            or set(archive.namelist()) != expected_members
        ):
            raise ValueError("development archive membership differs")


def same_summary(actual: Any, expected: Any, path: tuple = ()) -> bool:
    """Exact types/structure/values, except at most eight ULPs on the two CI bounds."""
    if type(actual) is not type(expected):
        return False
    if isinstance(actual, dict):
        return actual.keys() == expected.keys() and all(
            same_summary(actual[key], expected[key], (*path, key)) for key in actual
        )
    if isinstance(actual, list):
        return len(actual) == len(expected) and all(
            same_summary(a, b, (*path, index))
            for index, (a, b) in enumerate(zip(actual, expected, strict=True))
        )
    if (
        type(actual) is float
        and len(path) == 4
        and path[0] == "paired_comparisons"
        and path[1] in SYSTEMS[1:]
        and path[2] == "conservative_paired_ci"
        and path[3] in (0, 1)
    ):
        return (
            math.isfinite(actual)
            and math.isfinite(expected)
            and abs(actual - expected) <= 8 * max(math.ulp(actual), math.ulp(expected))
        )
    return actual == expected


def check() -> None:
    check_diagnostic()
    check_development_replay()
    check_phase("development")
    # analyze verifies all frozen source objects and the complete heldout archive.
    summary = analyze()
    if not same_summary(summary, json.loads((ROOT / "summary.json").read_text())):
        raise ValueError("summary differs beyond allowed CI-bound rounding")
    if report(summary) != (ROOT / "REPORT.md").read_text():
        raise ValueError("report differs from recomputed evidence")
    print("v3 portable raw replay and paired analysis: PASS")


if __name__ == "__main__":
    check()
