"""Spelled figured bass, native rule conditioning, and first native viable path."""

from __future__ import annotations

import itertools
from fractions import Fraction
from pathlib import Path
from typing import Any

from research.paired_cross_system_v1.adapter import save
from research.paired_cross_system_v1.contract import KEYS, VOICES


def generate(request: dict[str, Any], directory: Path, *, legacy_spelling: bool = False) -> list:
    from music21 import key, meter, note, tempo
    from music21.figuredBass import realizer, rules, segment

    old = request["schema_version"] == 1
    degrees = request["degrees"]
    tonic = KEYS[request["key"]][0]
    tonal_key = key.Key(request["key"])
    basses = request.get("bass", [48 + (tonic + (0, 2, 4, 5, 7, 9, 11)[d]) % 12 for d in degrees])
    inversions = request.get("inversions", [0] * len(degrees))
    sevenths = request.get("sevenths", [False] * len(degrees))
    duration = request["chord_quarters"]

    class ConditionedSegment(segment.Segment):
        def singlePossibilityRules(self, fbRules=None):
            native = super().singlePossibilityRules(fbRules)

            def requested(possibility):
                pitches = [int(p.midi) for p in possibility]
                ranges = ((60, 84), (55, 74), (48, 67), (48, 59))
                given = request["given_soprano"][self.request_index]
                return (
                    all(lo <= p <= hi for p, (lo, hi) in zip(pitches, ranges, strict=True))
                    and all(a > b for a, b in itertools.pairwise(pitches))
                    and pitches[0] - pitches[1] <= 12
                    and pitches[1] - pitches[2] <= 12
                    and (given is None or pitches[0] == given)
                )

            return native if old else [*native, (True, requested, True)]

        def consecutivePossibilityRules(self, fbRules=None):
            native = super().consecutivePossibilityRules(fbRules)

            def leading(left, right):
                return all(
                    a.pitchClass != (tonic + 11) % 12 or b.midi == a.midi + 1
                    for a, b in zip(left, right, strict=True)
                )

            def seventh(left, right):
                return all(
                    a.pitchClass != (tonic + 5) % 12 or b.midi - a.midi in (-1, -2)
                    for a, b in zip(left, right, strict=True)
                )

            index = self.request_index
            cadence = degrees[index : index + 2] == [4, 0]
            return [*native, (cadence, leading, True), (not old and sevenths[index], seventh, True)]

    class ConditionedLine(realizer.FiguredBassLine):
        def retrieveSegments(self, fbRules, numParts, maxPitch):
            segments = super().retrieveSegments(fbRules, numParts, maxPitch)
            for index, native in enumerate(segments):
                native.__class__ = ConditionedSegment
                native.request_index = index
            return segments

    line = ConditionedLine(tonal_key, meter.TimeSignature("4/4"))
    spellings = []
    for degree, inversion, seventh_chord, midi in zip(
        degrees, inversions, sevenths, basses, strict=True
    ):
        pitch = tonal_key.pitchFromDegree((degree + 2 * inversion) % 7 + 1)
        pitch.octave += (midi - int(pitch.midi)) // 12
        if int(pitch.midi) != midi:
            raise ValueError("bass spelling changed MIDI pitch")
        bass_note = note.Note(midi if legacy_spelling else pitch, quarterLength=duration)
        spellings.append(bass_note.pitch.nameWithOctave)
        figure = ("7", "6,5", "4,3")[inversion] if seventh_chord else ("", "6", "6,4")[inversion]
        line.addElement(bass_note, figure)
    fb_rules = rules.Rules()
    if not old:
        # Resolution shortcuts must also run the same declared single/pair obligations.
        fb_rules.applySinglePossibRulesToResolution = True
        fb_rules.applyConsecutivePossibRulesToResolution = True
        fb_rules.forbidHiddenFifths = False
        fb_rules.forbidHiddenOctaves = False
        fb_rules.forbidVoiceOverlap = False
        fb_rules.upperPartsMaxSemitoneSeparation = 24
        # The default V7 shortcut forces an incomplete tonic. Our task explicitly
        # requests complete chords, so use music21's ordinary native movement DAG.
        fb_rules.resolveDominantSeventhProperly = False
    save(
        directory / "native_input.json",
        {
            "request": request,
            "bass_spellings": spellings,
            "legacy_spelling": legacy_spelling,
            "rules": vars(fb_rules),
        },
    )
    result = line.realize(fbRules=fb_rules)
    result.keyboardStyleOutput = False
    segments = result._segmentList
    viable = set(segments[-2].movements)
    viable_sets = [viable]
    for native in reversed(segments[:-2]):
        viable = {
            a for a, successors in native.movements.items() if any(b in viable for b in successors)
        }
        viable_sets.append(viable)
    viable_sets.reverse()
    if not viable_sets[0]:
        raise ValueError("NO_SOLUTION")
    current = min(viable_sets[0], key=lambda p: tuple(x.midi for x in p))
    progression = [current]
    for index, native in enumerate(segments[:-1]):
        choices = native.movements[current]
        if index < len(segments) - 2:
            choices = [c for c in choices if c in viable_sets[index + 1]]
        current = min(choices, key=lambda p: tuple(x.midi for x in p))
        progression.append(current)
    score = result.generateRealizationFromPossibilityProgression(progression)
    score.insert(0, tempo.MetronomeMark(number=request["tempo_bpm"]))
    score.write("musicxml", fp=directory / "native_score.musicxml")
    score.write("midi", fp=directory / "native.mid")
    return sorted(
        [VOICES[i], int(n.pitch.midi), str(Fraction(n.offset)), str(Fraction(n.quarterLength))]
        for i, part in enumerate(score.parts)
        for n in part.flatten().notes
    )
