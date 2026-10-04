from __future__ import annotations

from itertools import pairwise

from .contract import HARD_CONSTRAINT_IDS
from .models import GenerationResult, RhythmState, ValidationReport
from .modulation_runtime import (
    modulated_satb_verification_issues,
    modulation_verification_issues,
)
from .phrase_verify import phrase_verification_issues
from .satb import satb_verification_issues
from .theory import is_parallel_perfect


def verify_result(result: GenerationResult) -> ValidationReport:
    """Verify a solved or imported composition without trusting solver state."""
    spec = result.spec
    key = spec.tonal_key
    melody = result.melody
    rhythm = result.effective_rhythm
    bass = result.bass
    chords = result.chord_degrees
    issues: list[str] = []
    failed: list[str] = []

    def fail(rule_id: str, message: str) -> None:
        issues.append(f"[{rule_id}] {message}")
        if rule_id not in failed:
            failed.append(rule_id)

    if len(melody) != spec.total_steps:
        fail("CM001", f"Expected {spec.total_steps} melody steps, got {len(melody)}")
    if len(rhythm) != spec.total_steps:
        fail("CM001", f"Expected {spec.total_steps} rhythm steps, got {len(rhythm)}")
    if len(bass) != spec.total_beats:
        fail("CM001", f"Expected {spec.total_beats} bass notes, got {len(bass)}")
    if len(chords) != spec.total_beats:
        fail("CM001", f"Expected {spec.total_beats} chords, got {len(chords)}")

    for index, note in enumerate(melody):
        active_key = (
            spec.active_key_at_beat(index // spec.subdivisions_per_beat)
            if spec.modulation_enabled
            else key
        )
        if note % 12 not in active_key.pitch_classes:
            fail(
                "CM002",
                f"Melody step {index}: note {note} is outside {active_key}",
            )
        if not spec.melody_low <= note <= spec.melody_high:
            fail("CM002", f"Melody step {index}: note {note} is outside the configured range")

    for beat, note in enumerate(bass):
        active_key = spec.active_key_at_beat(beat) if spec.modulation_enabled else key
        if note % 12 not in active_key.pitch_classes:
            fail("CM003", f"Bass beat {beat}: note {note} is outside {active_key}")
        if not spec.bass_low <= note <= spec.bass_high:
            fail("CM003", f"Bass beat {beat}: note {note} is outside the configured range")

    for beat, chord in enumerate(chords):
        if not 0 <= chord <= 6:
            fail("CM004", f"Chord beat {beat}: degree {chord} is outside 0..6")

    for beat in range(min(spec.total_beats, len(chords))):
        chord = chords[beat]
        if not 0 <= chord <= 6:
            continue
        active_key = spec.active_key_at_beat(beat)
        strong_step = beat * spec.subdivisions_per_beat
        if strong_step < len(melody):
            strong_note = melody[strong_step]
            if strong_note % 12 not in active_key.triad_pitch_classes(chord):
                fail(
                    "CM005",
                    f"Beat {beat}: strong melody note is not in active-key "
                    f"{active_key.chord_name(chord)}",
                )
        if beat < len(bass) and bass[beat] % 12 not in active_key.triad_pitch_classes(chord):
            fail(
                "CM006",
                f"Bass beat {beat}: note {bass[beat]} is not in active-key "
                f"{active_key.chord_name(chord)}",
            )

    allowed_pairs = set(spec.progression_pairs)
    for beat, pair in enumerate(pairwise(chords)):
        if pair not in allowed_pairs:
            fail("CM007", f"Chord transition at beat {beat} is not allowed: {pair}")

    for step, (left, right) in enumerate(pairwise(melody)):
        delta = right - left
        if abs(delta) > spec.max_melody_leap:
            fail("CM008", f"Melody steps {step}->{step + 1}: leap exceeds limit")
        if abs(delta) % 12 == 6:
            fail("CM009", f"Melody steps {step}->{step + 1}: tritone motion is forbidden")
        active_key = (
            spec.active_key_at_beat(step // spec.subdivisions_per_beat)
            if spec.modulation_enabled
            else key
        )
        if (
            spec.resolve_leading_tone
            and left % 12 == active_key.leading_tone_pc
            and right != left + 1
        ):
            fail("CM010", f"Melody step {step}: leading tone does not resolve upward to tonic")

    run_length = 1
    for step in range(1, len(melody)):
        run_length = run_length + 1 if melody[step] == melody[step - 1] else 1
        if run_length > spec.max_repeated_notes:
            fail("CM011", f"Melody step {step}: too many repeated notes")

    for step in range(len(melody) - 2):
        first = melody[step + 1] - melody[step]
        second = melody[step + 2] - melody[step + 1]
        if abs(first) > 7 and not (abs(second) <= 2 and first * second < 0):
            fail(
                "CM012",
                f"Melody steps {step}->{step + 2}: large leap is not followed by "
                "contrary stepwise recovery",
            )

    for beat, (left, right) in enumerate(pairwise(bass)):
        delta = right - left
        if abs(delta) > spec.max_bass_leap:
            fail("CM013", f"Bass beats {beat}->{beat + 1}: leap exceeds limit")
        if abs(delta) % 12 == 6:
            fail("CM014", f"Bass beats {beat}->{beat + 1}: tritone motion is forbidden")

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

    if spec.require_authentic_cadence and chords:
        if chords[0] != 0:
            fail("CM016", "Opening chord is not tonic")
        if len(chords) < 2 or chords[-2] not in {4, 6} or chords[-1] != 0:
            fail("CM016", "Piece does not end with dominant-function to tonic")
        if not melody or melody[-1] % 12 != key.tonic_pc:
            fail("CM016", "Final melody note is not tonic")
        if not bass or bass[-1] % 12 != key.tonic_pc:
            fail("CM016", "Final bass note is not tonic")

    valid_states = {RhythmState.REST, RhythmState.ONSET, RhythmState.TIE}
    for step, state in enumerate(rhythm):
        if state not in valid_states:
            fail("CM017", f"Rhythm step {step}: invalid state {state!r}")

    if rhythm:
        if rhythm[0] == RhythmState.TIE:
            fail("CM018", "The first rhythm step cannot be a tie")
        tie_run = 0
        rest_run = 0
        for step, state in enumerate(rhythm):
            tie_run = tie_run + 1 if state == RhythmState.TIE else 0
            rest_run = rest_run + 1 if state == RhythmState.REST else 0
            if tie_run > spec.max_tie_steps:
                fail("CM018", f"Rhythm step {step}: tie run exceeds max_tie_steps")
            if rest_run > spec.max_consecutive_rests:
                fail("CM018", f"Rhythm step {step}: rest run exceeds max_consecutive_rests")
            if state == RhythmState.TIE:
                if step == 0 or rhythm[step - 1] == RhythmState.REST:
                    fail("CM018", f"Rhythm step {step}: tie does not extend a sounding note")
                elif step < len(melody) and melody[step] != melody[step - 1]:
                    fail("CM018", f"Rhythm step {step}: tied pitch changed")

    if spec.rhythm_enabled and len(rhythm) == spec.total_steps:
        for bar in range(spec.bars):
            start = bar * spec.steps_per_bar
            states = rhythm[start : start + spec.steps_per_bar]
            counts = {state: states.count(state) for state in RhythmState}
            if not spec.min_onsets_per_bar <= counts[RhythmState.ONSET] <= spec.max_onsets_per_bar:
                fail("CM019", f"Bar {bar + 1}: onset count is outside configured bounds")
            if not spec.min_rests_per_bar <= counts[RhythmState.REST] <= spec.max_rests_per_bar:
                fail("CM019", f"Bar {bar + 1}: rest count is outside configured bounds")
            if not spec.min_ties_per_bar <= counts[RhythmState.TIE] <= spec.max_ties_per_bar:
                fail("CM019", f"Bar {bar + 1}: tie count is outside configured bounds")
            if spec.require_bar_downbeat_onset and states and states[0] != RhythmState.ONSET:
                fail("CM019", f"Bar {bar + 1}: downbeat is not an onset")

    if (
        spec.motif_relation != "none"
        and len(melody) == spec.total_steps
        and len(rhythm) == spec.total_steps
    ):
        source = spec.motif_source_start
        target = spec.motif_target_start
        interval = 0 if spec.motif_relation == "repeat" else spec.motif_transpose_semitones
        for offset in range(spec.motif_length_steps):
            if melody[target + offset] != melody[source + offset] + interval:
                fail("CM020", f"Motif step {offset}: pitch relation is violated")
            if rhythm[target + offset] != rhythm[source + offset]:
                fail("CM020", f"Motif step {offset}: rhythm relation is violated")

    if spec.require_authentic_cadence and rhythm and rhythm[-1] != RhythmState.ONSET:
        fail("CM021", "Final tonic must be a newly articulated onset")

    for rule_id, message in phrase_verification_issues(result):
        fail(rule_id, message)
    satb_issues = (
        modulated_satb_verification_issues(result)
        if spec.modulation_enabled
        else satb_verification_issues(result)
    )
    for rule_id, message in satb_issues:
        fail(rule_id, message)
    for rule_id, message in modulation_verification_issues(result):
        fail(rule_id, message)

    return ValidationReport(
        valid=not issues,
        issues=tuple(issues),
        checked_rules=HARD_CONSTRAINT_IDS,
        failed_rules=tuple(failed),
    )


validate_result = verify_result
