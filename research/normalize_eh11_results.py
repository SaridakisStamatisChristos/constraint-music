"""Normalize EH-11 scope exclusions without hiding the original observed outcome."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from research import benchmark_performance as perf

_COMBINED_ONE_BAR_ERROR = (
    "minimum_borrowed_chords exceeds beats available outside the "
    "preserved cadential/context boundary"
)


def normalize_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Reclassify only the known contract-invalid 1-bar combined profile as excluded.

    The original result is retained in explicit audit fields. Any different failure remains
    untouched so genuine generator/verifier errors cannot be laundered into exclusions.
    """

    normalized: list[dict[str, Any]] = []
    for source in rows:
        row = dict(source)
        if (
            row.get("workload") == "single"
            and row.get("profile") == "combined_borrowed_modulation"
            and row.get("bars") == 1
            and row.get("outcome") == "internal_error"
            and row.get("error_type") == "ValueError"
            and row.get("error") == _COMBINED_ONE_BAR_ERROR
        ):
            row["original_outcome"] = row["outcome"]
            row["original_solver_status"] = row.get("solver_status")
            row["normalization"] = "scope_exclusion"
            row["normalization_reason"] = _COMBINED_ONE_BAR_ERROR
            row["outcome"] = "excluded"
            row["excluded_count"] = 1
            row["solver_status"] = "NOT_RUN"
            row["exclusion_reason"] = _COMBINED_ONE_BAR_ERROR
        normalized.append(row)
    return normalized


def normalize_evidence(output: Path, report_path: Path) -> None:
    raw_path = output / perf.RAW
    rows = [json.loads(line) for line in raw_path.read_text(encoding="utf-8").splitlines() if line]
    normalized = normalize_rows(rows)
    env = json.loads((output / perf.ENV).read_text(encoding="utf-8"))
    summary = perf.summarize(normalized)
    perf.write(output, normalized, summary, env)
    perf.report(report_path, summary, env)
    perf.validate(output)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("research/results"))
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("docs/EH11_PERFORMANCE_RESULTS.md"),
    )
    args = parser.parse_args(argv)
    normalize_evidence(args.output_dir, args.report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
