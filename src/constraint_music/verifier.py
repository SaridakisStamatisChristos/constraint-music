from __future__ import annotations

from itertools import pairwise

from .contract import HARD_CONSTRAINT_IDS
from .models import GenerationResult, ValidationReport
from .theory import is_parallel_perfect


def verify_result(result: GenerationResult) -> ValidationReport:
    """Verify a solved or imported composition without trusting solver state.

    The verifier deliberately operates only on the serialized musical result and
    GenerationSpec. It does not inspect an OR-Tools model or solver assignment.
    """
    spec = result.spec
    key = spec.tonal_key
    melody = result.melody
    bass = result.bass
    chords = result.chord_degrees
    issues: list[str] = []
    failed: list[str] = []

    def fail(rule_id: str, message: str) -> None:
        issues.append(f"[{rule_id}] {message}")
        if rule_id not in failed:
            failed.append(rule_id)

    # CM001 — shape.
    if len(melody) != spec.total_steps:
        fail("CM001", f"Expected {spec.total_steps} melody steps, got {len(melody)}")
    if len(bass) != spec.total_beats:
        fail("CM001", f"Expected {spec.total_beats} bass notes, got {len(bass)}")
    if len(chords) != spec.total_beats:
        fail("CM001", f"Expected {spec.total_beats} chords, got {len(chords)}")

    # CM002 / CM003 — pitch domains.
    key_pcs = set(key.pitch_classes)
    for index, note in enumerate(melody):
        if note % 12 not in key_pcs:
            fail("CM002", f"Melody step {index}: note {note} is outside {key}")
        if not spec.melody_low <= note <= spec.melody_high:
            fail("CM002", f"Melody step {index}: note {note} is outside the configured range")

    for beat, note in enumerate(bass):
        if note % 12 not in key_pcs:
            fail("CM003", f"Bass beat {beat}: note {note} is outside {key}")
        if not spec.bass_low <= note <= spec.bass_high:
            fail("CM003", f"Bass beat {beat}: note {note} is outside the configured range")

    # CM004 — harmony domain.
    for beat, chord in enumerate(chords):
        if not 0 <= chord <= 6:
            fail("CM004", f"Chord beat {beat}: degree {chord} is outside 0..6")

    # CM005 / CM006 — chord membership. Guard against malformed imported shapes.
    for beat in range(min(spec.total_beats, len(chords))):
        chord = chords[beat]
        if not 0 <= chord <= 6:
            continue
        strong_step = beat * spec.subdivisions_per_beat
        if strong_step < len(melody):
            strong_note = melody[strong_step]
            if strong_note % 12 not in key.triad_pitch_classes(chord):
                fail("CM005", f"Beat {beat}: strong melody note is not in {key.chord_name(chord)}")
        if beat < len(bass) and bass[beat] % 12 not in key.triad_pitch_classes(chord):
            fail("CM006", f"Bass beat {beat}: note {bass[beat]} is not in {key.chord_name(chord)}")

    # CM007 — progression legality.
    allowed_pairs = set(spec.progression_pairs)
    for beat, pair in enumerate(pairwise(chords)):
        if pair not in allowed_pairs:
            fail("CM007", f"Chord transition at beat {beat} is not allowed: {pair}")

    # CM008 / CM009 / CM010 — adjacent melody motion.
    for step, (left, right) in enumerate(pairwise(melody)):
        delta = right - left
        if abs(delta) > spec.max_melody_leap:
            fail("CM008", f"Melody steps {step}->{step + 1}: leap exceeds limit")
        if abs(delta) % 12 == 6:
            fail("CM009", f"Melody steps {step}->{step + 1}: tritone motion is forbidden")
        if spec.resolve_leading_tone and left % 12 == key.leading_tone_pc and right != left + 1:
            fail("CM010", f"Melody step {step}: leading tone does not resolve upward to tonic")

    # CM011 — repeated note runs.
    run_length = 1
    for step in range(1, len(melody)):
        run_length = run_length + 1 if melody[step] == melody[step - 1] else 1
        if run_length > spec.max_repeated_notes:
            fail("CM011", f"Melody step {step}: too many repeated notes")

    # CM012 — recovery after a large melodic leap.
    for step in range(len(melody) - 2):
        first = melody[step + 1] - melody[step]
        second = melody[step + 2] - melody[step + 1]
        if abs(first) > 7 and not (abs(second) <= 2 and first * second < 0):
            fail(
                "CM012",
                f"Melody steps {step}->{step + 2}: large leap is not followed by "
                "contrary stepwise recovery",
            )

    # CM013 / CM014 — bass motion.
    for beat, (left, right) in enumerate(pairwise(bass)):
        delta = right - left
        if abs(delta) > spec.max_bass_leap:
            fail("CM013", f"Bass beats {beat}->{beat + 1}: leap exceeds limit")
        if abs(delta) % 12 == 6:
            fail("CM014", f"Bass beats {beat}->{beat + 1}: tritone motion is forbidden")

    # CM015 — outer-voice parallel perfect intervals.
    if spec.avoid_parallel_perfects:
        for step, (m1, m2) in enumerate(pairwise(melody)):
            first_beat = step // spec.subdivisions_per_beat
            second_beat = (step + 1) // spec.subdivisions_per_beat
            if first_beat >= len(bass) or second_beat >= len(bass):
                continue
            if is_parallel_perfect(m1, bass[first_beat], m2, bass[second_beat]):
                fail(
                    "CM015",
                    f"Parallel perfect interval between melody steps {step} and {step + 1}",
                )

    # CM016 — phrase-level cadence.
    if spec.require_authentic_cadence and chords:
        if chords[0] != 0:
            fail("CM016", "Opening chord is not tonic")
        if len(chords) < 2 or chords[-2] not in {4, 6} or chords[-1] != 0:
            fail("CM016", "Phrase does not end with dominant-function to tonic")
        if not melody or melody[-1] % 12 != key.tonic_pc:
            fail("CM016", "Final melody note is not tonic")
        if not bass or bass[-1] % 12 != key.tonic_pc:
            fail("CM016", "Final bass note is not tonic")

    return ValidationReport(
        valid=not issues,
        issues=tuple(issues),
        checked_rules=HARD_CONSTRAINT_IDS,
        failed_rules=tuple(failed),
    )


# v1 compatibility for external callers that imported the old function name.
validate_result = verify_result
