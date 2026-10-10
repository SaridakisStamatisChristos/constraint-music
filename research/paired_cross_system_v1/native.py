"""Independent reconstruction from preserved generator-native score formats."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from fractions import Fraction
from typing import Any

from .contract import VOICES


def reconstruct(system: str, files: dict[str, bytes]) -> list[list[Any]]:
    events = []
    if system == "constraint-music":
        score = json.loads(files["native_score.json"])["music"]
        for voice in VOICES:
            for beat, pitch in enumerate(score[voice.lower() + "_midi"]):
                events.append([voice, pitch, str(beat), "1"])
    elif system == "diatony":
        lines = files["native_score.txt"].decode().splitlines()
        if lines[0] != "VOICE_ROWS_B_T_A_S":
            raise ValueError("native order header")
        for block, line in enumerate(lines[1:]):
            row = [int(x) for x in line.split()]
            if len(row) != 4:
                raise ValueError("native row width")
            for column, voice in enumerate(("Bass", "Tenor", "Alto", "Soprano")):
                events.append([voice, row[column], str(block * 4), "4"])
    else:
        score = ET.fromstring(files["native_score.musicxml"])
        parts = score.findall("part")
        if len(parts) != 4:
            raise ValueError("native part count")
        semitones = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
        for voice, part in zip(VOICES, parts, strict=True):
            cursor = Fraction(0)
            divisions = 1
            for measure in part.findall("measure"):
                if measure.find("backup") is not None or measure.find("forward") is not None:
                    raise ValueError("unsupported native part timing")
                division = measure.findtext("attributes/divisions")
                if division is not None:
                    divisions = int(division)
                for note in measure.findall("note"):
                    if note.find("chord") is not None or note.find("rest") is not None:
                        raise ValueError("unsupported native note")
                    step = note.findtext("pitch/step")
                    pitch = (
                        12 * (int(note.findtext("pitch/octave", "-1")) + 1)
                        + semitones[step]
                        + int(note.findtext("pitch/alter", "0"))
                    )
                    duration = Fraction(int(note.findtext("duration", "0")), divisions)
                    events.append([voice, pitch, str(cursor), str(duration)])
                    cursor += duration
    return sorted(events)


def binding(system: str, request: dict[str, Any], files: dict[str, bytes]) -> bool:
    native = json.loads(files["native_input.json"])
    if system == "constraint-music":
        spec = native["spec"]
        return (
            native["conditioning_request"] == request
            and spec["key"] == request["key"]
            and spec["bars"] == len(request["degrees"])
            and spec["tempo_bpm"] == request["tempo_bpm"]
            and spec["workers"] == 1
            and spec["max_time_seconds"] == 20
        )
    if system == "diatony":
        return (
            native["key"] == request["key"]
            and native["degrees"] == request["degrees"]
            and native["inversions"] == [0] * len(request["degrees"])
            and native["budget_ms"] == 20000
            and native["conditioning"] == "complete triads and all-voice V-I ascending leading tone"
        )
    roots = {"C": 0, "G": 7, "D": 2, "A": 9, "E": 4, "F": 5, "Bb": 10, "Eb": 3}
    steps = (0, 2, 4, 5, 7, 9, 11)
    bass = [48 + (roots[request["key"]] + steps[d]) % 12 for d in request["degrees"]]
    return (
        native["key"] == request["key"]
        and native["bass"] == bass
        and native["quarter_length"] == 4
        and native["meter"] == "4/4"
        and native["tempo"] == request["tempo_bpm"]
        and native["chorale"] is True
        and native["conditioning"] == "all-voice V-I ascending leading tone"
    )
