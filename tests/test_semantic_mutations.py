from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from research.mutations import mutation_manifest
from research.run_corruption_benchmark import run, summarize

from constraint_music.midi import write_midi
from constraint_music.models import GenerationResult
from constraint_music.provenance import artifact_payload

_RESULTS = Path(__file__).parents[1] / "research/results"


def _benchmark(
    solved_piece: GenerationResult,
    tmp_path: Path,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    midi_path = write_midi(solved_piece, tmp_path / "control.mid")
    midi_bytes = midi_path.read_bytes()
    payload = artifact_payload(solved_piece)
    rows = run(payload, solved_piece.spec, delivery_bytes=midi_bytes)
    fixture = {
        "bars": solved_piece.spec.bars,
        "beats_per_bar": solved_piece.spec.beats_per_bar,
        "seed": solved_piece.spec.seed,
        "workers": solved_piece.spec.workers,
        "composition_sha256": payload["provenance"]["composition_sha256"],
        "midi_sha256": sha256(midi_bytes).hexdigest(),
    }
    return rows, summarize(rows, fixture=fixture)


def test_full_corruption_corpus_has_complete_adjudication_and_no_crashes(
    solved_piece: GenerationResult,
    tmp_path: Path,
) -> None:
    rows, summary = _benchmark(solved_piece, tmp_path)

    assert len(rows) == 32
    assert len({row["case_id"] for row in rows}) == len(rows)
    assert all(row["adjudicated"] is True for row in rows)
    assert summary["overall"] == {
        "cases": 32,
        "attacks": 30,
        "controls": 2,
        "correct": 32,
        "crashes": 0,
        "outcomes": {"ACCEPT": 2, "BLOCKED": 6, "REJECT": 24},
        "attack_detection_rate": 1.0,
        "control_acceptance_rate": 1.0,
        "clusters": 15,
        "successful_clusters": 15,
        "cluster_detection_rate": 1.0,
        "cluster_wilson_95": [0.796117, 1.0],
    }
    assert set(summary["by_family"]) == {
        "delivery",
        "harmonic-claims",
        "integrity-request",
        "realized-music",
        "structure",
    }
    assert set(summary["by_tier"]) == {"T0", "T1", "T2", "T3", "T4"}
    assert set(summary["by_split"]) == {"development", "evaluation"}


def test_manifest_clusters_do_not_leak_across_splits() -> None:
    manifest = mutation_manifest()
    cases = manifest["cases"]
    assert isinstance(cases, list)
    by_cluster: dict[str, set[str]] = {}
    for case in cases:
        assert isinstance(case, dict)
        by_cluster.setdefault(case["cluster_id"], set()).add(case["split"])

    assert all(len(splits) == 1 for splits in by_cluster.values())
    assert len(cases) == 32


def test_checked_in_corruption_evidence_matches_a_fresh_run(
    solved_piece: GenerationResult,
    tmp_path: Path,
) -> None:
    rows, summary = _benchmark(solved_piece, tmp_path)
    persisted_manifest = json.loads(
        (_RESULTS / "corruption_manifest.json").read_text(encoding="utf-8")
    )
    persisted_rows = [
        json.loads(line)
        for line in (_RESULTS / "corruption_benchmark.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    persisted_summary = json.loads(
        (_RESULTS / "corruption_summary.json").read_text(encoding="utf-8")
    )

    assert persisted_manifest == mutation_manifest()
    assert persisted_rows == rows
    assert persisted_summary == summary
