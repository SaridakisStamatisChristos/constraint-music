"""Fresh-process generator adapters; no oracle is called to select or repair outputs."""

from __future__ import annotations

import argparse
import json
import resource
import subprocess
import time
from dataclasses import asdict
from fractions import Fraction
from pathlib import Path
from typing import Any

from .contract import KEYS, VOICES, admission, content_hash


def save(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def conditioned_cm(request: dict[str, Any], directory: Path) -> list[list[Any]]:
    from constraint_music.midi import write_midi
    from constraint_music.models import GenerationSpec
    from constraint_music.solver import ConstraintMusicSolver

    class ConditionedSolver(ConstraintMusicSolver):
        def _compile(self, spec: Any, weights: Any) -> Any:
            problem = super()._compile(spec, weights)
            voices = [
                problem.satb.soprano,
                problem.satb.alto,
                problem.satb.tenor,
                problem.bass_note,
            ]
            for block, degree in enumerate(request["degrees"]):
                for beat in range(block * 4, block * 4 + 4):
                    problem.model.add(problem.chord[beat] == degree)
                    problem.model.add(problem.satb.chord_inversion[beat] == 0)
                    for values in voices:
                        problem.model.add(values[beat] == values[block * 4])
            leading_pc = (KEYS[request["key"]][0] + 11) % 12
            for block in range(len(request["degrees"]) - 1):
                if request["degrees"][block : block + 2] != [4, 0]:
                    continue
                for i, values in enumerate(voices):
                    left, right = values[block * 4], values[(block + 1) * 4]
                    pc = problem.model.new_int_var(0, 11, f"shared_pc_{block}_{i}")
                    leading = problem.model.new_bool_var(f"shared_leading_{block}_{i}")
                    problem.model.add_modulo_equality(pc, left, 12)
                    problem.model.add(pc == leading_pc).only_enforce_if(leading)
                    problem.model.add(pc != leading_pc).only_enforce_if(leading.Not())
                    problem.model.add(right == left + 1).only_enforce_if(leading)
            # Conformance asks for the first feasible result, not weighted optimality.
            problem.model.clear_objective()
            return problem

    spec = GenerationSpec(
        key=request["key"],
        bars=len(request["degrees"]),
        subdivisions_per_beat=1,
        tempo_bpm=request["tempo_bpm"],
        workers=1,
        seed=7,
        max_time_seconds=20,
        max_repeated_notes=8,
        bass_low=36,
        bass_high=59,
        melody_low=60,
        melody_high=84,
        max_bass_leap=12,
        require_authentic_cadence=False,
        resolve_leading_tone=False,
    )
    save(
        directory / "native_input.json",
        {
            "spec": asdict(spec),
            "conditioning_request": request,
            "selection": "first-feasible, objective cleared",
        },
    )
    result = ConditionedSolver().generate(spec)
    save(directory / "native_score.json", result.to_dict())
    write_midi(result, directory / "native.mid")
    return [
        [voice, p, str(beat), "1"]
        for voice in VOICES
        for beat, p in enumerate(getattr(result, voice.lower()))
    ]


def music21(request: dict[str, Any], directory: Path) -> list[list[Any]]:
    from music21 import key, meter, note, tempo
    from music21.figuredBass import realizer
    from music21.figuredBass import segment as fb_segment

    class ConditionedSegment(fb_segment.Segment):
        def consecutivePossibilityRules(self, fbRules=None):
            native_rules = super().consecutivePossibilityRules(fbRules)

            def shared_cadence(left, right):
                return all(
                    a.pitchClass != (tonic + 11) % 12 or b.midi == a.midi + 1
                    for a, b in zip(left, right, strict=True)
                )

            return [*native_rules, (self.shared_cadential, shared_cadence, True)]

    class ConditionedLine(realizer.FiguredBassLine):
        def retrieveSegments(self, fbRules, numParts, maxPitch):
            segments = super().retrieveSegments(fbRules, numParts, maxPitch)
            for index, native in enumerate(segments):
                native.__class__ = ConditionedSegment
                native.shared_cadential = request["degrees"][index : index + 2] == [4, 0]
            return segments

    tonic = KEYS[request["key"]][0]
    scale = (0, 2, 4, 5, 7, 9, 11)
    basses = [48 + (tonic + scale[d]) % 12 for d in request["degrees"]]
    save(
        directory / "native_input.json",
        {
            "key": request["key"],
            "bass": basses,
            "quarter_length": 4,
            "meter": "4/4",
            "tempo": request["tempo_bpm"],
            "chorale": True,
            "conditioning": "all-voice V-I ascending leading tone",
        },
    )
    line = ConditionedLine(key.Key(request["key"]), meter.TimeSignature("4/4"))
    for p in basses:
        line.addElement(note.Note(p, quarterLength=4))
    result = line.realize()
    result.keyboardStyleOutput = False
    # Pinned internal movement DAG: find a first complete path without materializing
    # exponentially many progressions. Nodes/edges were generated by music21.
    segments = result._segmentList
    viable = set(segments[-2].movements)
    viable_sets = [viable]
    for segment in reversed(segments[:-2]):
        viable = {
            a for a, successors in segment.movements.items() if any(b in viable for b in successors)
        }
        viable_sets.append(viable)
    viable_sets.reverse()
    if not viable_sets[0]:
        raise ValueError("NO_SOLUTION")

    def order(possibility):
        return tuple(p.midi for p in possibility)

    current = min(viable_sets[0], key=order)
    progression = [current]
    for index, segment in enumerate(segments[:-1]):
        choices = segment.movements[current]
        if index < len(segments) - 2:
            choices = [c for c in choices if c in viable_sets[index + 1]]
        current = min(choices, key=order)
        progression.append(current)
    score = result.generateRealizationFromPossibilityProgression(progression)
    score.insert(0, tempo.MetronomeMark(number=request["tempo_bpm"]))
    score.write("musicxml", fp=directory / "native_score.musicxml")
    score.write("midi", fp=directory / "native.mid")
    return [
        [VOICES[i], int(n.pitch.midi), str(Fraction(n.offset)), str(Fraction(n.quarterLength))]
        for i, part in enumerate(score.parts)
        for n in part.flatten().notes
    ]


def diatony(request: dict[str, Any], directory: Path, binary: Path) -> list[list[Any]]:
    save(
        directory / "native_input.json",
        {
            "key": request["key"],
            "degrees": request["degrees"],
            "inversions": [0] * len(request["degrees"]),
            "budget_ms": 20000,
            "selection": "first-feasible DFS",
            "conditioning": "complete triads and all-voice V-I ascending leading tone",
        },
    )
    completed = subprocess.run(
        [
            str(binary),
            str(KEYS[request["key"]][0]),
            "20000",
            ",".join(map(str, request["degrees"])),
            str(directory / "native_score.txt"),
            str(directory / "native"),
        ],
        capture_output=True,
        timeout=25,
    )
    (directory / "native_stdout.txt").write_bytes(completed.stdout)
    (directory / "native_stderr.txt").write_bytes(completed.stderr)
    if completed.returncode:
        raise ValueError("TIMEOUT" if completed.returncode == 4 else "NO_SOLUTION")
    lines = (directory / "native_score.txt").read_text().splitlines()
    if lines[0] != "VOICE_ROWS_B_T_A_S" or len(lines) != len(request["degrees"]) + 1:
        raise ValueError("invalid capture")
    rows = [[int(x) for x in line.split()] for line in lines[1:]]
    if any(len(row) != 4 for row in rows):
        raise ValueError("invalid voice row")
    return [
        [voice, row[3 - i], str(block * 4), "4"]
        for block, row in enumerate(rows)
        for i, voice in enumerate(VOICES)
    ]


def generate(system: str, request: dict[str, Any], directory: Path, binary: Path) -> None:
    if admission(request) != "SUPPORTED":
        raise ValueError("unsupported request")
    start = time.perf_counter()
    if system == "constraint-music":
        events = conditioned_cm(request, directory)
    elif system == "music21":
        events = music21(request, directory)
    elif system == "diatony":
        events = diatony(request, directory, binary)
    else:
        raise ValueError("unknown engine")
    save(
        directory / "artifact.json",
        {
            "request": request,
            "events": sorted(events),
            "events_sha256": content_hash(sorted(events)),
        },
    )
    if system == "diatony":
        from .render import render

        (directory / "delivered.mid").write_bytes(render(request, events))
    else:
        (directory / "delivered.mid").write_bytes((directory / "native.mid").read_bytes())
    save(
        directory / "worker_metrics.json",
        {
            "elapsed_seconds": round(time.perf_counter() - start, 6),
            "max_process_rss_kib": max(
                resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
            ),
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("system")
    parser.add_argument("request", type=Path)
    parser.add_argument("directory", type=Path)
    parser.add_argument("binary", type=Path)
    args = parser.parse_args()
    generate(
        args.system,
        json.loads(args.request.read_text()),
        args.directory.resolve(),
        args.binary.resolve(),
    )
