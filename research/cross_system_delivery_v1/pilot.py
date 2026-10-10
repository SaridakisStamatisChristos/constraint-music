"""Collect/check the adapted profile, retaining both native and adapted delivery."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import subprocess
import time
from collections import Counter
from fractions import Fraction
from pathlib import Path
from typing import Any

from research.cross_system_assurance_v1.feasibility import (
    ROOT as NATIVE_ROOT,
)
from research.cross_system_assurance_v1.feasibility import (
    check as check_native,
)
from research.cross_system_assurance_v1.feasibility import (
    digest,
    inspect_attempt,
    inspect_score,
    probe,
    write_json,
)
from research.cross_system_assurance_v1.midi_probe import parse_mido, parse_smf

from .contract import VOICES, inspect_input, validate_request

ROOT = Path(__file__).resolve().parent
PROTOCOL = (
    "manifest.json",
    "contract.py",
    "renderer.py",
    "pilot.py",
    "requests/C.json",
    "requests/G.json",
)


def load_request(root: Path, key: str) -> dict[str, Any]:
    request = json.loads((root / "requests" / f"{key}.json").read_text())
    validate_request(request)
    if request["key"] != key:
        raise ValueError("request identity mismatch")
    return request


def source_events(directory: Path) -> list[list[Any]]:
    """Independently reconstruct the public capture order, without renderer helpers."""
    lines = (directory / "score.txt").read_text().splitlines()
    if len(lines) != 5 or lines[0] != "VOICE_ROWS_B_T_A_S":
        raise ValueError("invalid native capture")
    events = []
    columns = {"Bass": 0, "Tenor": 1, "Alto": 2, "Soprano": 3}
    for chord, line in enumerate(lines[1:]):
        values = [int(value) for value in line.split()]
        if len(values) != 4 or any(not 0 <= pitch <= 127 for pitch in values):
            raise ValueError("invalid native pitches")
        for voice, column in columns.items():
            events.append([voice, 0, values[column], str(4 * chord), "4"])
    recorded = json.loads((directory / "normalized.json").read_text())["events"]
    if sorted(events) != recorded:
        raise ValueError("native capture/normalization mismatch")
    return sorted(events)


def inspect_delivery(
    request: dict[str, Any], events: list[list[Any]], data: bytes
) -> dict[str, Any]:
    """Read delivered bytes using two parsers; expected facts come from source/request."""
    validate_request(request)
    parsed = parse_smf(data)
    if parsed != parse_mido(data):
        raise ValueError("independent parsers disagree")
    mapping = {(i + 1, i): voice for i, voice in enumerate(VOICES)}
    expected = Counter((e[0], e[2], e[3], e[4]) for e in events)
    actual = Counter((mapping.get((e[0], e[1])), e[2], e[3], e[4]) for e in parsed["events"])
    expected_context = sorted(
        [
            ["0", "key", "0:0" if request["key"] == "C" else "1:0"],
            ["0", "meter", request["meter"]],
            ["0", "tempo", str(60_000_000 // request["tempo_bpm"])],
        ]
    )
    symbolic = inspect_score(request["key"], {"events": events})
    if any(Fraction(e[4]) not in (1, 4) for e in events):
        symbolic.append("SYMBOLIC_UNSUPPORTED_RHYTHM")
    return {
        "parser_agreement": True,
        "parsed_notes": len(parsed["events"]),
        "division": parsed["division"],
        "symbolic_issues": sorted(set(symbolic)),
        "voice_event_relation": "PASS" if actual == expected else "FAIL",
        "context_relation": "PASS" if parsed["context"] == expected_context else "FAIL",
    }


def inspect_pilot(root: Path, key: str) -> dict[str, Any]:
    directory = root / "pilots" / f"diatony.{key}"
    request = load_request(root, key)
    if json.loads((directory / "request.json").read_text()) != request:
        raise ValueError("external request binding mismatch")
    native = json.loads((directory / "input.json").read_text())
    result = inspect_delivery(
        request, source_events(directory), (directory / "adapted.mid").read_bytes()
    )
    result["input_issues"] = inspect_input("diatony", request, native)
    result["native_inspection"] = inspect_attempt("diatony", key, directory)
    return result


def derive(root: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    if len(rows) != 2 or {r["id"] for r in rows} != {"diatony.C", "diatony.G"}:
        raise ValueError("planned adapted slots missing or duplicate")
    check_native()
    manifest = json.loads((root / "manifest.json").read_text())
    if manifest["planned_render_slots"] != ["diatony.C", "diatony.G"]:
        raise ValueError("unexpected slot declaration")
    native_rows = json.loads((NATIVE_ROOT / "observations.json").read_text())["rows"]
    profile_rows = []
    for system in ("constraint-music", "music21", "diatony"):
        for key in ("C", "G"):
            request = load_request(root, key)
            if system == "diatony":
                row = next(r for r in rows if r["id"] == f"diatony.{key}")
                inspection = row.get("inspection", {})
                status = row["status"]
            else:
                row = next(r for r in native_rows if r["id"] == f"{system}.{key}")
                directory = NATIVE_ROOT / "native" / row["id"]
                inspection = inspect_attempt(system, key, directory)
                inspection["input_issues"] = inspect_input(
                    system, request, json.loads((directory / "input.json").read_text())
                )
                events = json.loads((directory / "normalized.json").read_text())["events"]
                if any(Fraction(e[4]) not in (1, 4) for e in events):
                    inspection["symbolic_issues"].append("SYMBOLIC_UNSUPPORTED_RHYTHM")
                status = row["status"]
            passed = (
                status == "OUTPUT"
                and inspection.get("parser_agreement") is True
                and inspection.get("voice_event_relation") == "PASS"
                and inspection.get("context_relation") == "PASS"
                and inspection.get("symbolic_issues") == []
                and inspection.get("input_issues") == []
            )
            profile_rows.append(
                {
                    "id": f"{system}.{key}",
                    "profile": manifest["profiles"][system]["delivery"],
                    "request_id": request["request_id"],
                    "status": status,
                    "shared_delivery_pass": passed,
                    "inspection": inspection,
                }
            )
    qualified = [
        system
        for system in ("music21", "diatony")
        if all(r["shared_delivery_pass"] for r in profile_rows if r["id"].startswith(system + "."))
    ]
    groups = {manifest["profiles"][system]["independence_group"] for system in qualified}
    return {
        "delivery_feasibility_gate": "GO" if len(groups) >= 2 else "HOLD",
        "qualified_external_engines": qualified,
        "new_generation_slots": 2,
        "observed_new_generation_slots": len(rows),
        "new_slot_statuses": dict(Counter(r["status"] for r in rows)),
        "profile_rows": profile_rows,
        "native_profile_gate": "HOLD",
        "paired_generation_benchmark_completed": False,
        "held_out_slots": 0,
    }


def check(root: Path = ROOT) -> dict[str, Any]:
    payload = json.loads((root / "observations.json").read_text())
    if payload["source_observations_sha256"] != digest(NATIVE_ROOT / "observations.json"):
        raise ValueError("source archive hash mismatch")
    if set(payload["protocol_hashes"]) != set(PROTOCOL):
        raise ValueError("protocol coverage mismatch")
    for filename, expected in payload["protocol_hashes"].items():
        if digest(root / filename) != expected:
            raise ValueError(f"protocol hash mismatch: {filename}")
    for row in payload["rows"]:
        if row["id"] not in ("diatony.C", "diatony.G"):
            raise ValueError("unknown pilot identity")
        directory = root / "pilots" / row["id"]
        filenames = {p.name for p in directory.iterdir() if p.is_file()}
        if filenames != set(row["hashes"]):
            raise ValueError("evidence coverage mismatch")
        for filename, expected in row["hashes"].items():
            if Path(filename).name != filename or digest(directory / filename) != expected:
                raise ValueError(f"evidence hash mismatch: {row['id']}/{filename}")
        if row["status"] == "OUTPUT":
            required = {
                "score.txt",
                "normalized.json",
                "delivered.mid",
                "adapted.mid",
                "request.json",
                "input.json",
            }
            if not required <= filenames:
                raise ValueError("required evidence missing")
            actual = inspect_pilot(root, row["id"].split(".")[1])
            if json.dumps(actual, sort_keys=True) != json.dumps(row["inspection"], sort_keys=True):
                raise ValueError("pilot inspection mismatch")
        elif row["status"] != "HARNESS_ERROR":
            raise ValueError("unknown pilot status")
    summary = derive(root, payload["rows"])
    if json.dumps(summary, sort_keys=True) != json.dumps(
        json.loads((root / "summary.json").read_text()), sort_keys=True
    ):
        raise ValueError("derived summary mismatch")
    return summary


def run(binary: Path) -> None:
    from .renderer import render

    if (ROOT / "observations.json").exists() or (ROOT / "pilots").exists():
        raise ValueError("archive exists; use a new versioned study for reruns")
    check_native()
    source = json.loads((NATIVE_ROOT / "observations.json").read_text())
    if digest(binary) != source["environment"]["diatony_probe_sha256"]:
        raise ValueError("probe binary differs from pinned native pilot")
    if importlib.metadata.version("mido") != "1.3.3":
        raise ValueError("pinned mido 1.3.3 required for collection")
    protocol_hashes = {filename: digest(ROOT / filename) for filename in PROTOCOL}
    rows = []
    for key in ("C", "G"):
        request = load_request(ROOT, key)
        directory = ROOT / "pilots" / f"diatony.{key}"
        directory.mkdir(parents=True)
        write_json(directory / "request.json", request)
        row: dict[str, Any] = {"id": f"diatony.{key}", "status": "HARNESS_ERROR"}
        start = time.perf_counter()
        try:
            probe("diatony", key, directory, binary.resolve())
            data = render((directory / "score.txt").read_text(), request)
            (directory / "adapted.mid").write_bytes(data)
            row["inspection"] = inspect_pilot(ROOT, key)
            row["status"] = "OUTPUT"
        except (ValueError, OSError, subprocess.SubprocessError) as exc:
            (directory / "error.txt").write_text(f"{type(exc).__name__}: {exc}\n")
        row["elapsed_generation_and_render_seconds"] = round(time.perf_counter() - start, 6)
        row["hashes"] = {p.name: digest(p) for p in sorted(directory.iterdir()) if p.is_file()}
        rows.append(row)
    if protocol_hashes != {filename: digest(ROOT / filename) for filename in PROTOCOL}:
        raise ValueError("protocol changed during collection")
    write_json(
        ROOT / "observations.json",
        {
            "protocol_hashes": protocol_hashes,
            "source_observations_sha256": digest(NATIVE_ROOT / "observations.json"),
            "diatony_probe_sha256": digest(binary),
            "mido_version": importlib.metadata.version("mido"),
            "rows": rows,
        },
    )
    write_json(ROOT / "summary.json", derive(ROOT, rows))
    check()


def report(root: Path = ROOT) -> str:
    summary = check(root)
    lines = [
        "# Adapted cross-system delivery feasibility",
        "",
        f"**Delivery gate: {summary['delivery_feasibility_gate']}.** "
        "Native-profile gate remains HOLD.",
        "",
        "| Pilot | Delivery profile | Shared delivery pass | Voice relation | Context |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in summary["profile_rows"]:
        item = row["inspection"]
        lines.append(
            f"| {row['id']} | {row['profile']} | {row['shared_delivery_pass']} | "
            f"{item.get('voice_event_relation', '—')} | {item.get('context_relation', '—')} |"
        )
    lines.extend(
        [
            "",
            "Two new Diatony generations retain explicit B/T/A/S capture rows, original native "
            "MIDI and logs alongside adapted MIDI. The benchmark renderer preserves all pitches "
            "and musical times; it declares four voice tracks/channels and adds request-supplied "
            "context. "
            "The independent byte parser and mido agree. Original Diatony delivery remains "
            "UNOBSERVABLE for voice identity and FAIL for context.",
            "",
            "The shared request envelope is frozen in requests/C.json and requests/G.json. "
            "Existing Constraint Music/music21 inputs are mapped retrospectively. Fixed harmony, "
            "given voice and equal generator search spaces are not established. Additional native "
            "presets are disclosed in manifest.json. This supports the next development stage, "
            "not paired generation-rate or cost comparisons.",
            "",
            "Held-out slots: 0. Full tonal obligations, a prospectively paired corpus, attack "
            "denominators and the larger benchmark remain pending. PR37 and the native feasibility "
            "archive are unchanged. No license or external research-run rights are changed.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true")
    action.add_argument("--diatony-binary", type=Path)
    action.add_argument("--report", action="store_true")
    args = parser.parse_args()
    if args.diatony_binary:
        run(args.diatony_binary)
        (ROOT / "FEASIBILITY_REPORT.md").write_text(report())
    elif args.report:
        (ROOT / "FEASIBILITY_REPORT.md").write_text(report())
    else:
        result = check()
        if (ROOT / "FEASIBILITY_REPORT.md").read_text() != report():
            raise ValueError("derived report mismatch")
        print(json.dumps({k: v for k, v in result.items() if k != "profile_rows"}, sort_keys=True))


if __name__ == "__main__":
    main()
