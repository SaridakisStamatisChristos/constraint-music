from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from .midi import write_midi
from .models import GenerationSpec
from .objective import evaluate_objective_vector
from .provenance import (
    ARTIFACT_SCHEMA_VERSION,
    load_result_json,
    verify_artifact_integrity,
    write_result_json,
)
from .render import render_grid
from .search import objective_mapping
from .solver import ConstraintMusicSolver, InternalVerificationError, NoSolutionError
from .verifier import verify_result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="constraint-music",
        description=(
            "Compose and independently verify short tonal pieces under explicit constraints."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate from a YAML specification")
    generate.add_argument("config", type=Path, help="Path to YAML config")
    generate.add_argument("--output", "-o", type=Path, default=Path("composition.mid"))
    generate.add_argument(
        "--json", dest="json_path", type=Path, help="Write a verifiable JSON artifact"
    )
    generate.add_argument("--seed", type=int, help="Override the YAML seed")
    generate.add_argument("--count", type=int, default=1, help="Generate N distinct alternatives")
    generate.add_argument(
        "--distinct-on",
        default="melody",
        help=(
            "Comma-separated no-good dimensions: "
            "melody,rhythm,bass,harmony,voicing,harmonic_form"
        ),
    )
    generate.add_argument(
        "--pareto",
        action="store_true",
        help="Approximate a nondominated front using deterministic weighted scalarizations",
    )
    generate.add_argument(
        "--pareto-candidate-multiplier",
        type=int,
        default=3,
        help="Candidate-pool multiplier for Pareto approximation (1..8)",
    )
    generate.add_argument("--print-grid", action="store_true", help="Print the solved note grid")

    verify = subparsers.add_parser(
        "verify",
        help=(
            "Verify hard musical constraints and current artifact provenance "
            "without rerunning the solver"
        ),
    )
    verify.add_argument("artifact", type=Path, help="JSON artifact produced by constraint-music")
    verify.add_argument(
        "--allow-legacy",
        action="store_true",
        help="Accept missing current provenance while still checking musical constraints",
    )

    demo = subparsers.add_parser("demo", help="Generate a built-in four-bar C-major example")
    demo.add_argument("--output", "-o", type=Path, default=Path("constraint_demo.mid"))
    demo.add_argument(
        "--json", dest="json_path", type=Path, help="Write a verifiable JSON artifact"
    )
    demo.add_argument("--print-grid", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            spec = GenerationSpec.from_yaml(args.config)
            if args.seed is not None:
                spec = replace(spec, seed=args.seed)
            _run_generation(
                spec,
                args.output,
                args.json_path,
                args.count,
                args.print_grid,
                args.distinct_on,
                args.pareto,
                args.pareto_candidate_multiplier,
            )
        elif args.command == "verify":
            _run_verification(args.artifact, args.allow_legacy)
        elif args.command == "demo":
            _run_generation(
                GenerationSpec(),
                args.output,
                args.json_path,
                1,
                args.print_grid,
                "melody",
                False,
                3,
            )
        else:
            parser.error(f"Unknown command {args.command}")
    except (ValueError, NoSolutionError, InternalVerificationError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


def _run_generation(
    spec: GenerationSpec,
    output: Path,
    json_path: Path | None,
    count: int,
    print_grid: bool,
    distinct_on: str,
    pareto: bool,
    pareto_candidate_multiplier: int,
) -> None:
    solver = ConstraintMusicSolver()
    if pareto:
        results = solver.generate_pareto(
            spec,
            count,
            distinct_on,
            pareto_candidate_multiplier,
        )
    else:
        results = solver.generate_many(spec, count, distinct_on)
    for index, result in enumerate(results, start=1):
        midi_path = _numbered_path(output, index, len(results))
        write_midi(result, midi_path)
        if json_path is not None:
            report_path = _numbered_path(json_path, index, len(results))
            write_result_json(result, report_path)
        if print_grid:
            if index > 1:
                print("\n" + "=" * 80 + "\n")
            print(render_grid(result))
        vector = objective_mapping(evaluate_objective_vector(result))
        print(
            f"wrote {midi_path} | {result.solver_status} | "
            f"objective={result.objective_value:.1f} | vector={vector} | verification=PASS"
        )


def _run_verification(path: Path, allow_legacy: bool) -> None:
    result, payload = load_result_json(path)
    report = verify_result(result)
    integrity_issues = verify_artifact_integrity(result, payload)
    if allow_legacy and payload.get("schema_version") != ARTIFACT_SCHEMA_VERSION:
        integrity_issues = ()

    if report.valid and not integrity_issues:
        print(
            f"PASS | {len(report.checked_rules)} hard constraints | "
            f"artifact={path}"
        )
        return

    if not report.valid:
        print("MUSICAL VERIFICATION: FAIL", file=sys.stderr)
        for issue in report.issues:
            print(f"- {issue}", file=sys.stderr)
    if integrity_issues:
        print("ARTIFACT INTEGRITY: FAIL", file=sys.stderr)
        for issue in integrity_issues:
            print(f"- {issue}", file=sys.stderr)
    raise SystemExit(1)


def _numbered_path(path: Path, index: int, count: int) -> Path:
    if count == 1:
        return path
    return path.with_name(f"{path.stem}_{index:02d}{path.suffix}")


if __name__ == "__main__":
    main()
