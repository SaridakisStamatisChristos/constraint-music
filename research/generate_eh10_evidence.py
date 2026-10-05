"""Regenerate checked-in EH-10 ablation and external-comparator evidence."""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile

from constraint_music.midi import write_midi
from constraint_music.provenance import artifact_payload
from constraint_music.solver import ConstraintMusicSolver

from .assurance_ablations import run_ablations, summarize_ablations
from .external_comparators import run_external_comparators
from .generate_corruption_evidence import benchmark_spec

_ROOT = Path(__file__).resolve().parents[1]


def _canonical_hash(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _source_hash(path: str) -> str:
    return sha256((_ROOT / path).read_bytes()).hexdigest()


def generate() -> tuple[list[dict[str, object]], dict[str, object], dict[str, object]]:
    spec = benchmark_spec()
    result = ConstraintMusicSolver().generate(spec)
    payload = artifact_payload(result)
    with NamedTemporaryFile(suffix=".mid") as handle:
        write_midi(result, handle.name)
        midi_bytes = Path(handle.name).read_bytes()
    rows = run_ablations(payload, spec, delivery_bytes=midi_bytes)
    summary = summarize_ablations(rows)
    summary["fixture"] = {
        "composition_sha256": payload["provenance"]["composition_sha256"],
        "midi_sha256": sha256(midi_bytes).hexdigest(),
    }
    summary["raw_results_sha256"] = _canonical_hash(rows)
    summary["implementation_hashes"] = {
        path: _source_hash(path)
        for path in (
            "research/assurance_ablations.py",
            "research/mutations.py",
            "src/constraint_music/artifact_validation.py",
            "src/constraint_music/provenance.py",
            "src/constraint_music/delivery.py",
            "src/constraint_music/verifier.py",
        )
    }
    comparators = run_external_comparators()
    comparators["implementation_hashes"] = {
        path: _source_hash(path)
        for path in (
            "research/external_comparators.py",
            "src/constraint_music/theory.py",
            "src/constraint_music/satb.py",
        )
    }
    return rows, summary, comparators


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, default=Path(__file__).parent / "results")
    args = parser.parse_args()
    rows, summary, comparators = generate()
    args.directory.mkdir(parents=True, exist_ok=True)
    (args.directory / "assurance_ablation_rows.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8"
    )
    (args.directory / "assurance_ablation_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    (args.directory / "external_comparator_summary.json").write_text(
        json.dumps(comparators, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
