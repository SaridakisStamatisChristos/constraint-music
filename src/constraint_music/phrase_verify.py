from __future__ import annotations

from .models import GenerationResult, RhythmState
from .phrase import PhraseSpec, phrase_by_id

PhraseIssue = tuple[str, str]


def _bounds(result: GenerationResult, phrase: PhraseSpec) -> tuple[int, int, int, int]:
    spec = result.spec
    start_beat = phrase.start_bar * spec.beats_per_bar
    end_beat = phrase.end_bar * spec.beats_per_bar
    start_step = phrase.start_bar * spec.steps_per_bar
    end_step = phrase.end_bar * spec.steps_per_bar
    return start_beat, end_beat, start_step, end_step


def phrase_verification_issues(result: GenerationResult) -> tuple[PhraseIssue, ...]:
    """Independently reconstruct all v2.2 phrase hard rules from serialized values."""
    spec = result.spec
    if not spec.phrases:
        return ()

    melody = result.melody
    rhythm = result.effective_rhythm
    bass = result.bass
    chords = result.chord_degrees
    key = spec.tonal_key
    issues: list[PhraseIssue] = []

    def fail(rule_id: str, message: str) -> None:
        issues.append((rule_id, message))

    def has_beat(index: int) -> bool:
        return 0 <= index < len(chords) and index < len(bass)

    def has_step(index: int) -> bool:
        return 0 <= index < len(melody) and index < len(rhythm)

    def tonic_close_ok(phrase: PhraseSpec, penultimate: int | None = None) -> bool:
        start_beat, end_beat, _, end_step = _bounds(result, phrase)
        final_beat = end_beat - 1
        final_step = end_step - 1
        if end_beat <= start_beat or not has_beat(final_beat) or not has_step(final_step):
            return False
        if chords[final_beat] != 0:
            return False
        if melody[final_step] % 12 != key.tonic_pc or bass[final_beat] % 12 != key.tonic_pc:
            return False
        if rhythm[final_step] != RhythmState.ONSET:
            return False
        if penultimate is not None:
            if final_beat - 1 < start_beat or not has_beat(final_beat - 1):
                return False
            if chords[final_beat - 1] != penultimate:
                return False
        return True

    ids = [phrase.id for phrase in spec.phrases]
    if len(ids) != len(set(ids)):
        fail("CM022", "Phrase ids are not unique")
    ordered = sorted(spec.phrases, key=lambda phrase: phrase.start_bar)
    for phrase in ordered:
        if phrase.start_bar < 0 or phrase.end_bar > spec.bars:
            fail("CM022", f"Phrase {phrase.id!r} is outside the composition span")
    for left, right in zip(ordered, ordered[1:], strict=False):
        if left.end_bar > right.start_bar:
            fail("CM022", f"Phrases {left.id!r} and {right.id!r} overlap")

    by_id = phrase_by_id(spec.phrases)
    for phrase in spec.phrases:
        start_beat, end_beat, _, end_step = _bounds(result, phrase)
        final_beat = end_beat - 1
        final_step = end_step - 1

        if phrase.role == "antecedent":
            if not has_beat(start_beat) or chords[start_beat] != 0:
                fail("CM023", f"Antecedent {phrase.id!r} does not open on tonic")
            if not has_beat(final_beat) or chords[final_beat] != 4:
                fail("CM023", f"Antecedent {phrase.id!r} does not end dominant-open")
        elif phrase.role in {"consequent", "cadential"}:
            if not tonic_close_ok(phrase):
                fail("CM023", f"Phrase {phrase.id!r} role requires an articulated tonic close")

        if phrase.cadence == "tonic_close" and not tonic_close_ok(phrase):
            fail("CM025", f"Phrase {phrase.id!r} violates tonic_close")
        elif phrase.cadence == "dominant_open":
            if not has_beat(final_beat) or chords[final_beat] != 4:
                fail("CM025", f"Phrase {phrase.id!r} violates dominant_open")
        elif phrase.cadence == "dominant_to_tonic" and not tonic_close_ok(phrase, 4):
            fail("CM025", f"Phrase {phrase.id!r} violates dominant_to_tonic")
        elif phrase.cadence == "leading_tone_to_tonic" and not tonic_close_ok(phrase, 6):
            fail("CM025", f"Phrase {phrase.id!r} violates leading_tone_to_tonic")

        if phrase.relation == "independent":
            continue
        source = by_id.get(phrase.source or "")
        if source is None:
            fail("CM024", f"Phrase {phrase.id!r} names missing source {phrase.source!r}")
            continue
        _, _, source_start, source_end = _bounds(result, source)
        _, _, target_start, target_end = _bounds(result, phrase)

        def compare_fragment(
            source_offset: int,
            target_offset: int,
            length: int,
            interval: int,
        ) -> bool:
            for offset in range(length):
                source_index = source_start + source_offset + offset
                target_index = target_start + target_offset + offset
                if not has_step(source_index) or not has_step(target_index):
                    return False
                if melody[target_index] != melody[source_index] + interval:
                    return False
                if rhythm[target_index] != rhythm[source_index]:
                    return False
            return True

        relation_ok = True
        if phrase.relation in {"repeat", "transpose"}:
            length = target_end - target_start
            interval = 0 if phrase.relation == "repeat" else phrase.transpose_semitones
            relation_ok = source_end - source_start == length and compare_fragment(0, 0, length, interval)
        elif phrase.relation == "answer":
            length = phrase.relation_steps or spec.steps_per_bar
            relation_ok = compare_fragment(0, 0, length, phrase.transpose_semitones)
        elif phrase.relation == "sequence":
            fragment = phrase.relation_steps or spec.steps_per_bar
            target_length = target_end - target_start
            if fragment <= 0 or target_length % fragment != 0:
                relation_ok = False
            else:
                for copy in range(target_length // fragment):
                    interval = phrase.transpose_semitones + copy * phrase.sequence_step_semitones
                    if not compare_fragment(0, copy * fragment, fragment, interval):
                        relation_ok = False
                        break
        if not relation_ok:
            fail("CM024", f"Phrase {phrase.id!r} violates {phrase.relation} relation")

        if phrase.role == "consequent" and source.role == "antecedent" and phrase.relation == "answer":
            source_start_beat, source_end_beat, _, _ = _bounds(result, source)
            pair_ok = (
                has_beat(source_start_beat)
                and chords[source_start_beat] == 0
                and has_beat(source_end_beat - 1)
                and chords[source_end_beat - 1] == 4
                and tonic_close_ok(phrase)
            )
            if pair_ok:
                target_final_beat = end_beat - 1
                pair_ok = (
                    target_final_beat - 1 >= start_beat
                    and has_beat(target_final_beat - 1)
                    and chords[target_final_beat - 1] in {4, 6}
                )
            if not pair_ok:
                fail(
                    "CM026",
                    f"Antecedent/consequent pair {source.id!r}->{phrase.id!r} lacks open-to-strong closure",
                )

        _ = final_step

    return tuple(issues)
