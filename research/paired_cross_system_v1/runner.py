"""Freeze, collect and replay all planned paired attempts; preserve actual bytes in ZIP."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import signal
import subprocess
import sys
import time
import zipfile
from collections import Counter
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from .adapter import save
from .contract import SYSTEMS, admission, canonical, content_hash
from .controls import controls
from .faults import FAULTS, mutate, scaled
from .native import binding, reconstruct
from .oracle import delivery, evaluate, semantics
from .reference import valid as reference_valid

ROOT = Path(__file__).resolve().parent


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def protocol_hashes(root: Path) -> dict[str, str]:
    paths = [
        *root.glob("*.py"),
        *root.glob("*.cpp"),
        root / "manifest.json",
        root / "corpus.json",
        root / "PROTOCOL.md",
        root / "support.json",
    ]
    return {p.name: digest(p.read_bytes()) for p in sorted(paths)}


def freeze(binary: Path) -> None:
    if (ROOT / "freeze.json").exists():
        raise ValueError("freeze already exists")
    if subprocess.check_output(["git", "status", "--porcelain"], text=True).strip():
        raise ValueError("commit the development-validated protocol before freezing")
    development = check_phase(ROOT, "development")
    for system in SYSTEMS:
        if not any(
            row["system"] == system
            and row.get("inspection", {}).get("evaluation", {}).get("status") == "PASS"
            for row in development
        ):
            raise ValueError("development comparability gate failed")
    if any(
        not row["inspection"]["reference_agreement"]
        for row in development
        if row["generation_status"] == "OUTPUT"
    ):
        raise ValueError("development semantic references disagree")
    pins = json.loads((ROOT / "manifest.json").read_text())["pins"]
    dependencies = {
        name: importlib.metadata.version(name) for name in ("music21", "mido", "ortools")
    }
    if any(dependencies[name] != pins[name] for name in dependencies):
        raise ValueError("dependency pins differ")
    save(
        ROOT / "freeze.json",
        {
            "schema_version": 1,
            "protocol_hashes": protocol_hashes(ROOT),
            "source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip(),
            "binary_sha256": digest(binary.read_bytes()),
            "dependencies": dependencies,
            "python": platform.python_version(),
            "platform": platform.platform(),
            "preregistered_externally": False,
        },
    )


def check_freeze(root: Path) -> dict[str, Any]:
    frozen = json.loads((root / "freeze.json").read_text())
    if frozen["protocol_hashes"] != protocol_hashes(root):
        raise ValueError("frozen protocol changed")
    for filename, expected in frozen["protocol_hashes"].items():
        path = "research/paired_cross_system_v1/" + filename
        data = subprocess.check_output(["git", "show", frozen["source_commit"] + ":" + path])
        if digest(data) != expected:
            raise ValueError("frozen Git source mismatch")
    return frozen


def put(archive: zipfile.ZipFile, name: str, data: bytes) -> str:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, data)
    return digest(data)


def inspect(request: dict[str, Any], system: str, files: dict[str, bytes]) -> dict[str, Any]:
    try:
        return inspect_output(request, system, files)
    except (KeyError, ValueError, TypeError, IndexError, ZeroDivisionError, SyntaxError) as exc:
        return {
            "request_pass": False,
            "source_relation_pass": False,
            "semantic_pass": False,
            "semantic_issues": ["OUTPUT_ADMISSION"],
            "reference_agreement": False,
            "delivered": {"status": "BLOCKED", "issues": ["OUTPUT_ADMISSION"]},
            "native_delivery": {"status": "UNOBSERVABLE", "issues": ["OUTPUT_ADMISSION"]},
            "evaluation": {
                "status": "BLOCKED",
                "boundary": "artifact",
                "issues": ["OUTPUT_ADMISSION"],
                "error_type": type(exc).__name__,
            },
        }


def inspect_output(request: dict[str, Any], system: str, files: dict[str, bytes]) -> dict[str, Any]:
    artifact = json.loads(files["artifact.json"])
    source = reconstruct(system, files)
    request_ok = binding(system, request, files) and canonical(artifact["request"]) == canonical(
        request
    )
    source_ok = source == artifact["events"]
    issues = semantics(request, source)
    agreement = (not issues) == reference_valid(request, source)
    evaluation = evaluate(request, artifact, files["delivered.mid"], system)
    if not request_ok:
        evaluation = {"status": "REJECT", "boundary": "request", "issues": ["NATIVE_INPUT_BINDING"]}
    elif not source_ok:
        evaluation = {
            "status": "REJECT",
            "boundary": "artifact",
            "issues": ["NATIVE_SCORE_RELATION"],
        }
    elif not agreement:
        evaluation = {
            "status": "BLOCKED",
            "boundary": "artifact",
            "issues": ["ORACLE_DISAGREEMENT"],
        }
    return {
        "request_pass": request_ok,
        "source_relation_pass": source_ok,
        "semantic_pass": not issues and agreement and source_ok,
        "semantic_issues": issues,
        "reference_agreement": agreement,
        "delivered": delivery(request, source, files["delivered.mid"], system),
        "native_delivery": delivery(request, source, files["native.mid"], system, native=True),
        "evaluation": evaluation,
    }


def launch(
    system: str, request: dict[str, Any], binary: Path, directory: Path
) -> tuple[str, float]:
    save(directory / "request.json", request)
    eligibility = admission(request)
    if eligibility != "SUPPORTED":
        return eligibility, 0.0
    environment = dict(os.environ)
    environment.update(
        {
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "PYTHONHASHSEED": "7",
        }
    )
    command = [
        sys.executable,
        "-m",
        "research.paired_cross_system_v1.adapter",
        system,
        str(directory / "request.json"),
        str(directory),
        str(binary),
    ]
    start = time.perf_counter()
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=30)
            if process.returncode == 0:
                status = "OUTPUT"
            elif b"NO_SOLUTION" in stderr or b"NoSolutionError" in stderr:
                status = "NO_SOLUTION"
            elif b"TIMEOUT" in stderr:
                status = "TIMEOUT"
            else:
                status = "HARNESS_ERROR"
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
            status = "TIMEOUT"
        (directory / "worker_stdout.txt").write_bytes(stdout)
        (directory / "worker_stderr.txt").write_bytes(stderr)
    except OSError as exc:
        (directory / "worker_stderr.txt").write_text(str(exc))
        status = "HARNESS_ERROR"
    return status, round(time.perf_counter() - start, 6)


def collect(phase: str, binary: Path) -> None:
    if phase not in ("development", "heldout"):
        raise ValueError("unknown phase")
    target = ROOT / phase
    if target.exists():
        raise ValueError("archive exists; reruns require a new study version")
    if phase == "heldout":
        frozen = check_freeze(ROOT)
        if digest(binary.read_bytes()) != frozen["binary_sha256"]:
            raise ValueError("probe binary changed")
        if subprocess.check_output(["git", "status", "--porcelain"], text=True).strip():
            raise ValueError("commit the freeze receipt before held-out collection")
        if (
            subprocess.check_output(
                ["git", "show", "HEAD:research/paired_cross_system_v1/freeze.json"]
            )
            != (ROOT / "freeze.json").read_bytes()
        ):
            raise ValueError("freeze receipt is not committed")
    baseline = json.loads((ROOT / "manifest.json").read_text())["baseline_commit"]
    for path in Path("src/constraint_music").glob("*.py"):
        if path.read_bytes() != subprocess.check_output(
            ["git", "show", baseline + ":" + path.as_posix()]
        ):
            raise ValueError("pinned generator source differs")
    snapshot = protocol_hashes(ROOT)
    corpus = [c for c in json.loads((ROOT / "corpus.json").read_text()) if c["phase"] == phase]
    target.mkdir()
    rows = []
    with (
        zipfile.ZipFile(target / "evidence.zip", "w") as archive,
        TemporaryDirectory() as temporary,
    ):
        for index, case in enumerate(corpus):
            order = SYSTEMS[index % 3 :] + SYSTEMS[: index % 3]
            for system in order:
                request = case["request"]
                identity = request["request_id"] + "." + system
                directory = Path(temporary) / identity
                directory.mkdir()
                status, elapsed = launch(system, request, binary.resolve(), directory)
                files = {p.name: p.read_bytes() for p in directory.iterdir() if p.is_file()}
                row = {
                    "id": identity,
                    "system": system,
                    "request_id": request["request_id"],
                    "request_sha256": content_hash(request),
                    "family": case["family"],
                    "primary": case["eligible"],
                    "generation_status": status,
                    "wall_seconds": elapsed,
                    "files": {},
                }
                if status == "OUTPUT":
                    row["inspection"] = inspect(request, system, files)
                    if "worker_metrics.json" in files:
                        row["metrics"] = json.loads(files["worker_metrics.json"])
                row["files"] = {
                    "attempts/" + identity + "/" + name: put(
                        archive, "attempts/" + identity + "/" + name, data
                    )
                    for name, data in sorted(files.items())
                }
                rows.append(row)
                print(f"{phase}: {identity}: {status}", flush=True)
    (target / "attempts.jsonl").write_text("".join(canonical(r) + "\n" for r in rows))
    save(
        target / "index.json",
        {
            "protocol_hashes": snapshot,
            "collection_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip(),
            "archive_sha256": digest((target / "evidence.zip").read_bytes()),
            "rows_sha256": digest((target / "attempts.jsonl").read_bytes()),
        },
    )
    if snapshot != protocol_hashes(ROOT):
        raise ValueError("protocol changed during collection")
    check_phase(ROOT, phase)


def read_rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def attempt_files(archive: zipfile.ZipFile, row: dict[str, Any]) -> dict[str, bytes]:
    files = {}
    for name, expected in row["files"].items():
        if name.startswith("/") or ".." in Path(name).parts:
            raise ValueError("unsafe evidence path")
        data = archive.read(name)
        if digest(data) != expected:
            raise ValueError("evidence hash mismatch")
        files[Path(name).name] = data
    return files


def check_phase(root: Path, phase: str) -> list[dict[str, Any]]:
    target = root / phase
    index = json.loads((target / "index.json").read_text())
    if index["protocol_hashes"] != protocol_hashes(root):
        raise ValueError("collection protocol hash mismatch")
    if phase == "heldout":
        receipt = subprocess.check_output(
            [
                "git",
                "show",
                index["collection_commit"] + ":research/paired_cross_system_v1/freeze.json",
            ]
        )
        if receipt != (root / "freeze.json").read_bytes():
            raise ValueError("collection commit does not contain the frozen receipt")
    if index["archive_sha256"] != digest((target / "evidence.zip").read_bytes()):
        raise ValueError("archive hash mismatch")
    if index["rows_sha256"] != digest((target / "attempts.jsonl").read_bytes()):
        raise ValueError("row hash mismatch")
    rows = read_rows(target / "attempts.jsonl")
    corpus = {
        c["request"]["request_id"]: c
        for c in json.loads((root / "corpus.json").read_text())
        if c["phase"] == phase
    }
    expected = {r + "." + system for r in corpus for system in SYSTEMS}
    if len(rows) != len(expected) or {r["id"] for r in rows} != expected:
        raise ValueError("attempt slots missing/duplicate")
    with zipfile.ZipFile(target / "evidence.zip") as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != {p for r in rows for p in r["files"]}:
            raise ValueError("evidence member coverage")
        for row in rows:
            case = corpus[row["request_id"]]
            request = case["request"]
            if row["id"] != row["request_id"] + "." + row["system"] or row["system"] not in SYSTEMS:
                raise ValueError("paired identity mismatch")
            if row["family"] != case["family"] or row["primary"] != case["eligible"]:
                raise ValueError("case stratum mismatch")
            if row["request_sha256"] != content_hash(request):
                raise ValueError("trusted request hash mismatch")
            files = attempt_files(archive, row)
            if json.loads(files["request.json"]) != request:
                raise ValueError("request bytes mismatch")
            if row["generation_status"] == "OUTPUT":
                if inspect(request, row["system"], files) != row["inspection"]:
                    raise ValueError("independent inspection mismatch")
            elif row["generation_status"] not in (
                "TIMEOUT",
                "NO_SOLUTION",
                "HARNESS_ERROR",
                "UNSUPPORTED",
                "BLOCKED",
            ):
                raise ValueError("unknown generation status")
            if not case["eligible"] and row["generation_status"] != admission(request):
                raise ValueError("unsupported request miscounted as generation failure")
    return rows


def fault_evaluation(
    request: dict[str, Any], artifact: dict[str, Any], data: bytes, system: str
) -> dict[str, Any]:
    if (not semantics(request, artifact["events"])) != reference_valid(request, artifact["events"]):
        return {"status": "BLOCKED", "boundary": "artifact", "issues": ["ORACLE_DISAGREEMENT"]}
    return evaluate(request, artifact, data, system)


def attacks() -> None:
    check_freeze(ROOT)
    rows = check_phase(ROOT, "heldout")
    target = ROOT / "heldout"
    if (target / "faults.jsonl").exists():
        raise ValueError("fault archive exists")
    requests = {
        c["request"]["request_id"]: c["request"]
        for c in json.loads((ROOT / "corpus.json").read_text())
    }
    faults = []
    members: dict[str, bytes] = {}
    with zipfile.ZipFile(target / "evidence.zip") as originals:
        for attempt in rows:
            if not attempt["primary"]:
                continue
            eligible = (
                attempt["generation_status"] == "OUTPUT"
                and attempt["inspection"]["evaluation"]["status"] == "PASS"
            )
            files = attempt_files(originals, attempt) if eligible else {}
            for name in (*FAULTS, "ppqn_control"):
                identity = attempt["id"] + "." + name
                row = {
                    "id": identity,
                    "attempt_id": attempt["id"],
                    "fault": name,
                    "eligible": eligible,
                }
                if not eligible:
                    row.update({"status": "INAPPLICABLE", "reason": "BASELINE_NOT_ACCEPTED"})
                else:
                    artifact = json.loads(files["artifact.json"])
                    data = files["delivered.mid"]
                    changed, output = (
                        (artifact, scaled(data))
                        if name == "ppqn_control"
                        else mutate(name, artifact, data)
                    )
                    if name != "ppqn_control" and changed == artifact and output == data:
                        raise ValueError("no-op attack")
                    a_bytes = canonical(changed).encode()
                    a_name, m_name = (
                        "blobs/" + digest(a_bytes) + ".json",
                        "blobs/" + digest(output) + ".mid",
                    )
                    members[a_name], members[m_name] = a_bytes, output
                    verdict = fault_evaluation(
                        requests[attempt["request_id"]], changed, output, attempt["system"]
                    )
                    row.update(
                        {
                            "status": verdict["status"],
                            "verdict": verdict,
                            "artifact_member": a_name,
                            "midi_member": m_name,
                            "artifact_sha256": digest(a_bytes),
                            "midi_sha256": digest(output),
                        }
                    )
                faults.append(row)
    with zipfile.ZipFile(target / "fault_bytes.zip", "w") as archive:
        for name, data in sorted(members.items()):
            put(archive, name, data)
    (target / "faults.jsonl").write_text("".join(canonical(r) + "\n" for r in faults))
    hand = []
    for identity, request, artifact, data in controls():
        hand.append(
            {
                "id": identity,
                "reference_pass": reference_valid(request, artifact["events"]),
                "semantic_issues": semantics(request, artifact["events"]),
                "verdict": evaluate(request, artifact, data, "constraint-music"),
            }
        )
    save(target / "hand_controls.json", hand)
    save(
        target / "fault_index.json",
        {
            p.name: digest(p.read_bytes())
            for p in (
                target / "fault_bytes.zip",
                target / "faults.jsonl",
                target / "hand_controls.json",
            )
        },
    )


def check_faults(root: Path, attempts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    target = root / "heldout"
    index = json.loads((target / "fault_index.json").read_text())
    if set(index) != {"fault_bytes.zip", "faults.jsonl", "hand_controls.json"}:
        raise ValueError("fault index coverage")
    for name, expected in index.items():
        if digest((target / name).read_bytes()) != expected:
            raise ValueError("fault hash mismatch")
    faults = read_rows(target / "faults.jsonl")
    primary = {a["id"]: a for a in attempts if a["primary"]}
    expected = {a + "." + f for a in primary for f in (*FAULTS, "ppqn_control")}
    if len(faults) != len(expected) or {f["id"] for f in faults} != expected:
        raise ValueError("fault slots missing/duplicate")
    requests = {
        c["request"]["request_id"]: c["request"]
        for c in json.loads((root / "corpus.json").read_text())
    }
    used = set()
    with (
        zipfile.ZipFile(target / "evidence.zip") as baseline,
        zipfile.ZipFile(target / "fault_bytes.zip") as mutations,
    ):
        for row in faults:
            attempt = primary[row["attempt_id"]]
            if row["id"] != row["attempt_id"] + "." + row["fault"] or row["fault"] not in (
                *FAULTS,
                "ppqn_control",
            ):
                raise ValueError("fault identity mismatch")
            eligible = (
                attempt["generation_status"] == "OUTPUT"
                and attempt["inspection"]["evaluation"]["status"] == "PASS"
            )
            if eligible != row["eligible"]:
                raise ValueError("fault eligibility mismatch")
            if not eligible:
                if row["status"] != "INAPPLICABLE" or row["reason"] != "BASELINE_NOT_ACCEPTED":
                    raise ValueError("inapplicable count mismatch")
                continue
            files = attempt_files(baseline, attempt)
            original = json.loads(files["artifact.json"])
            changed, data = (
                (original, scaled(files["delivered.mid"]))
                if row["fault"] == "ppqn_control"
                else mutate(row["fault"], original, files["delivered.mid"])
            )
            a_bytes = mutations.read(row["artifact_member"])
            m_bytes = mutations.read(row["midi_member"])
            used.update((row["artifact_member"], row["midi_member"]))
            if digest(a_bytes) != row["artifact_sha256"] or digest(m_bytes) != row["midi_sha256"]:
                raise ValueError("mutant hash mismatch")
            if json.loads(a_bytes) != changed or m_bytes != data:
                raise ValueError("mutation replay mismatch")
            verdict = fault_evaluation(
                requests[attempt["request_id"]], changed, data, attempt["system"]
            )
            if verdict != row["verdict"] or verdict["status"] != row["status"]:
                raise ValueError("fault verdict mismatch")
        names = mutations.namelist()
        if set(names) != used or len(names) != len(set(names)):
            raise ValueError("mutation member coverage")
    expected_hand = [
        {
            "id": identity,
            "reference_pass": reference_valid(request, artifact["events"]),
            "semantic_issues": semantics(request, artifact["events"]),
            "verdict": evaluate(request, artifact, data, "constraint-music"),
        }
        for identity, request, artifact, data in controls()
    ]
    if json.loads((target / "hand_controls.json").read_text()) != expected_hand:
        raise ValueError("hand control replay mismatch")
    return faults


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("development", "freeze", "heldout", "attacks", "check"))
    parser.add_argument("--binary", type=Path)
    args = parser.parse_args()
    if args.action == "freeze":
        freeze(args.binary)
    elif args.action in ("development", "heldout"):
        collect(args.action, args.binary)
    elif args.action == "attacks":
        attacks()
    else:
        check_freeze(ROOT)
        check_phase(ROOT, "development")
        attempts = check_phase(ROOT, "heldout")
        faults = check_faults(ROOT, attempts)
        print(
            canonical(
                {
                    "attempts": len(attempts),
                    "fault_and_equivalence_slots": len(faults),
                    "generation_statuses": dict(Counter(a["generation_status"] for a in attempts)),
                }
            )
        )


if __name__ == "__main__":
    main()
