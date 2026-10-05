"""Regenerate the checked-in EH-09 corruption benchmark evidence."""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile

from constraint_music.midi import write_midi
from constraint_music.models import GenerationSpec
from constraint_music.provenance import artifact_payload
from constraint_music.solver import ConstraintMusicSolver

from .mutations import mutation_manifest
from .run_corruption_benchmark import run, summarize


def benchmark_spec() -> GenerationSpec:
    return GenerationSpec(
        bars=2,
        beats_per_bar=4,
        subdivisions_per_beat=1,
        max_time_seconds=10,
        workers=1,
        seed=123,
        tension_curve=(0.05, 0.75, 0.02),
    )


def generate() -> tuple[dict[str, object], list[dict[str, object]], dict[str, object]]:
    spec = benchmark_spec()
    result = ConstraintMusicSolver().generate(spec)
    payload = artifact_payload(result)
    with NamedTemporaryFile(suffix=".mid") as handle:
        write_midi(result, handle.name)
        midi_bytes = Path(handle.name).read_bytes()
    rows = run(payload, spec, delivery_bytes=midi_bytes)
    fixture = {
        "bars": spec.bars,
        "beats_per_bar": spec.beats_per_bar,
        "seed": spec.seed,
        "workers": spec.workers,
        "composition_sha256": payload["provenance"]["composition_sha256"],
        "midi_sha256": sha256(midi_bytes).hexdigest(),
    }
    return mutation_manifest(), rows, summarize(rows, fixture=fixture)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--directory",
        type=Path,
        default=Path(__file__).parent / "results",
    )
    args = parser.parse_args()
    manifest, rows, summary = generate()
    args.directory.mkdir(parents=True, exist_ok=True)
    (args.directory / "corruption_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.directory / "corruption_benchmark.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    (args.directory / "corruption_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
