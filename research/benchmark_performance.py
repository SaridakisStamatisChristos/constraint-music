"""EH-11 controlled performance, memory, yield, and variance benchmark."""
from __future__ import annotations

import argparse
import json
import math
import os
import platform
import re
import resource
import statistics
import subprocess
import sys
import tempfile
import time
import tracemalloc
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any, Iterator

from constraint_music.certification import verify_artifact
from constraint_music.delivery import RenderProfile, verify_delivery
from constraint_music.errors import NoSolutionError
from constraint_music.midi import write_midi
from constraint_music.models import GenerationSpec
from constraint_music.phrase import PhraseSpec
from constraint_music.provenance import artifact_payload, load_result_json
from constraint_music.search import DEFAULT_OBJECTIVE_WEIGHTS
from constraint_music.solver import ConstraintMusicSolver
from constraint_music.verifier import verify_result

VERSION = "eh11-v1"
RAW = "eh11_performance_raw.jsonl"
SUMMARY = "eh11_performance_summary.json"
ENV = "eh11_environment.json"
PROFILES = (
    "base_satb", "rhythm_motifs", "phrase_grammar", "expanded_sevenths",
    "applied_harmony", "secondary_harmony", "borrowed_harmony",
    "declared_modulation", "combined_borrowed_modulation",
)


@dataclass(frozen=True, slots=True)
class Case:
    workload: str
    profile: str
    bars: int
    seed: int
    workers: int
    worker_mode: str
    time_limit_seconds: float
    multi_output_count: int = 1


class TimedSolver(ConstraintMusicSolver):
    def __init__(self) -> None:
        super().__init__()
        self.compile_seconds = 0.0

    def _compile(self, spec: GenerationSpec, weights: Any) -> Any:
        start = time.perf_counter()
        try:
            return super()._compile(spec, weights)
        finally:
            self.compile_seconds += time.perf_counter() - start


