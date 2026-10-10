"""Native request conditioning before search, never oracle-guided selection."""

from __future__ import annotations

import argparse
import json
import resource
import subprocess
import time
from dataclasses import asdict
from pathlib import Path

from research.paired_cross_system_v1.adapter import save
from research.paired_cross_system_v1.render import render

from .contract import KEYS, VOICES, admission


def cm(request: dict, directory: Path, seed: int) -> list:
    from constraint_music.midi import write_midi
    from constraint_music.models import GenerationSpec
    from constraint_music.solver import ConstraintMusicSolver

    class ConditionedSolver(ConstraintMusicSolver):
        def _compile(self, spec, weights):
            problem = super()._compile(spec, weights)
            voices = [
                problem.satb.soprano,
                problem.satb.alto,
                problem.satb.tenor,
                problem.bass_note,
            ]
            for beat, degree in enumerate(request["degrees"]):
                problem.model.add(problem.chord[beat] == degree)
                problem.model.add(problem.satb.chord_kind[beat] == int(request["sevenths"][beat]))
                problem.model.add(problem.satb.chord_inversion[beat] == request["inversions"][beat])
                problem.model.add(problem.bass_note[beat] == request["bass"][beat])
                if request["given_soprano"][beat] is not None:
                    problem.model.add(voices[0][beat] == request["given_soprano"][beat])
                if request["degrees"][beat : beat + 2] == [4, 0]:
                    for i, notes in enumerate(voices):
                        pc = problem.model.new_int_var(0, 11, f"v2pc_{beat}_{i}")
                        leading = problem.model.new_bool_var(f"v2lt_{beat}_{i}")
                        problem.model.add_modulo_equality(pc, notes[beat], 12)
                        problem.model.add(
                            pc == (KEYS[request["key"]][0] + 11) % 12
                        ).only_enforce_if(leading)
                        problem.model.add(
                            pc != (KEYS[request["key"]][0] + 11) % 12
                        ).only_enforce_if(leading.Not())
                        problem.model.add(notes[beat + 1] == notes[beat] + 1).only_enforce_if(
                            leading
                        )
            problem.model.clear_objective()
            return problem

    spec = GenerationSpec(
        key=request["key"],
        bars=len(request["degrees"]) // 4,
        beats_per_bar=4,
        subdivisions_per_beat=1,
        tempo_bpm=request["tempo_bpm"],
        workers=1,
        seed=seed,
        max_time_seconds=20,
        max_repeated_notes=8,
        bass_low=48,
        bass_high=59,
        melody_low=60,
        melody_high=84,
        max_bass_leap=12,
        require_authentic_cadence=False,
        resolve_leading_tone=False,
        harmony_vocabulary="triads+sevenths",
        progression_graph=tuple(tuple(range(7)) for _ in range(7)),
    )
    save(directory / "native_input.json", {"request": request, "spec": asdict(spec), "seed": seed})
    result = ConditionedSolver().generate(spec)
    save(directory / "native_score.json", result.to_dict())
    write_midi(result, directory / "native.mid")
    return sorted(
        [v, p, str(i), "1"] for v in VOICES for i, p in enumerate(getattr(result, v.lower()))
    )


def diatony(request: dict, directory: Path, binary: Path, seed: int) -> list:
    save(directory / "native_input.json", {"request": request, "seed": seed, "budget_ms": 20000})

    def csv(name):
        return ",".join(str(int(x)) if x is not None else "-1" for x in request[name])

    command = [
        str(binary),
        str(KEYS[request["key"]][0]),
        "20000",
        csv("degrees"),
        csv("inversions"),
        csv("sevenths"),
        csv("bass"),
        csv("given_soprano"),
        str(directory / "native_score.txt"),
        str(directory / "native"),
    ]
    result = subprocess.run(command, capture_output=True, timeout=25)
    (directory / "native_stdout.txt").write_bytes(result.stdout)
    (directory / "native_stderr.txt").write_bytes(result.stderr)
    if result.returncode:
        raise ValueError("TIMEOUT" if result.returncode == 4 else "NO_SOLUTION")
    lines = (directory / "native_score.txt").read_text().splitlines()
    if lines[0] != "VOICE_ROWS_B_T_A_S" or len(lines) != len(request["degrees"]) + 1:
        raise ValueError("native row count")
    rows = [[int(x) for x in line.split()] for line in lines[1:]]
    if any(len(row) != 4 for row in rows):
        raise ValueError("native row width")
    return sorted(
        [v, row[3 - j], str(i), "1"] for i, row in enumerate(rows) for j, v in enumerate(VOICES)
    )


def generate(system: str, request: dict, directory: Path, binary: Path, seed: int) -> None:
    if admission(request) != "SUPPORTED":
        raise ValueError("unsupported request")
    start = time.perf_counter()
    if system == "constraint-music":
        events = cm(request, directory, seed)
    elif system == "diatony":
        events = diatony(request, directory, binary, seed)
    else:
        from .music21_adapter import generate as music21

        events = music21(request, directory)
    save(directory / "events.json", events)
    # The same declared renderer for all engines; no pitch/voice selection or repair.
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
