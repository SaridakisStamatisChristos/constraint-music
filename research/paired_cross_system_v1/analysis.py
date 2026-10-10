"""Deterministic stage, paired-request, cost and fault analysis "
"from verified rows."""

from __future__ import annotations

import argparse
import itertools
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

from .adapter import save
from .contract import SYSTEMS
from .runner import ROOT, check_faults, check_freeze, check_phase, digest


def passed(row: dict[str, Any]) -> bool:
    return row.get("inspection", {}).get("evaluation", {}).get("status") == "PASS"


def distribution(values: list[float]) -> dict[str, Any]:
    return {
        "n": len(values),
        "min": min(values) if values else None,
        "median": statistics.median(values) if values else None,
        "max": max(values) if values else None,
    }


def derive(root: Path = ROOT) -> dict[str, Any]:
    frozen = check_freeze(root)
    development = check_phase(root, "development")
    attempts = check_phase(root, "heldout")
    faults = check_faults(root, attempts)
    manifest = json.loads((root / "manifest.json").read_text())
    hand = json.loads((root / "heldout/hand_controls.json").read_text())
    primary = [r for r in attempts if r["primary"]]
    result: dict[str, Any] = {
        "schema_version": 1,
        "study_id": manifest["study_id"],
        "freeze_source_commit": frozen["source_commit"],
        "freeze_sha256": digest((root / "freeze.json").read_bytes()),
        "evidence_sha256": {
            str(p.relative_to(root)): digest(p.read_bytes())
            for p in (
                root / "development/index.json",
                root / "heldout/index.json",
                root / "heldout/fault_index.json",
            )
        },
        "planned": manifest["sample"],
        "observed": {
            "development_attempts": len(development),
            "heldout_attempts": len(attempts),
            "heldout_primary_attempts": len(primary),
            "primary_request_clusters": len({r["request_id"] for r in primary}),
            "heldout_families": len({r["family"] for r in primary}),
            "fault_slots": sum(r["fault"] != "ppqn_control" for r in faults),
            "ppqn_control_slots": sum(r["fault"] == "ppqn_control" for r in faults),
        },
        "systems": {},
        "paired": [],
        "counterexamples": [],
    }
    for system in SYSTEMS:
        rows = [r for r in primary if r["system"] == system]
        output = [r for r in rows if r["generation_status"] == "OUTPUT"]
        request_ok = [r for r in output if r["inspection"]["request_pass"]]
        artifact_ok = [r for r in request_ok if r["inspection"]["semantic_pass"]]
        delivered = [r for r in output if r["inspection"]["delivered"]["status"] == "PASS"]
        full = [r for r in rows if passed(r)]
        native_full = [
            r for r in artifact_ok if r["inspection"]["native_delivery"]["status"] == "PASS"
        ]
        injected = [
            f
            for f in faults
            if f["fault"] != "ppqn_control" and f["attempt_id"].endswith("." + system)
        ]
        ppqn = [
            f
            for f in faults
            if f["fault"] == "ppqn_control" and f["attempt_id"].endswith("." + system)
        ]
        result["systems"][system] = {
            "primary_attempts": len(rows),
            "generation": dict(sorted(Counter(r["generation_status"] for r in rows).items())),
            "unsupported_attempts": sum(
                r["system"] == system and r["generation_status"] == "UNSUPPORTED" for r in attempts
            ),
            "funnel": {
                "planned": len(rows),
                "returned_output": len(output),
                "request_bound": len(request_ok),
                "semantic_artifact": len(artifact_ok),
                "delivered_full": len(full),
            },
            "independent_stages": {
                "source_relation": sum(r["inspection"]["source_relation_pass"] for r in output),
                "semantic": sum(r["inspection"]["semantic_pass"] for r in output),
                "delivery": len(delivered),
                "native_end_to_end": len(native_full),
            },
            "native_delivery_statuses": dict(
                sorted(
                    Counter(r["inspection"]["native_delivery"]["status"] for r in output).items()
                )
            ),
            "end_to_end_statuses": dict(
                sorted(
                    Counter(
                        r.get("inspection", {})
                        .get("evaluation", {})
                        .get("status", r["generation_status"])
                        for r in rows
                    ).items()
                )
            ),
            "oracle_agreements": sum(r["inspection"]["reference_agreement"] for r in output),
            "wall_seconds_all_primary": distribution([r["wall_seconds"] for r in rows]),
            "max_process_rss_kib_outputs": distribution(
                [r["metrics"]["max_process_rss_kib"] for r in output if "metrics" in r]
            ),
            "faults": {
                "planned": len(injected),
                "applicable": sum(f["eligible"] for f in injected),
                "statuses": dict(sorted(Counter(f["status"] for f in injected).items())),
                "by_type": {
                    name: dict(
                        sorted(Counter(f["status"] for f in injected if f["fault"] == name).items())
                    )
                    for name in manifest["faults"]
                },
                "first_boundary": dict(
                    sorted(
                        Counter(f["verdict"]["boundary"] for f in injected if f["eligible"]).items()
                    )
                ),
            },
            "ppqn_controls": dict(sorted(Counter(f["status"] for f in ppqn).items())),
        }
        for r in rows:
            if not passed(r):
                result["counterexamples"].append(
                    {
                        "id": r["id"],
                        "generation": r["generation_status"],
                        "evaluation": r.get("inspection", {}).get("evaluation"),
                        "evidence_members": sorted(r["files"]),
                    }
                )
    paired = {s: {r["request_id"]: r for r in primary if r["system"] == s} for s in SYSTEMS}
    for left, right in itertools.combinations(SYSTEMS, 2):
        ids = sorted(paired[left])
        differences = [int(passed(paired[left][i])) - int(passed(paired[right][i])) for i in ids]
        families = sorted({paired[left][i]["family"] for i in ids})
        family_means = [
            statistics.mean(
                d
                for i, d in zip(ids, differences, strict=True)
                if paired[left][i]["family"] == family
            )
            for family in families
        ]
        resamples = [statistics.mean(draw) for draw in itertools.product(family_means, repeat=2)]
        result["paired"].append(
            {
                "left": left,
                "right": right,
                "request_pairs": len(ids),
                "both_pass": sum(passed(paired[left][i]) and passed(paired[right][i]) for i in ids),
                "left_only": differences.count(1),
                "right_only": differences.count(-1),
                "neither": sum(
                    not passed(paired[left][i]) and not passed(paired[right][i]) for i in ids
                ),
                "mean_difference": statistics.mean(differences),
                "family_mean_differences": dict(zip(families, family_means, strict=True)),
                "illustrative_family_bootstrap_means": resamples,
                "illustrative_range": [min(resamples), max(resamples)],
                "interpretation": (
                    "Two purposively selected families; four ordered cluster resamples. "
                    "Not a population confidence interval."
                ),
            }
        )
    injected = [r for r in faults if r["fault"] != "ppqn_control"]
    positives = [r for r in faults if r["fault"] == "ppqn_control" and r["eligible"]]
    result["controls"] = {
        "hand_planned": len(hand),
        "hand_pass": sum(r["verdict"]["status"] == "PASS" and r["reference_pass"] for r in hand),
        "ppqn_applicable": len(positives),
        "ppqn_pass": sum(r["status"] == "PASS" for r in positives),
        "known_valid_false_rejections": sum(r["verdict"]["status"] != "PASS" for r in hand)
        + sum(r["status"] != "PASS" for r in positives),
    }
    result["faults"] = {
        "planned": len(injected),
        "applicable": sum(r["eligible"] for r in injected),
        "statuses": dict(sorted(Counter(r["status"] for r in injected).items())),
        "false_accepts": sum(r["status"] == "PASS" for r in injected),
    }
    agreement = all(
        s["oracle_agreements"] == s["funnel"]["returned_output"] for s in result["systems"].values()
    )
    result["gates"] = {
        "complete_paired_collection": True,
        "semantic_reference_agreement": agreement,
        "positive_controls_pass": result["controls"]["known_valid_false_rejections"] == 0,
        "no_injected_false_accepts": result["faults"]["false_accepts"] == 0,
        "outside_independent_replication_completed": False,
        "public_research_run_permission_granted": False,
    }
    return result