def build_spec(case: Case) -> tuple[GenerationSpec | None, str | None]:
    v: dict[str, Any] = {
        "bars": case.bars, "beats_per_bar": 4, "subdivisions_per_beat": 1,
        "seed": case.seed, "workers": case.workers,
        "max_time_seconds": case.time_limit_seconds,
        "tension_curve": (0.05, 0.22, 0.52, 0.84, 0.36, 0.04),
    }
    if case.profile == "base_satb":
        pass
    elif case.profile == "rhythm_motifs":
        if case.bars < 3:
            return None, "motif profile needs source bar 0 and target bar 2"
        v.update(
            subdivisions_per_beat=2, rhythm_enabled=True, min_onsets_per_bar=5,
            max_onsets_per_bar=6, min_rests_per_bar=1, max_rests_per_bar=2,
            min_ties_per_bar=1, max_ties_per_bar=1, max_consecutive_rests=1,
            max_tie_steps=1, motif_relation="transpose", motif_source_bar=0,
            motif_target_bar=2, motif_length_steps=4, motif_transpose_semitones=12,
        )
    elif case.profile == "phrase_grammar":
        if case.bars < 2:
            return None, "answer phrase profile needs at least two bars"
        a = case.bars // 2
        b = case.bars - a
        v["phrases"] = (
            PhraseSpec("A", 0, a, "antecedent", "dominant_open"),
            PhraseSpec("B", a, b, "consequent", "dominant_to_tonic", "answer", "A",
                       7, min(4, a * 4, b * 4)),
        )
    elif case.profile == "expanded_sevenths":
        v.update(harmony_vocabulary="triads+sevenths", minimum_seventh_chords=1)
    elif case.profile == "applied_harmony":
        v.update(harmony_vocabulary="triads+sevenths", minimum_seventh_chords=1,
                 tonicization_enabled=True, minimum_applied_dominants=1)
    elif case.profile == "secondary_harmony":
        v.update(require_authentic_cadence=False, avoid_parallel_perfects=False,
                 harmony_vocabulary="triads+sevenths", minimum_seventh_chords=1,
                 secondary_leading_tone_seventh_enabled=True,
                 minimum_secondary_leading_tone_seventh_chords=1)
    elif case.profile == "borrowed_harmony":
        v.update(modal_mixture_enabled=True, minimum_borrowed_chords=1)
    elif case.profile in {"declared_modulation", "combined_borrowed_modulation"}:
        beats = case.bars * 4
        boundary = max(2, min(beats - 2, beats // 2))
        v.update(require_authentic_cadence=False, avoid_parallel_perfects=False,
                 modulation_enabled=True, modulation_destination_key="G",
                 modulation_boundary_beat=boundary)
        if case.profile == "combined_borrowed_modulation":
            v.update(harmony_vocabulary="triads+sevenths", minimum_seventh_chords=1,
                     modal_mixture_enabled=True, minimum_borrowed_chords=1)
    else:
        raise ValueError(f"unknown profile {case.profile!r}")
    return GenerationSpec(**v), None


def load_config(path: Path) -> dict[str, Any]:
    c = json.loads(path.read_text(encoding="utf-8"))
    if c.get("benchmark_version") != VERSION:
        raise ValueError("benchmark version mismatch")
    if tuple(c["bar_sizes"]) != (1, 2, 4, 8, 16, 32):
        raise ValueError("bar_sizes must be exactly 1,2,4,8,16,32")
    if len(set(c["seeds"])) < 3:
        raise ValueError("at least three distinct fixed seeds are required")
    if set(c["profiles"]) != set(PROFILES):
        raise ValueError("profile set does not match EH-11")
    return c


def matrix(c: Mapping[str, Any]) -> tuple[Case, ...]:
    throughput = max(1, min(int(c["throughput_worker_cap"]), os.cpu_count() or 1))
    modes = [(1, "single")] + ([(throughput, "throughput")] if throughput > 1 else [])
    rows: list[Case] = []
    for profile in c["profiles"]:
        for bars in c["bar_sizes"]:
            for seed in c["seeds"]:
                for workers, mode in modes:
                    rows.append(Case("single", profile, bars, seed, workers, mode,
                                     float(c["time_limit_seconds"])))
    m = c["multi_output"]
    for bars in m["bar_sizes"]:
        for seed in m["seeds"]:
            for workers, mode in modes:
                rows.append(Case("multi_output", m["profile"], bars, seed, workers, mode,
                                 float(c["time_limit_seconds"]), int(m["count"])))
    return tuple(rows)


def status_from(exc: NoSolutionError) -> str:
    m = re.search(r"\((OPTIMAL|FEASIBLE|INFEASIBLE|MODEL_INVALID|UNKNOWN)\)", str(exc))
    return m.group(1) if m else "NO_SOLUTION"


def rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


@contextmanager
def strict_semantic_timer() -> Iterator[dict[str, float | int]]:
    import constraint_music.certification as certification_module
    import constraint_music.provenance as provenance_module
    import constraint_music.verifier as verifier_module

    original_cert = certification_module.verify_result
    original_prov = provenance_module.verify_result
    timing: dict[str, float | int] = {"seconds": 0.0, "calls": 0}

    def wrapped(result: Any) -> Any:
        start = time.perf_counter()
        try:
            return verifier_module.verify_result(result)
        finally:
            timing["seconds"] = float(timing["seconds"]) + time.perf_counter() - start
            timing["calls"] = int(timing["calls"]) + 1

    certification_module.verify_result = wrapped
    provenance_module.verify_result = wrapped
    try:
        yield timing
    finally:
        certification_module.verify_result = original_cert
        provenance_module.verify_result = original_prov


def one(case: Case, spec: GenerationSpec) -> dict[str, Any]:
    solver = TimedSolver()
    start = time.perf_counter()
    result = solver.generate(spec)
    generation = time.perf_counter() - start
    start = time.perf_counter()
    semantic = verify_result(result)
    semantic_s = time.perf_counter() - start
    start = time.perf_counter()
    payload = artifact_payload(result)
    artifact_s = time.perf_counter() - start
    with tempfile.TemporaryDirectory(prefix="eh11-") as d:
        artifact_path = Path(d) / "result.json"
        artifact_path.write_text(json.dumps(payload), encoding="utf-8")
        start = time.perf_counter()
        parsed, raw = load_result_json(artifact_path)
        parse_s = time.perf_counter() - start
        with strict_semantic_timer() as strict_semantics:
            start = time.perf_counter()
            strict = verify_artifact(raw, expected_spec=spec)
            strict_s = time.perf_counter() - start
        midi = Path(d) / "delivery.mid"
        start = time.perf_counter()
        write_midi(result, midi, profile=RenderProfile.CERTIFIED_SATB)
        export_s = time.perf_counter() - start
        start = time.perf_counter()
        delivery = verify_delivery(parsed, midi)
        delivery_s = time.perf_counter() - start
    strict_semantic_s = float(strict_semantics["seconds"])
    binding_s = max(0.0, strict_s - strict_semantic_s)
    certification = strict_s + delivery_s
    return {
        "generated_count": 1, "accepted_count": int(strict.accepted),
        "released_count": int(strict.accepted and delivery.accepted),
        "solver_status": result.solver_status,
        "generation_total_seconds": generation,
        "compile_seconds": solver.compile_seconds,
        "solve_seconds": float(result.wall_time_seconds),
        "generation_residual_seconds": max(
            0.0, generation - solver.compile_seconds - result.wall_time_seconds
        ),
        "semantic_verification_seconds": semantic_s,
        "artifact_build_seconds": artifact_s, "artifact_parse_seconds": parse_s,
        "strict_artifact_certification_seconds": strict_s,
        "strict_semantic_recheck_seconds": strict_semantic_s,
        "strict_semantic_recheck_calls": int(strict_semantics["calls"]),
        "integrity_request_binding_exclusive_seconds": binding_s,
        "export_seconds": export_s, "parseback_and_delivery_seconds": delivery_s,
        "certification_total_seconds": certification,
        "verification_overhead_ratio": certification / generation if generation else None,
        "semantic_valid": semantic.valid, "strict_artifact_accepted": strict.accepted,
        "delivery_accepted": delivery.accepted,
    }


def multi(case: Case, spec: GenerationSpec) -> dict[str, Any]:
    solver = ConstraintMusicSolver()
    results: list[Any] = []
    stopped = "COMPLETE"
    start = time.perf_counter()
    for _ in range(case.multi_output_count):
        try:
            result = solver._solve(
                spec,
                DEFAULT_OBJECTIVE_WEIGHTS,
                tuple(results),
                ("melody",),
            )
        except NoSolutionError as exc:
            stopped = status_from(exc)
            break
        results.append(result)
    elapsed = time.perf_counter() - start
    accepted = sum(verify_result(result).valid for result in results)
    return {
        "generated_count": len(results),
        "accepted_count": accepted,
        "released_count": 0,
        "solver_status": stopped,
        "multi_output_elapsed_seconds": elapsed,
        "multi_output_solutions_per_second": len(results) / elapsed if elapsed else None,
    }


def execute(case: Case) -> dict[str, Any]:
    tracemalloc.start()
    started = time.perf_counter()
    row: dict[str, Any] = {"benchmark_version": VERSION, **asdict(case),
                           "attempted_count": 1, "excluded_count": 0,
                           "generated_count": 0, "accepted_count": 0, "released_count": 0,
                           "started_at_utc": datetime.now(UTC).isoformat()}
    try:
        spec, exclusion = build_spec(case)
        if spec is None:
            row.update(outcome="excluded", exclusion_reason=exclusion,
                       excluded_count=1, solver_status="NOT_RUN")
            return row
        row.update(one(case, spec) if case.workload == "single" else multi(case, spec))
        row["outcome"] = "success"
        return row
    except NoSolutionError as exc:
        status = status_from(exc)
        row.update(outcome="no_solution", solver_status=status, error=str(exc),
                   no_solution_class="infeasible" if status == "INFEASIBLE" else
                   "unknown" if status == "UNKNOWN" else "other")
        return row
    except Exception as exc:
        row.update(outcome="internal_error", solver_status="ERROR",
                   error_type=type(exc).__name__, error=str(exc))
        return row
    finally:
        row["attempt_elapsed_seconds"] = time.perf_counter() - started
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        row["python_tracemalloc_peak_bytes"] = peak
        row["peak_rss_bytes"] = rss_bytes()
        row["finished_at_utc"] = datetime.now(UTC).isoformat()


def run(c: Mapping[str, Any]) -> list[dict[str, Any]]:
    cases = matrix(c)
    rows: list[dict[str, Any]] = []
    for index, case in enumerate(cases, 1):
        cmd = [sys.executable, "-m", "research.benchmark_performance", "--worker-json",
               json.dumps(asdict(case), separators=(",", ":"))]
        p = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if p.returncode:
            row = {"benchmark_version": VERSION, **asdict(case), "attempted_count": 1,
                   "excluded_count": 0, "generated_count": 0, "accepted_count": 0,
                   "released_count": 0, "outcome": "worker_crash", "solver_status": "ERROR",
                   "worker_returncode": p.returncode, "worker_stderr": p.stderr[-4000:]}
        else:
            row = json.loads(p.stdout)
        row.update(matrix_index=index, matrix_total=len(cases))
        rows.append(row)
        print(
            f"[{index}/{len(cases)}] {case.profile} {case.bars}b "
            f"{case.worker_mode}: {row['outcome']}",
            file=sys.stderr,
            flush=True,
        )
    return rows


def quantile(v: Sequence[float], p: float) -> float | None:
    if len(v) < 5:
        return None
    s = sorted(v)
    pos = (len(s) - 1) * p
    lo = math.floor(pos)
    hi = math.ceil(pos)
    return s[lo] if lo == hi else s[lo] * (hi - pos) + s[hi] * (pos - lo)


def stats(v: Sequence[float]) -> dict[str, float | int | None]:
    if not v:
        return {"n": 0, "median": None, "mean": None, "min": None, "max": None,
                "stdev": None, "cv": None, "p90": None, "p95": None}
    mean = statistics.fmean(v)
    sd = statistics.stdev(v) if len(v) > 1 else 0.0
    return {"n": len(v), "median": statistics.median(v), "mean": mean, "min": min(v),
            "max": max(v), "stdev": sd, "cv": sd / mean if mean else None,
            "p90": quantile(v, .90), "p95": quantile(v, .95)}


def summarize(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    singles = [r for r in rows if r["workload"] == "single"]
    excluded = sum(int(r.get("excluded_count", 0)) for r in singles)
    runnable = len(singles) - excluded
    groups: dict[tuple[str, int, str], list[Mapping[str, Any]]] = defaultdict(list)
    for r in singles:
        key = (str(r["profile"]), int(r["bars"]), str(r["worker_mode"]))
        groups[key].append(r)
    grouped = []
    for (profile, bars, mode), members in sorted(groups.items()):
        runn = [r for r in members if r["outcome"] != "excluded"]
        ok = [r for r in members if r["outcome"] == "success"]
        grouped.append({
            "profile": profile, "bars": bars, "worker_mode": mode,
            "attempted": len(members), "excluded": len(members) - len(runn),
            "outcomes": dict(Counter(str(r["outcome"]) for r in members)),
            "solver_statuses": dict(Counter(str(r.get("solver_status")) for r in members)),
            "attempt_seconds": stats(
                [
                    float(r["attempt_elapsed_seconds"])
                    for r in runn
                    if "attempt_elapsed_seconds" in r
                ]
            ),
            "successful_generation_seconds": stats(
                [float(r["generation_total_seconds"]) for r in ok]
            ),
            "peak_rss_bytes": stats(
                [float(r["peak_rss_bytes"]) for r in runn if "peak_rss_bytes" in r]
            ),
            "certification_seconds": stats(
                [float(r["certification_total_seconds"]) for r in ok]
            ),
            "stage_seconds": {
                name: stats([float(r[name]) for r in ok])
                for name in (
                    "compile_seconds",
                    "solve_seconds",
                    "semantic_verification_seconds",
                    "artifact_parse_seconds",
                    "strict_semantic_recheck_seconds",
                    "integrity_request_binding_exclusive_seconds",
                    "export_seconds",
                    "parseback_and_delivery_seconds",
                )
            },
            "verification_overhead_ratio": stats(
                [
                    float(r["verification_overhead_ratio"])
                    for r in ok
                    if r.get("verification_overhead_ratio") is not None
                ]
            ),
        })
    generated = sum(int(r.get("generated_count", 0)) for r in singles)
    accepted = sum(int(r.get("accepted_count", 0)) for r in singles)
    released = sum(int(r.get("released_count", 0)) for r in singles)
    multis = [r for r in rows if r["workload"] == "multi_output"]
    return {"benchmark_version": VERSION, "single_output": {
        "attempted": len(singles), "excluded": excluded, "runnable": runnable,
        "generated": generated, "accepted": accepted, "released": released,
        "generation_yield": generated / runnable if runnable else None,
        "acceptance_yield": accepted / runnable if runnable else None,
        "release_yield": released / runnable if runnable else None,
        "outcomes": dict(Counter(str(r["outcome"]) for r in singles)),
        "solver_statuses": dict(Counter(str(r.get("solver_status")) for r in singles)),
        "groups": grouped},
        "multi_output": {"attempted_cases": len(multis),
                         "requested_solutions": sum(
                             int(r["multi_output_count"]) for r in multis
                         ),
                         "generated_solutions": sum(
                             int(r.get("generated_count", 0)) for r in multis
                         ),
                         "rows": multis}}


def environment(c: Mapping[str, Any]) -> dict[str, Any]:
    packages = {}
    for name in ("constraint-music", "ortools", "mido", "PyYAML"):
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = None
    cpu = None
    if Path("/proc/cpuinfo").exists():
        m = re.search(
            r"^model name\s*:\s*(.+)$",
            Path("/proc/cpuinfo").read_text(),
            re.MULTILINE,
        )
        cpu = m.group(1) if m else None
    mem = None
    if Path("/proc/meminfo").exists():
        m = re.search(
            r"^MemTotal:\s+(\d+)\s+kB$",
            Path("/proc/meminfo").read_text(),
            re.MULTILINE,
        )
        mem = int(m.group(1)) if m else None
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip())
    except (OSError, subprocess.CalledProcessError):
        commit, dirty = os.environ.get("GITHUB_SHA"), None
    return {"benchmark_version": VERSION, "captured_at_utc": datetime.now(UTC).isoformat(),
            "git_commit": commit, "git_dirty": dirty, "python": sys.version,
            "platform": platform.platform(), "machine": platform.machine(), "cpu_model": cpu,
            "logical_cpu_count": os.cpu_count(), "memory_total_kib": mem, "packages": packages,
            "github_actions": {k: os.environ.get(k) for k in
                               ("GITHUB_ACTIONS", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT",
                                "RUNNER_OS", "RUNNER_ARCH", "RUNNER_NAME")},
            "matrix": c,
            "notes": ["Fresh subprocess per case for case-local peak RSS.",
                      "UNKNOWN is never relabelled INFEASIBLE.",
                      "Upper quantiles require at least five observations."]}


def dump(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write(
    output: Path,
    rows: Sequence[Mapping[str, Any]],
    summary: Mapping[str, Any],
    env: Mapping[str, Any],
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / RAW).write_text(
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows),
        encoding="utf-8",
    )
    dump(output / SUMMARY, summary)
    dump(output / ENV, env)


def report(path: Path, summary: Mapping[str, Any], env: Mapping[str, Any]) -> None:
    s = summary["single_output"]
    def ratio(value: Any) -> str:
        return "n/a" if value is None else f"{100 * float(value):.1f}%"
    lines = ["# EH-11 Performance Evaluation", "", f"Commit: `{env['git_commit']}`  ",
             f"Captured: `{env['captured_at_utc']}`", "", "## Environment", "",
             f"- CPU: `{env['cpu_model']}`", f"- Logical CPUs: `{env['logical_cpu_count']}`",
             f"- Platform: `{env['platform']}`",
             f"- Python: `{str(env['python']).splitlines()[0]}`",
             f"- OR-Tools: `{env['packages']['ortools']}`", "", "## Yield", "",
             f"- Attempted: **{s['attempted']}**; excluded: **{s['excluded']}**; "
             f"runnable: **{s['runnable']}**",
             f"- Generated: **{s['generated']}** ({ratio(s['generation_yield'])})",
             f"- Strict accepted: **{s['accepted']}** ({ratio(s['acceptance_yield'])})",
             f"- Released: **{s['released']}** ({ratio(s['release_yield'])})",
             f"- Outcomes: `{s['outcomes']}`", f"- Solver statuses: `{s['solver_statuses']}`", "",
             "## Multi-output throughput", "",
             f"- Cases: **{summary['multi_output']['attempted_cases']}**",
             f"- Requested solutions: **{summary['multi_output']['requested_solutions']}**",
             f"- Generated solutions: **{summary['multi_output']['generated_solutions']}**",
             "", "## Scaling and variance", "",
             "| Profile | Bars | Mode | n run | n success | Attempt median s | "
             "Attempt p90 s | Attempt CV | Success median s | RSS median MiB | "
             "Cert median s | Cert/gen |",
             "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | "
             "---: | ---: |"]
    for g in s["groups"]:
        a, gen, mem, cert, ov = (g["attempt_seconds"], g["successful_generation_seconds"],
                                  g["peak_rss_bytes"], g["certification_seconds"],
                                  g["verification_overhead_ratio"])
        def fmt(value: Any, digits: int = 4) -> str:
            return "n/a" if value is None else f"{float(value):.{digits}f}"
        memory_mib = None if mem["median"] is None else mem["median"] / 1048576
        lines.append(
            f"| {g['profile']} | {g['bars']} | {g['worker_mode']} | {a['n']} | "
            f"{gen['n']} | {fmt(a['median'])} | {fmt(a['p90'])} | {fmt(a['cv'], 3)} | "
            f"{fmt(gen['median'])} | {fmt(memory_mib, 1)} | {fmt(cert['median'])} | "
            f"{fmt(ov['median'], 3)} |"
        )
    lines += ["", "Raw rows preserve exclusions, UNKNOWN/no-solution outcomes, and crashes. ",
              "These measurements apply only to the recorded commit/runner; "
              "optimization is outside EH-11.", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def validate(output: Path) -> None:
    rows = [json.loads(x) for x in (output / RAW).read_text().splitlines() if x]
    if not rows:
        raise ValueError("empty EH-11 raw results")
    saved = json.loads((output / SUMMARY).read_text())
    if saved != summarize(rows):
        raise ValueError("summary does not reproduce from raw rows")
    env = json.loads((output / ENV).read_text())
    if env.get("benchmark_version") != VERSION:
        raise ValueError("environment version mismatch")


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--config",
        type=Path,
        default=Path("research/configs/eh11_performance_matrix.json"),
    )
    p.add_argument("--output-dir", type=Path, default=Path("research/results"))
    p.add_argument("--report", type=Path, default=Path("docs/EH11_PERFORMANCE_RESULTS.md"))
    p.add_argument("--worker-json")
    p.add_argument("--validate-results", action="store_true")
    a = p.parse_args(argv)
    if a.worker_json:
        print(json.dumps(execute(Case(**json.loads(a.worker_json))), sort_keys=True))
        return 0
    if a.validate_results:
        validate(a.output_dir)
        return 0
    c = load_config(a.config)
    rows = run(c)
    summary = summarize(rows)
    env = environment(c)
    write(a.output_dir, rows, summary, env)
    report(a.report, summary, env)
    validate(a.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
