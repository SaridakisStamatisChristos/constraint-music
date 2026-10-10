"""Native request-bound CM; frozen legacy/m21/Diatony configurations as controls."""

from __future__ import annotations

import argparse
import json
import resource
import time
from pathlib import Path

from constraint_music.harmonization import ChordRequest, HarmonizationRequest
from research.paired_cross_system_v1.adapter import save
from research.paired_cross_system_v1.render import render
from research.paired_cross_system_v2.adapter import cm as legacy_cm
from research.paired_cross_system_v2.adapter import diatony
from research.paired_cross_system_v2.contract import VOICES, admission
from research.paired_cross_system_v2.music21_adapter import generate as music21


def bound_request(request: dict) -> HarmonizationRequest:
    if admission(request) != "SUPPORTED":
        raise ValueError("unsupported request")
    return HarmonizationRequest(
        key=request["key"],
        chords=tuple(
            ChordRequest(d, i, s)
            for d, i, s in zip(
                request["degrees"],
                request["inversions"],
                request["sevenths"],
                strict=True,
            )
        ),
        given_voices=tuple(
            (s, None, None, b)
            for s, b in zip(
                request["given_soprano"],
                request["bass"],
                strict=True,
            )
        ),
        tempo_bpm=request["tempo_bpm"],
    )


def cm(request: dict, directory: Path, seed: int) -> list:
    from constraint_music.harmonization.midi import write_midi
    from constraint_music.harmonization.solver import harmonize

    obligations = bound_request(request)
    save(
        directory / "native_input.json",
        {
            "request": request,
            "harmonization_request": obligations.to_dict(),
            "profile": "request-bound-satb-v1",
            "seed": seed,
            "workers": 1,
            "max_time_seconds": 20,
        },
    )
    result = harmonize(obligations, seed=seed, max_time_seconds=20)
    save(directory / "native_score.json", result.to_dict())
    write_midi(result, directory / "native.mid")
    return sorted(
        [v, p, str(i), "1"]
        for i, row in enumerate(result.rows)
        for v, p in zip(VOICES, row, strict=True)
    )


def generate(system: str, request: dict, directory: Path, binary: Path, seed: int) -> None:
    if admission(request) != "SUPPORTED":
        raise ValueError("unsupported request")
    start = time.perf_counter()
    if system == "constraint-music":
        events = cm(request, directory, seed)
    elif system == "legacy-constraint-music":
        events = legacy_cm(request, directory, seed)
    elif system == "diatony":
        events = diatony(request, directory, binary, seed)
    elif system == "music21":
        events = music21(request, directory)
    else:
        raise ValueError("unknown system")
    save(directory / "events.json", events)
    (directory / "adapted.mid").write_bytes(render(request, events))
    save(
        directory / "metrics.json",
        {
            "elapsed_seconds": round(time.perf_counter() - start, 6),
            "max_process_rss_kib": max(
                resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
            ),
        },
    )


if __name__ == "__main__":
    from constraint_music.errors import NoSolutionError

    parser = argparse.ArgumentParser()
    parser.add_argument("system")
    parser.add_argument("request", type=Path)
    parser.add_argument("directory", type=Path)
    parser.add_argument("binary", type=Path)
    parser.add_argument("seed", type=int)
    args = parser.parse_args()
    try:
        generate(
            args.system,
            json.loads(args.request.read_text()),
            args.directory,
            args.binary,
            args.seed,
        )
    except NoSolutionError as exc:
        save(args.directory / "native_failure.json", {"exception": str(exc)})
        raise SystemExit(4 if "(UNKNOWN)" in str(exc) else 3) from exc
    except ValueError as exc:
        if str(exc) == "NO_SOLUTION":
            raise SystemExit(3) from exc
        if str(exc) == "TIMEOUT":
            raise SystemExit(4) from exc
        raise