def report(summary: dict[str, Any]) -> str:
    lines = [
        "# Paired cross-system conformance v1: derived report",
        "",
        (
            "This report is derived from independently replayed archived bytes. "
            "It measures the declared major-triad request subset; it does "
            "not rank musical quality, optimization, or general generator "
            "reliability."
        ),
        "",
        "## Planned and observed units",
        "",
        (
            f"Development: {summary['observed']['development_attempts']} attempts. "
            f"Held out: {summary['observed']['heldout_attempts']} attempts, including "
            f"{summary['observed']['heldout_primary_attempts']} primary attempts on "
            f"{summary['observed']['primary_request_clusters']} paired requests in two new "
            "harmonic families, and 12 explicitly unsupported attempts."
        ),
        "",
        "## Boundary transitions",
        "",
        (
            "Every row starts from 12 primary requests. Later funnel stages "
            "require all preceding stages. Independent delivery counts below "
            "test byte fidelity even when harmony fails."
        ),
        "",
        (
            "| System | Planned | Output | Request bound | Semantic artifact "
            "| Full delivered | Native full |"
        ),
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for system, data in summary["systems"].items():
        f = data["funnel"]
        lines.append(
            f"| {system} | {f['planned']} | {f['returned_output']} | {f['request_bound']} | "
            f"{f['semantic_artifact']} | {f['delivered_full']} | "
            f"{data['independent_stages']['native_end_to_end']} |"
        )
    lines += [
        "",
        (
            "Diatony's full delivered endpoint uses its separately declared "
            "renderer; its untouched native bytes remain archived and evaluated "
            "separately. Quarter-note rearticulations from Constraint Music "
            "are retained; whole notes from the other systems are retained. "
            "No attack coalescing is permitted."
        ),
        "",
        "## Natural outcomes and costs",
        "",
        (
            "| System | Generation | End-to-end | Independent delivery pass "
            "| Native delivery | Wall min/median/max (s) | Output max-process "
            "RSS min/median/max (KiB) |"
        ),
        "| --- | --- | --- | ---: | --- | --- | --- |",
    ]
    for system, data in summary["systems"].items():
        wall, rss = data["wall_seconds_all_primary"], data["max_process_rss_kib_outputs"]
        lines.append(
            f"| {system} | {data['generation']} | {data['end_to_end_statuses']} | "
            f"{data['independent_stages']['delivery']} | {data['native_delivery_statuses']} | "
            f"{wall['min']}/{wall['median']}/{wall['max']} (n={wall['n']}) | "
            f"{rss['min']}/{rss['median']}/{rss['max']} (n={rss['n']}) |"
        )
    lines += [
        "",
        (
            "Costs include cold-process import and generation/export work "
            "under a common 30-second outer cap. Constraint Music/Gecode also "
            "have 20-second native clocks; music21 has no comparable native "
            "clock. RSS is the largest individual worker/child process observation, "
            "not summed concurrent pipeline memory. Internal rules, registers, "
            "rhythms, solver strategies and instrumentation differ; costs "
            "are descriptive, not a speed ranking."
        ),
        "",
        "## Paired end-to-end outcomes",
        "",
        (
            "| Left minus right | Pairs | Both pass | Left only | Right only "
            "| Neither | Difference | Two-family resample range |"
        ),
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in summary["paired"]:
        lines.append(
            f"| {row['left']} minus {row['right']} | {row['request_pairs']} | {row['both_pass']} | "
            f"{row['left_only']} | {row['right_only']} | {row['neither']} | "
            f"{row['mean_difference']} | {row['illustrative_range']} |"
        )
    lines += [
        "",
        (
            "The four ordered family-cluster resamples are fully enumerated "
            "in summary.json. With only two purposively chosen families their "
            "ranges are illustrative, not inferential confidence intervals. "
            "Mutations share baselines and do not supply independent statistical "
            "samples."
        ),
        "",
        "## Injected faults",
        "",
        ("| System | Planned | Applicable | Statuses | First failing boundaries | PPQN controls |"),
        "| --- | ---: | ---: | --- | --- | --- |",
    ]
    for system, data in summary["systems"].items():
        f = data["faults"]
        lines.append(
            f"| {system} | {f['planned']} | {f['applicable']} | {f['statuses']} | "
            f"{f['first_boundary']} | {data['ppqn_controls']} |"
        )
    lines += ["", "| Fault | Constraint Music | music21 | Diatony |", "| --- | --- | --- | --- |"]
    for name in next(iter(summary["systems"].values()))["faults"]["by_type"]:
        counts = [str(summary["systems"][s]["faults"]["by_type"][name]) for s in SYSTEMS]
        lines.append("| " + " | ".join([name, *counts]) + " |")
    lines += [
        "",
        (
            f"Total fault accounting: {summary['faults']}. "
            "Inapplicable slots retain their baseline IDs and reasons; malformed MIDI "
            "is blocked and is not relabeled as semantic rejection."
        ),
        "",
        (
            f"Known-valid controls: {summary['controls']}. "
            "These are false-rejection observations on the declared controls, "
            "not an estimate for arbitrary valid music."
        ),
        "",
        "## Traceable natural discrepancies",
        "",
    ]
    if not summary["counterexamples"]:
        lines.append(
            "No primary delivered endpoint failed in this bounded sample. "
            "Native unobservability and unsupported requests still constrain "
            "the claim."
        )
    for row in summary["counterexamples"]:
        lines.append(
            f"- `{row['id']}`: generation={row['generation']}; "
            f"evaluation={row['evaluation']}. Native and normalized bytes/logs: "
            f"`heldout/evidence.zip`, members under `attempts/{row['id']}/`."
        )
    lines += [
        "",
        "## Gates and limits",
        "",
        f"Machine-derived gates: `{summary['gates']}`.",
        "",
        (
            "The protocol/source/corpus/budgets/faults were committed before "
            "held-out collection, with original Git history retained. This "
            "is a local prospective freeze, not externally timestamped preregistration. "
            "Six held-out keys and 4/6-chord requests broaden the earlier "
            "C/G pilot; minor, rest, tie and given-voice requests are explicitly "
            "unsupported. Shared obligations are a narrow intersection and "
            "native systems retain extra restrictions. Both semantic implementations "
            "may share conceptual mistakes; two MIDI parsers can share format "
            "assumptions. No human aesthetic evaluation, global novelty proof, "
            "outside replication or population reliability guarantee is claimed."
        ),
        "",
        (
            "The proprietary license is unchanged. Outside research execution "
            "requires case-by-case written permission; the replay procedure "
            "and permission template make that route reviewable without granting "
            "rights automatically."
        ),
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    summary = derive()
    text = report(summary)
    if args.check:
        if (
            json.loads((ROOT / "summary.json").read_text()) != summary
            or (ROOT / "REPORT.md").read_text() != text
        ):
            raise ValueError("derived summary/report differs from evidence")
    else:
        save(ROOT / "summary.json", summary)
        (ROOT / "REPORT.md").write_text(text)
    print(
        json.dumps(
            {
                "observed": summary["observed"],
                "faults": summary["faults"],
                "gates": summary["gates"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
