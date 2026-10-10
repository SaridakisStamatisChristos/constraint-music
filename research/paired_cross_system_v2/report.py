"""Report derived directly from verified request-level paired outcomes."""

from __future__ import annotations

import json
from collections import Counter
from statistics import median

from .contract import SYSTEMS
from .runner import ROOT, analyze, check_phase


def report(summary: dict) -> str:
    rows = check_phase("heldout")
    lines = [
        "# Fair paired cross-system study v2",
        "",
        "The primary outcome is a fully conforming common-adapted MIDI in both scheduled runs.",
        "The denominator is 128 feasible requests, not 256 run rows. Four unsupported requests",
        "are retained separately. All raw outputs and nonoutputs are replayable.",
        "",
        "| Engine | Adapted pass in both runs | Native observed pass in both runs |",
        "|---|---:|---:|",
    ]
    for system in SYSTEMS:
        native = str(summary["native_reproducible_pass"][system]) + "/128"
        if system == "diatony":
            native = "Full native conformance unobservable"
        lines.append(
            f"| {system} | {summary['adapted_reproducible_pass'][system]}/128 | {native} |"
        )
    lines += [
        "",
        "Native and adapted delivery are separate profiles. Diatony's native anonymous",
        "four-quarter writer cannot establish the requested voiced quarter-grid/context contract.",
        "Its adapted output uses the same renderer as both competitors, with an explicit",
        "native chord-index to quarter mapping and unchanged pitches/voices.",
        "",
        "| CM versus | Both pass | CM only | Other only | Neither | Difference | "
        "Conservative simultaneous CI | Exact p | Bonferroni p |",
        "|---|---:|---:|---:|---:|---:|---|---:|---:|",
    ]
    for system, comparison in summary["paired_comparisons"].items():
        low, high = comparison["conservative_paired_ci"]
        lines.append(
            f"| {system} | {comparison['both_pass']} | {comparison['left_only']} | "
            f"{comparison['right_only']} | {comparison['neither_pass']} | "
            f"{comparison['difference']:+.2%} | [{low:+.2%}, {high:+.2%}] | "
            f"{comparison['exact_mcnemar_two_sided_p']:.6g} | {comparison['bonferroni_p']:.6g} |"
        )
    conclusion = (
        "ESTABLISHED on the declared outcome and conditional grammar"
        if summary["superiority_established"]
        else "NOT ESTABLISHED"
    )
    lines += [
        "",
        f"**Overall superiority: {conclusion}.** The frozen gate requires both lower",
        "bounds above +10 percentage points and both exact p-values below .025, with no",
        "unresolved harness or inspection errors. Equal rates do not prove equivalence.",
        "",
        "The paired intervals subtract simultaneous Clopper-Pearson bounds for the two",
        "discordant-cell probabilities; each comparison has at least 97.5% coverage, giving",
        "at least 95% simultaneous coverage across the two comparisons. They are conservative.",
        "",
        "| Engine | Output attempts | No result/native limit | Timeout | "
        "Harness error | Blocked | Unsupported slots |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for system in SYSTEMS:
        status = summary["statuses"][system]
        lines.append(
            f"| {system} | "
            + " | ".join(
                str(status.get(x, 0))
                for x in (
                    "OUTPUT",
                    "NO_SOLUTION_OR_NATIVE_LIMIT",
                    "TIMEOUT",
                    "HARNESS_ERROR",
                    "BLOCKED",
                    "UNSUPPORTED",
                )
            )
            + " |"
        )
    lines += [
        "",
        "No-result/native-limit includes native exhaustion or a native limit without an",
        "infeasibility certificate. Every primary input nevertheless has a shared-contract",
        "feasibility witness. Extra native musical rules can restrict the compared configuration.",
        "",
        "| Engine | Worker wall seconds: min / median / max | "
        "Peak process RSS KiB: min / median / max |",
        "|---|---|---|",
    ]
    for system in SYSTEMS:
        selected = [r for r in rows if r["system"] == system and r["status"] != "UNSUPPORTED"]
        wall = [r["process"]["elapsed_seconds"] for r in selected]
        rss = [
            r["inspection"]["metrics"]["max_process_rss_kib"] for r in selected if "inspection" in r
        ]
        lines.append(
            f"| {system} | {min(wall):.4f} / {median(wall):.4f} / {max(wall):.4f} | "
            + (f"{min(rss):g} / {median(rss):g} / {max(rss):g}" if rss else "unavailable")
            + " |"
        )
    corpus = json.loads((ROOT / "heldout/corpus.json").read_text())
    requests = [e["request"] for e in corpus["primary"]]
    lengths = dict(Counter(len(r["degrees"]) for r in requests))
    seventh = sum(any(r["sevenths"]) for r in requests)
    anchors = sum(any(p is not None for p in r["given_soprano"]) for r in requests)
    inverted = sum(any(r["inversions"]) for r in requests)
    keys = dict(Counter(r["key"] for r in requests))
    lines += [
        "",
        f"Sample composition: lengths {lengths}; keys {keys}; {inverted} with inversions;",
        f"{seventh} with dominant sevenths; {anchors} with soprano anchors;",
        f"{corpus['discarded_reference_infeasible']} infeasible candidates rejected "
        "by the reference sampler;",
        f"{summary['exact_duplicate_draws']} exact duplicate IID draws retained.",
        "",
        "Population scope: the declared feasible grammar, conditioned pinned engines, common",
        "renderer and budgets. Templates are shared with development; heldout requests use",
        "an independent seed and were generated only after the committed source/receipt freeze.",
        "The repository freeze is not external preregistration. Repeated workers are not",
        "independent replication. Register bias from lexicographic soprano witness anchors",
        "and different extra native rules limit generalization. Timing is descriptive; RSS",
        "covers successful outputs and is not summed process-tree memory. No aesthetics claim.",
        "",
        "The controlled v1 Eb replay proves an adapter spelling error, not a music21 musical",
        "failure. V1 stays frozen; its 12/12 versus 11/12 is not superiority evidence.",
        "",
        "Every request-level outcome is in `summary.json`; all attempt-level statuses, native",
        "scores, logs and delivered bytes are in `heldout/attempts.json` "
        "and `heldout/evidence.zip`.",
        "",
    ]
    return "\n".join(lines)


def write() -> None:
    summary = analyze()
    (ROOT / "REPORT.md").write_text(report(summary))


if __name__ == "__main__":
    write()
