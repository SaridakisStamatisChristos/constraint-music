from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

from .certification import certify_delivery
from .delivery import RenderProfile
from .errors import InternalVerificationError, NoSolutionError
from .midi import write_certified_midi
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
            "melody,rhythm,bass,harmony,voicing,harmonic_form,tonicization,modal_source"
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
    generate.add_argument(
        "--render-profile",
        choices=(RenderProfile.CERTIFIED_SATB.value, RenderProfile.MELODY_PLUS_SATB.value),
        default=RenderProfile.CERTIFIED_SATB.value,
        help="Certified MIDI projection (default: certified-satb)",
    )

    verify = subparsers.add_parser(
        "verify",
        help=(
            "Inspect embedded-context musical constraints and current artifact integrity "
            "without claiming original-request authentication"
        ),
    )
    verify.add_argument("artifact", type=Path, help="JSON artifact produced by constraint-music")
    verify.add_argument(
        "--allow-legacy",
        action="store_true",
        help="Inspect a supported 2.12 artifact as explicitly non-certifying",
    )

    certify = subparsers.add_parser(
        "certify",
        help="Strictly certify an artifact and delivered MIDI against an independent request",
    )
    certify.add_argument("artifact", type=Path)
    certify.add_argument(
        "--spec", required=True, type=Path, help="Independently fixed YAML request"
    )
    certify.add_argument("--midi", required=True, type=Path, help="Delivered MIDI to parse back")
    certify.add_argument(
        "--render-profile",
        choices=(RenderProfile.CERTIFIED_SATB.value, RenderProfile.MELODY_PLUS_SATB.value),
        default=RenderProfile.CERTIFIED_SATB.value,
    )
    certify.add_argument("--certificate", type=Path, help="Write the structured certificate JSON")

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
                args.render_profile,
            )
        elif args.command == "verify":
            _run_verification(args.artifact, args.allow_legacy)
        elif args.command == "certify":
            _run_certification(
                args.artifact,
                args.spec,
                args.midi,
                args.render_profile,
                args.certificate,
            )
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
                RenderProfile.CERTIFIED_SATB.value,
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
    render_profile: str,
) -> None:
    try:
        from .solver import ConstraintMusicSolver
    except ModuleNotFoundError as exc:
        if exc.name and exc.name.startswith("ortools"):
            raise ValueError(
                "Generation requires: pip install 'constraint-music[generation]'"
            ) from exc
        raise
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
        write_certified_midi(result, midi_path, profile=render_profile)
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
    result, payload = load_result_json(path, require_current=not allow_legacy)
    report = verify_result(result)
    integrity_issues = verify_artifact_integrity(result, payload)

    if report.valid and not integrity_issues:
        print(
            f"PASS (EMBEDDED CONTEXT ONLY) | {len(report.evaluated_rule_ids)} evaluated rules | "
            f"artifact={path}"
        )
        return

    if allow_legacy and payload.get("schema_version") != ARTIFACT_SCHEMA_VERSION:
        print("LEGACY INSPECTION: NON-CERTIFYING", file=sys.stderr)

    if not report.valid:
        print("MUSICAL VERIFICATION: FAIL", file=sys.stderr)
        for issue in report.issues:
            print(f"- {issue}", file=sys.stderr)
    if integrity_issues:
        print("ARTIFACT INTEGRITY: FAIL", file=sys.stderr)
        for issue in integrity_issues:
            print(f"- {issue}", file=sys.stderr)
    raise SystemExit(1)


def _run_certification(
    artifact_path: Path,
    spec_path: Path,
    midi_path: Path,
    render_profile: str,
    certificate_path: Path | None,
) -> None:
    _result, payload = load_result_json(artifact_path, require_current=True)
    expected_spec = GenerationSpec.from_yaml(spec_path)
    report = certify_delivery(
        payload,
        midi_path,
        expected_spec=expected_spec,
        render_profile=render_profile,
    )
    rendered = json.dumps(dict(report.certificate), indent=2) + "\n"
    if certificate_path is not None:
        certificate_path.parent.mkdir(parents=True, exist_ok=True)
        certificate_path.write_text(rendered, encoding="utf-8")
    if report.accepted:
        print("PASS (EXTERNAL REQUEST + DELIVERY) | " + rendered.strip())
        return
    print("CERTIFICATION: FAIL", file=sys.stderr)
    for issue in report.semantic.issues:
        print(f"- {issue}", file=sys.stderr)
    for issue in report.integrity_issues:
        print(f"- {issue}", file=sys.stderr)
    if report.delivery is not None:
        for issue in report.delivery.issues:
            print(f"- {issue}", file=sys.stderr)
    raise SystemExit(1)


def _numbered_path(path: Path, index: int, count: int) -> Path:
    if count == 1:
        return path
    return path.with_name(f"{path.stem}_{index:02d}{path.suffix}")


if __name__ == "__main__":
    main()
