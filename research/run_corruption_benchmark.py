"""Execute the deterministic corruption smoke corpus with complete accounting."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from constraint_music.artifact_validation import ArtifactShapeError
from constraint_music.certification import verify_artifact
from constraint_music.models import GenerationSpec

from .mutations import generate_mutations


def run(payload: dict[str, Any], expected_spec: GenerationSpec) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for case in generate_mutations(payload):
        try:
            report = verify_artifact(case.payload, expected_spec=expected_spec)
        except ArtifactShapeError as exc:
            outcome = "BLOCKED"
            issues = list(exc.issues)
        except Exception as exc:  # pragma: no cover - benchmark preserves unexpected crashes
            outcome = "CRASH"
            issues = [f"{type(exc).__name__}: {exc}"]
        else:
            outcome = "ACCEPT" if report.accepted else "REJECT"
            issues = [*report.semantic.issues, *report.integrity_issues]
        results.append({**asdict(case), "payload": None, "outcome": outcome, "issues": issues})
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = json.loads(args.artifact.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("artifact root must be an object")
    results = run(payload, GenerationSpec.from_yaml(args.spec))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in results),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

