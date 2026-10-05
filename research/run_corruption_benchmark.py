"""Execute and summarize the frozen semantic-corruption benchmark."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from constraint_music.artifact_validation import ArtifactShapeError
from constraint_music.certification import certify_delivery, verify_artifact
from constraint_music.delivery import RenderProfile
from constraint_music.models import GenerationSpec

from .mutations import MutationCase, generate_mutations, mutation_manifest

_ROOT = Path(__file__).resolve().parents[1]


def _expected_spec(case: MutationCase, expected_spec: GenerationSpec) -> GenerationSpec:
    if case.expected_spec_variant == "identity":
        return expected_spec
    if case.expected_spec_variant == "seed+1":
        return replace(expected_spec, seed=expected_spec.seed + 1)
    raise AssertionError(f"Unknown expected-spec variant {case.expected_spec_variant!r}")


def _evaluate_case(case: MutationCase, expected_spec: GenerationSpec) -> tuple[str, list[str]]:
    try:
        if case.delivery_bytes is None:
            report = verify_artifact(
                case.payload,
                expected_spec=_expected_spec(case, expected_spec),
            )
        else:
            with NamedTemporaryFile(suffix=".mid") as handle:
                handle.write(case.delivery_bytes)
                handle.flush()
                report = certify_delivery(
                    case.payload,
                    handle.name,
                    expected_spec=_expected_spec(case, expected_spec),
                    render_profile=RenderProfile.CERTIFIED_SATB,
                )
    except ArtifactShapeError as exc:
        return "BLOCKED", list(exc.issues)
    except Exception as exc:  # pragma: no cover - raw benchmark must preserve crashes
        return "CRASH", [f"{type(exc).__name__}: {exc}"]
    issues = [*report.semantic.issues, *report.integrity_issues]
    if report.delivery is not None:
        issues.extend(report.delivery.issues)
    return ("ACCEPT" if report.accepted else "REJECT"), issues


def run(
    payload: dict[str, Any],
    expected_spec: GenerationSpec,
    *,
    delivery_bytes: bytes | None = None,
) -> list[dict[str, Any]]:
    """Run every applicable frozen case with complete outcome accounting."""

    results: list[dict[str, Any]] = []
    for case in generate_mutations(payload, delivery_bytes=delivery_bytes):
        outcome, issues = _evaluate_case(case, expected_spec)
        adjudicated = outcome in case.expected_outcomes
        results.append(
            {
                "case_id": case.case_id,
                "split": case.split,
                "tier": case.tier,
                "family": case.family,
                "cluster_id": case.cluster_id,
                "expected_class": case.expected_class,
                "expected_outcomes": list(case.expected_outcomes),
                "outcome": outcome,
                "adjudicated": adjudicated,
                "issues": issues,
            }
        )
    return results


def _wilson(successes: int, total: int) -> list[float] | None:
    if total == 0:
        return None
    z = 1.959963984540054
    observed = successes / total
    denominator = 1 + z * z / total
    center = (observed + z * z / (2 * total)) / denominator
    radius = (
        z * math.sqrt(observed * (1 - observed) / total + z * z / (4 * total * total)) / denominator
    )
    return [round(max(0.0, center - radius), 6), round(min(1.0, center + radius), 6)]


def _metrics(rows: list[dict[str, Any]]) -> dict[str, object]:
    attacks = [row for row in rows if row["expected_class"] != "valid"]
    controls = [row for row in rows if row["expected_class"] == "valid"]
    clusters: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in attacks:
        clusters[str(row["cluster_id"])].append(row)
    successful_clusters = sum(
        all(bool(row["adjudicated"]) for row in cluster) for cluster in clusters.values()
    )
    correct_attacks = sum(bool(row["adjudicated"]) for row in attacks)
    accepted_controls = sum(row["outcome"] == "ACCEPT" for row in controls)
    return {
        "cases": len(rows),
        "attacks": len(attacks),
        "controls": len(controls),
        "correct": sum(bool(row["adjudicated"]) for row in rows),
        "crashes": sum(row["outcome"] == "CRASH" for row in rows),
        "outcomes": dict(sorted(Counter(str(row["outcome"]) for row in rows).items())),
        "attack_detection_rate": (round(correct_attacks / len(attacks), 6) if attacks else None),
        "control_acceptance_rate": (
            round(accepted_controls / len(controls), 6) if controls else None
        ),
        "clusters": len(clusters),
        "successful_clusters": successful_clusters,
        "cluster_detection_rate": (
            round(successful_clusters / len(clusters), 6) if clusters else None
        ),
        "cluster_wilson_95": _wilson(successful_clusters, len(clusters)),
    }


def _group_metrics(
    rows: list[dict[str, Any]], key: str, *, exclude_control: bool = False
) -> dict[str, object]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        value = str(row[key])
        if exclude_control and value == "control":
            continue
        groups[value].append(row)
    return {name: _metrics(group) for name, group in sorted(groups.items())}


def _canonical_hash(value: object) -> str:
    rendered = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return sha256(rendered).hexdigest()


def _source_hash(path: str) -> str:
    return sha256((_ROOT / path).read_bytes()).hexdigest()


def summarize(
    rows: list[dict[str, Any]],
    *,
    fixture: dict[str, object] | None = None,
) -> dict[str, object]:
    """Compute raw, family, tier, split, and cluster-aware benchmark metrics."""

    manifest = mutation_manifest()
    manifest_clusters: dict[str, str] = {}
    manifest_cases = manifest["cases"]
    if not isinstance(manifest_cases, list):  # pragma: no cover - manifest invariant
        raise AssertionError("Manifest cases are not an array")
    for case in manifest_cases:
        if not isinstance(case, dict):  # pragma: no cover - manifest invariant
            raise AssertionError("Manifest case is not an object")
        cluster = str(case["cluster_id"])
        split = str(case["split"])
        previous = manifest_clusters.setdefault(cluster, split)
        if previous != split:
            raise AssertionError(f"Cluster {cluster!r} leaks across benchmark splits")
    return {
        "schema_version": 1,
        "claim_boundary": (
            "Finite deterministic corruptions of one pinned artifact and its certified "
            "MIDI delivery; confidence intervals use attack clusters, not raw cases."
        ),
        "fixture": fixture or {},
        "manifest_sha256": _canonical_hash(manifest),
        "raw_results_sha256": _canonical_hash(rows),
        "overall": _metrics(rows),
        "by_family": _group_metrics(rows, "family", exclude_control=True),
        "by_tier": _group_metrics(rows, "tier"),
        "by_split": _group_metrics(rows, "split"),
        "split_cluster_overlap": [],
        "implementation_hashes": {
            path: _source_hash(path)
            for path in (
                "research/mutations.py",
                "research/run_corruption_benchmark.py",
                "src/constraint_music/artifact_validation.py",
                "src/constraint_music/certification.py",
                "src/constraint_music/delivery.py",
            )
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--midi", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.artifact.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("artifact root must be an object")
    spec = GenerationSpec.from_yaml(args.spec)
    midi_bytes = args.midi.read_bytes()
    results = run(payload, spec, delivery_bytes=midi_bytes)
    fixture = {
        "composition_sha256": payload["provenance"]["composition_sha256"],
        "midi_sha256": sha256(midi_bytes).hexdigest(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in results),
        encoding="utf-8",
    )
    args.summary.write_text(
        json.dumps(summarize(results, fixture=fixture), indent=2) + "\n",
        encoding="utf-8",
    )
    if args.manifest:
        args.manifest.write_text(json.dumps(mutation_manifest(), indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
