"""Collect fresh workers, seal raw outputs, and replay the complete paired study."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import math
import os
import signal
import subprocess
import sys
import time
import zipfile
from collections import Counter
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

from research.paired_cross_system_v1.adapter import save
from research.paired_cross_system_v1.native import reconstruct
from research.paired_cross_system_v2.contract import admission, content_hash
from research.paired_cross_system_v2.oracle import delivery, semantics
from research.paired_cross_system_v2.reference import accepts

from .adapter import bound_request
from .corpus import sample
from .statistics import paired

SYSTEMS = ("constraint-music", "legacy-constraint-music", "music21", "diatony")
ROOT = Path(__file__).resolve().parent
SEEDS = (7, 19)


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def protocol_hashes() -> dict:
    files = [*ROOT.glob("*.py"), *ROOT.glob("*.cpp"), ROOT / "PROTOCOL.md", ROOT / "manifest.json"]
    # Imported code and native generation source are part of the frozen protocol too.
    repo = ROOT.parent.parent
    imports = [
        repo / "research/paired_cross_system_v1" / f
        for f in ("adapter.py", "contract.py", "render.py", "native.py", "oracle.py")
    ]
    imports += [repo / "research/cross_system_assurance_v1/midi_probe.py"]
    imports += list((repo / "src/constraint_music").rglob("*.py"))
    imports += list((repo / "research/paired_cross_system_v2").glob("*.py"))
    imports += [repo / "research/paired_cross_system_v2/diatony_probe.cpp"]
    imports += [repo / "research/check_paired_v3.py"]
    return {str(p.relative_to(repo)): digest(p.read_bytes()) for p in sorted([*files, *imports])}


def freeze(binary: Path) -> None:
    if (ROOT / "freeze.json").exists():
        raise ValueError("freeze already exists")
    if subprocess.check_output(["git", "status", "--porcelain"], text=True).strip():
        raise ValueError("commit the development-validated protocol first")
    rows = check_phase("development")
    if any(row["status"] in ("HARNESS_ERROR", "BLOCKED") for row in rows):
        raise ValueError("unresolved development harness/inspection error")
    for system in SYSTEMS:
        if not any(
            x["system"] == system and x.get("inspection", {}).get("adapted_pass") for x in rows
        ):
            raise ValueError("development comparability gate failed")
    pins = json.loads((ROOT / "manifest.json").read_text())["pins"]
    dependencies = {p: importlib.metadata.version(p) for p in ("music21", "mido", "ortools")}
    if any(pins[k] != v for k, v in dependencies.items()):
        raise ValueError("dependency pin mismatch")
    save(
        ROOT / "freeze.json",
        {
            "source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip(),
            "protocol_hashes": protocol_hashes(),
            "dependencies": dependencies,
            "binary_sha256": digest(binary.read_bytes()),
            "external_preregistration": False,
        },
    )


def verify_freeze(binary: Path | None = None) -> None:
    frozen = json.loads((ROOT / "freeze.json").read_text())
    if frozen["protocol_hashes"] != protocol_hashes():
        raise ValueError("frozen protocol changed")
    for name, expected in frozen["protocol_hashes"].items():
        data = subprocess.check_output(["git", "show", f"{frozen['source_commit']}:{name}"])
        if digest(data) != expected:
            raise ValueError("source commit differs")
    if binary is not None:
        if digest(binary.read_bytes()) != frozen["binary_sha256"]:
            raise ValueError("binary differs")
        for package, version in frozen["dependencies"].items():
            if importlib.metadata.version(package) != version:
                raise ValueError("dependency differs")
        # The receipt itself must have been committed before any heldout worker starts.
        data = subprocess.check_output(
            ["git", "show", "HEAD:research/paired_cross_system_v3/freeze.json"]
        )
        if json.loads(data) != frozen:
            raise ValueError("commit freeze receipt first")


def inspect(system: str, request: dict, files: dict[str, bytes]) -> dict:
    native_input = json.loads(files["native_input.json"])
    if native_input["request"] != request:
        raise ValueError("native input request mismatch")
    if system == "legacy-constraint-music":
        spec = native_input["spec"]
        if (
            spec["key"] != request["key"]
            or spec["bars"] * 4 != len(request["degrees"])
            or spec["workers"] != 1
            or spec["max_time_seconds"] != 20
            or spec["tempo_bpm"] != request["tempo_bpm"]
        ):
            raise ValueError("native input spec mismatch")
    if system == "music21" and native_input["legacy_spelling"]:
        raise ValueError("legacy spelling used")
    events = json.loads(files["events.json"])
    if system == "constraint-music":
        from constraint_music.harmonization import HarmonizationResult, verify_harmonization
        from constraint_music.harmonization.midi import verify_midi

        result = HarmonizationResult.from_dict(json.loads(files["native_score.json"]))
        expected_request = bound_request(request)
        if native_input["profile"] != "request-bound-satb-v1":
            raise ValueError("wrong CM profile")
        if native_input["workers"] != 1 or native_input["max_time_seconds"] != 20:
            raise ValueError("native search budget differs")
        if native_input["harmonization_request"] != json.loads(
            json.dumps(expected_request.to_dict())
        ):
            raise ValueError("native input obligations differ")
        if result.request != expected_request or verify_harmonization(
            expected_request, result.rows
        ):
            raise ValueError("native score request/semantics differs")
        if verify_midi(expected_request, result.rows, files["native.mid"]):
            raise ValueError("native delivered relation failed")
        captured = sorted(
            [v, pitch, str(i), "1"]
            for i, row in enumerate(result.rows)
            for v, pitch in zip(("Soprano", "Alto", "Tenor", "Bass"), row, strict=True)
        )
    else:
        captured = reconstruct(
            "constraint-music" if system == "legacy-constraint-music" else system, files
        )
    if system == "diatony":
        captured = [[v, p, str(int(a) // 4), "1"] for v, p, a, _ in captured]
    if sorted(captured) != sorted(events):
        raise ValueError("native capture differs from normalized events")
    problems = semantics(request, events)
    if accepts(request, events) != (not problems):
        raise ValueError("independent semantic references disagree")
    adapted = delivery(request, events, files["adapted.mid"], system)
    native = delivery(
        request,
        events,
        files["native.mid"],
        "constraint-music" if system == "legacy-constraint-music" else system,
        native=True,
    )
    metrics = json.loads(files["metrics.json"])
    if not all(type(v) in (int, float) and math.isfinite(v) and v >= 0 for v in metrics.values()):
        raise ValueError("invalid captured metrics")
    return {
        "semantic_issues": problems,
        "reference_agreement": True,
        "adapted": adapted,
        "native": native,
        "adapted_pass": not problems and adapted["status"] == "PASS",
        "native_pass": not problems and native["status"] == "PASS",
        "metrics": metrics,
    }


def launch(system: str, request: dict, seed: int, binary: Path, directory: Path) -> dict:
    directory.mkdir()
    save(directory / "request.json", request)
    if admission(request) != "SUPPORTED":
        save(
            directory / "process.json",
            {"status": admission(request), "seed": seed, "elapsed_seconds": 0.0},
        )
    else:
        start = time.perf_counter()
        environment = {
            **os.environ,
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
        }
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "research.paired_cross_system_v3.adapter",
                system,
                str(directory / "request.json"),
                str(directory),
                str(binary),
                str(seed),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
            env=environment,
        )
        timed_out = False
        try:
            stdout, stderr = process.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate(timeout=5)
        (directory / "worker_stdout.txt").write_bytes(stdout)
        (directory / "worker_stderr.txt").write_bytes(stderr)
        status = (
            "TIMEOUT"
            if timed_out or process.returncode == 4
            else {0: "OUTPUT", 3: "NO_SOLUTION_OR_NATIVE_LIMIT"}.get(
                process.returncode, "HARNESS_ERROR"
            )
        )
        save(
            directory / "process.json",
            {
                "status": status,
                "seed": seed,
                "returncode": process.returncode,
                "elapsed_seconds": round(time.perf_counter() - start, 6),
            },
        )
    files = {p.name: p.read_bytes() for p in directory.iterdir()}
    return derive(system, request, seed, files)


def derive(system: str, request: dict, seed: int, files: dict[str, bytes]) -> dict:
    process = json.loads(files["process.json"])
    if json.loads(files["request.json"]) != request or process["seed"] != seed:
        raise ValueError("attempt request/seed mismatch")
    expected_admission = admission(request)
    status = process["status"]
    if expected_admission != "SUPPORTED" and status != expected_admission:
        raise ValueError("unsupported request launched")
    if expected_admission != "SUPPORTED" and set(files) != {"request.json", "process.json"}:
        raise ValueError("unsupported slot contains generator output")
    if expected_admission == "SUPPORTED" and status not in (
        "OUTPUT",
        "TIMEOUT",
        "NO_SOLUTION_OR_NATIVE_LIMIT",
        "HARNESS_ERROR",
    ):
        raise ValueError("invalid process status")
    row = {
        "request_id": request["request_id"],
        "system": system,
        "seed": seed,
        "status": status,
        "process": process,
        "files": {n: digest(b) for n, b in sorted(files.items())},
    }
    if status == "OUTPUT":
        try:
            if system != "music21" and json.loads(files["native_input.json"])["seed"] != seed:
                raise ValueError("native input seed differs")
            row["inspection"] = inspect(system, request, files)
        except (ValueError, KeyError, TypeError, IndexError, EOFError) as exc:
            row["status"] = "BLOCKED"
            row["block_reason"] = str(exc)
    return row


def collect(phase: str, binary: Path) -> None:
    directory = ROOT / phase
    if (directory / "evidence.zip").exists():
        raise ValueError("phase already collected")
    if phase == "heldout":
        verify_freeze(binary)
    corpus = sample(phase)
    directory.mkdir(exist_ok=True)
    save(directory / "corpus.json", corpus)
    attempts = []
    with (
        TemporaryDirectory() as temporary,
        zipfile.ZipFile(directory / "evidence.zip", "w", zipfile.ZIP_DEFLATED) as archive,
    ):
        for index, entry in enumerate([*corpus["primary"], *corpus["unsupported"]]):
            request = entry["request"]
            for seed in SEEDS:
                order = SYSTEMS[index % len(SYSTEMS) :] + SYSTEMS[: index % len(SYSTEMS)]
                for system in order:
                    slot = f"{request['request_id']}.{system}.{seed}"
                    output = Path(temporary) / slot
                    row = launch(system, request, seed, binary, output)
                    attempts.append(row)
                    for path in sorted(output.iterdir()):
                        archive.write(path, f"{slot}/{path.name}")
                    print(
                        slot,
                        row["status"],
                        row.get("inspection", {}).get("adapted_pass"),
                        flush=True,
                    )
    save(directory / "attempts.json", attempts)
    save(
        directory / "index.json",
        {
            "archive_sha256": digest((directory / "evidence.zip").read_bytes()),
            "corpus_sha256": digest((directory / "corpus.json").read_bytes()),
            "attempts_sha256": digest((directory / "attempts.json").read_bytes()),
        },
    )
    check_phase(phase)


def check_phase(phase: str) -> list:
    directory = ROOT / phase
    index = json.loads((directory / "index.json").read_text())
    for name, field in (
        ("evidence.zip", "archive_sha256"),
        ("corpus.json", "corpus_sha256"),
        ("attempts.json", "attempts_sha256"),
    ):
        if digest((directory / name).read_bytes()) != index[field]:
            raise ValueError(f"{phase} {name} hash mismatch")
    corpus = json.loads((directory / "corpus.json").read_text())
    if corpus != json.loads(json.dumps(sample(phase))):
        raise ValueError("corpus differs from frozen sampling algorithm")
    entries = [*corpus["primary"], *corpus["unsupported"]]
    rows = json.loads((directory / "attempts.json").read_text())
    lookup = {(row["request_id"], row["system"], row["seed"]): row for row in rows}
    planned = {
        (e["request"]["request_id"], s, seed) for e in entries for s in SYSTEMS for seed in SEEDS
    }
    if len(lookup) != len(rows) or set(lookup) != planned:
        raise ValueError("duplicate, missing or unexpected attempts")
    with zipfile.ZipFile(directory / "evidence.zip") as archive:
        members = archive.namelist()
        expected = {
            f"{r['request_id']}.{r['system']}.{r['seed']}/{n}" for r in rows for n in r["files"]
        }
        if len(members) != len(set(members)) or set(members) != expected:
            raise ValueError("archive slot members differ")
        for entry in entries:
            request = entry["request"]
            events = [
                [v, p, str(i), "1"]
                for i, row in enumerate(entry.get("witness", []))
                for v, p in zip(("Soprano", "Alto", "Tenor", "Bass"), row, strict=True)
            ]
            if "witness" in entry and (semantics(request, events) or not accepts(request, events)):
                raise ValueError("input feasibility witness failed")
            for system in SYSTEMS:
                for seed in SEEDS:
                    row = lookup[request["request_id"], system, seed]
                    slot = f"{request['request_id']}.{system}.{seed}"
                    files = {name: archive.read(f"{slot}/{name}") for name in row["files"]}
                    if derive(system, request, seed, files) != row:
                        raise ValueError("captured attempt differs from replay")
    return rows


def analyze() -> dict:
    verify_freeze()
    rows = check_phase("heldout")
    corpus = json.loads((ROOT / "heldout/corpus.json").read_text())
    lookup = {(r["request_id"], r["system"], r["seed"]): r for r in rows}
    primary, native = {}, {}
    for system in SYSTEMS:
        primary[system], native[system] = [], []
        for entry in corpus["primary"]:
            attempts = [lookup[entry["request"]["request_id"], system, seed] for seed in SEEDS]
            primary[system].append(
                all(r.get("inspection", {}).get("adapted_pass", False) for r in attempts)
            )
            native[system].append(
                all(r.get("inspection", {}).get("native_pass", False) for r in attempts)
            )
    comparisons = {s: paired(primary["constraint-music"], primary[s]) for s in SYSTEMS[1:]}
    per_request = [
        {
            "request_id": e["request"]["request_id"],
            "pass_both_runs": {s: primary[s][i] for s in SYSTEMS},
            "native_pass_both_runs": {s: native[s][i] for s in SYSTEMS},
            "cm_minus_competitor": {
                s: int(primary["constraint-music"][i]) - int(primary[s][i]) for s in SYSTEMS[1:]
            },
        }
        for i, e in enumerate(corpus["primary"])
    ]
    fingerprints = [
        content_hash({k: v for k, v in e["request"].items() if k != "request_id"})
        for e in corpus["primary"]
    ]
    return {
        "primary_n": len(corpus["primary"]),
        "attempt_n": len(rows),
        "statuses": {
            s: dict(Counter(r["status"] for r in rows if r["system"] == s)) for s in SYSTEMS
        },
        "adapted_reproducible_pass": {s: sum(v) for s, v in primary.items()},
        "native_reproducible_pass": {s: sum(v) for s, v in native.items()},
        "paired_comparisons": comparisons,
        "per_request": per_request,
        "exact_duplicate_draws": len(fingerprints) - len(set(fingerprints)),
        "improvement_established": comparisons["legacy-constraint-music"]["superiority_gate"]
        and not any(r["status"] in ("HARNESS_ERROR", "BLOCKED") for r in rows),
        "superiority_established": all(c["superiority_gate"] for c in comparisons.values())
        and not any(r["status"] in ("HARNESS_ERROR", "BLOCKED") for r in rows),
        "population_scope": "IID feasible requests from the declared grammar, "
        "conditioned adapters and common renderer",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("development", "freeze", "heldout", "check", "analyze"))
    parser.add_argument("--binary", type=Path)
    args = parser.parse_args()
    if args.command in ("development", "heldout"):
        collect(args.command, args.binary.resolve())
    elif args.command == "freeze":
        freeze(args.binary.resolve())
    elif args.command == "check":
        from research.paired_cross_system_v2.diagnostic import check as check_diagnostic

        from .report import report

        check_diagnostic()
        verify_freeze()
        check_phase("development")
        check_phase("heldout")
        summary = analyze()
        if summary != json.loads((ROOT / "summary.json").read_text()):
            raise ValueError("summary differs from recomputed evidence")
        if report(summary) != (ROOT / "REPORT.md").read_text():
            raise ValueError("report differs from computed evidence")
        print("v3 raw replay and paired analysis: PASS")
    else:
        save(ROOT / "summary.json", analyze())
