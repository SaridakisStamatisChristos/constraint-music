"""Independent oracle for rhythm, motif, and phrase-form rules CM017--CM026.

The oracle uses only serialized scalar values and intentionally has no production
imports.  It returns rule identifiers rather than production diagnostics so test
fixtures can compare semantic decisions without sharing implementation helpers.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise

_RHYTHM_STATES = frozenset({"rest", "onset", "tie"})


@dataclass(frozen=True, slots=True)
class FormDecision:
    failed_rules: tuple[str, ...]
    reasons: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.failed_rules


@dataclass(frozen=True, slots=True)
class RhythmPolicy:
    bars: int
    steps_per_bar: int
    enabled: bool = True
    min_onsets_per_bar: int = 0
    max_onsets_per_bar: int = 16
    min_rests_per_bar: int = 0
    max_rests_per_bar: int = 16
    min_ties_per_bar: int = 0
    max_ties_per_bar: int = 16
    max_consecutive_rests: int = 1
    max_tie_steps: int = 1
    require_bar_downbeat_onset: bool = True
    require_final_onset: bool = False


@dataclass(frozen=True, slots=True)
class OraclePhrase:
    id: str
    start_bar: int
    bars: int
    role: str = "statement"
    cadence: str = "none"
    relation: str = "independent"
    source: str | None = None
    transpose_semitones: int = 0
    relation_steps: int = 0
    sequence_step_semitones: int = 0

    @property
    def end_bar(self) -> int:
        return self.start_bar + self.bars


class _Failures:
    def __init__(self) -> None:
        self.rules: list[str] = []
        self.reasons: list[str] = []

    def add(self, rule: str, reason: str) -> None:
        if rule not in self.rules:
            self.rules.append(rule)
        self.reasons.append(f"[{rule}] {reason}")

    def decision(self) -> FormDecision:
        return FormDecision(tuple(self.rules), tuple(self.reasons))


def adjudicate_rhythm(
    melody: tuple[int, ...],
    rhythm: tuple[str, ...],
    *,
    policy: RhythmPolicy,
) -> FormDecision:
    """Adjudicate state domain, transitions, density, and final articulation."""

    failures = _Failures()
    invalid = tuple(index for index, state in enumerate(rhythm) if state not in _RHYTHM_STATES)
    if invalid:
        failures.add("CM017", f"invalid rhythm states at steps {invalid}")

    if rhythm and not invalid:
        if rhythm[0] == "tie":
            failures.add("CM018", "first rhythm step is a tie")
        tie_run = 0
        rest_run = 0
        for step, state in enumerate(rhythm):
            tie_run = tie_run + 1 if state == "tie" else 0
            rest_run = rest_run + 1 if state == "rest" else 0
            if tie_run > policy.max_tie_steps:
                failures.add("CM018", f"tie run exceeds its bound at step {step}")
            if rest_run > policy.max_consecutive_rests:
                failures.add("CM018", f"rest run exceeds its bound at step {step}")
            if state == "tie":
                if step == 0 or rhythm[step - 1] == "rest":
                    failures.add("CM018", f"tie at step {step} has no sounding predecessor")
                elif step >= len(melody) or melody[step] != melody[step - 1]:
                    failures.add("CM018", f"tie changes pitch at step {step}")

    expected_steps = policy.bars * policy.steps_per_bar
    if policy.enabled and len(rhythm) == expected_steps and not invalid:
        bounds = {
            "onset": (policy.min_onsets_per_bar, policy.max_onsets_per_bar),
            "rest": (policy.min_rests_per_bar, policy.max_rests_per_bar),
            "tie": (policy.min_ties_per_bar, policy.max_ties_per_bar),
        }
        for bar in range(policy.bars):
            start = bar * policy.steps_per_bar
            states = rhythm[start : start + policy.steps_per_bar]
            for state, (minimum, maximum) in bounds.items():
                if not minimum <= states.count(state) <= maximum:
                    failures.add("CM019", f"bar {bar + 1} {state} count is outside bounds")
            if policy.require_bar_downbeat_onset and states and states[0] != "onset":
                failures.add("CM019", f"bar {bar + 1} does not start with an onset")

    if policy.require_final_onset and rhythm and rhythm[-1] != "onset":
        failures.add("CM021", "final step is not a new onset")
    return failures.decision()


def adjudicate_motif(
    melody: tuple[int, ...],
    rhythm: tuple[str, ...],
    *,
    relation: str,
    source_start: int,
    target_start: int,
    length: int,
    transpose_semitones: int = 0,
) -> FormDecision:
    """Adjudicate an exact repeated or transposed pitch-and-rhythm motif."""

    failures = _Failures()
    if relation == "none":
        return failures.decision()
    interval = 0 if relation == "repeat" else transpose_semitones
    if relation not in {"repeat", "transpose"}:
        failures.add("CM020", f"unsupported motif relation {relation!r}")
        return failures.decision()
    if (
        source_start < 0
        or target_start < 0
        or length < 1
        or source_start + length > len(melody)
        or target_start + length > len(melody)
        or source_start + length > len(rhythm)
        or target_start + length > len(rhythm)
    ):
        failures.add("CM020", "motif window is outside serialized material")
        return failures.decision()
    for offset in range(length):
        source = source_start + offset
        target = target_start + offset
        if melody[target] != melody[source] + interval:
            failures.add("CM020", f"pitch relation fails at motif offset {offset}")
        if rhythm[target] != rhythm[source]:
            failures.add("CM020", f"rhythm relation fails at motif offset {offset}")
    return failures.decision()


def adjudicate_phrases(
    *,
    phrases: tuple[OraclePhrase, ...],
    composition_bars: int,
    beats_per_bar: int,
    steps_per_bar: int,
    tonic_pitch_class: int,
    melody: tuple[int, ...],
    rhythm: tuple[str, ...],
    bass: tuple[int, ...],
    chord_degrees: tuple[int, ...],
) -> FormDecision:
    """Adjudicate phrase spans, roles, relations, cadences, and period strength."""

    failures = _Failures()
    ids = tuple(phrase.id for phrase in phrases)
    if len(ids) != len(set(ids)):
        failures.add("CM022", "phrase ids are not unique")
    ordered = sorted(phrases, key=lambda phrase: phrase.start_bar)
    for phrase in ordered:
        if phrase.start_bar < 0 or phrase.bars < 1 or phrase.end_bar > composition_bars:
            failures.add("CM022", f"phrase {phrase.id!r} is outside the composition")
    for left, right in pairwise(ordered):
        if left.end_bar > right.start_bar:
            failures.add("CM022", f"phrases {left.id!r} and {right.id!r} overlap")

    by_id = {phrase.id: phrase for phrase in phrases}

    def bounds(phrase: OraclePhrase) -> tuple[int, int, int, int]:
        return (
            phrase.start_bar * beats_per_bar,
            phrase.end_bar * beats_per_bar,
            phrase.start_bar * steps_per_bar,
            phrase.end_bar * steps_per_bar,
        )

    def tonic_close(phrase: OraclePhrase, penultimate: int | None = None) -> bool:
        start_beat, end_beat, _, end_step = bounds(phrase)
        final_beat = end_beat - 1
        final_step = end_step - 1
        if (
            end_beat <= start_beat
            or not 0 <= final_beat < len(chord_degrees)
            or final_beat >= len(bass)
            or not 0 <= final_step < len(melody)
            or final_step >= len(rhythm)
        ):
            return False
        closed = (
            chord_degrees[final_beat] == 0
            and melody[final_step] % 12 == tonic_pitch_class
            and bass[final_beat] % 12 == tonic_pitch_class
            and rhythm[final_step] == "onset"
        )
        if not closed or penultimate is None:
            return closed
        return (
            final_beat - 1 >= start_beat
            and final_beat - 1 < len(chord_degrees)
            and chord_degrees[final_beat - 1] == penultimate
        )

    def fragment_matches(
        source_start: int,
        target_start: int,
        source_offset: int,
        target_offset: int,
        length: int,
        interval: int,
    ) -> bool:
        if length < 0:
            return False
        for offset in range(length):
            source = source_start + source_offset + offset
            target = target_start + target_offset + offset
            if (
                not 0 <= source < len(melody)
                or source >= len(rhythm)
                or not 0 <= target < len(melody)
                or target >= len(rhythm)
                or melody[target] != melody[source] + interval
                or rhythm[target] != rhythm[source]
            ):
                return False
        return True

    for phrase in phrases:
        start_beat, end_beat, _, _ = bounds(phrase)
        final_beat = end_beat - 1
        if phrase.role == "antecedent":
            if not 0 <= start_beat < len(chord_degrees) or chord_degrees[start_beat] != 0:
                failures.add("CM023", f"antecedent {phrase.id!r} does not open on tonic")
            if not 0 <= final_beat < len(chord_degrees) or chord_degrees[final_beat] != 4:
                failures.add("CM023", f"antecedent {phrase.id!r} does not end on dominant")
        elif phrase.role in {"consequent", "cadential"} and not tonic_close(phrase):
            failures.add("CM023", f"role {phrase.role!r} lacks an articulated tonic close")

        if phrase.cadence == "tonic_close" and not tonic_close(phrase):
            failures.add("CM025", f"phrase {phrase.id!r} lacks tonic_close")
        elif phrase.cadence == "dominant_open":
            if not 0 <= final_beat < len(chord_degrees) or chord_degrees[final_beat] != 4:
                failures.add("CM025", f"phrase {phrase.id!r} lacks dominant_open")
        elif phrase.cadence == "dominant_to_tonic" and not tonic_close(phrase, 4):
            failures.add("CM025", f"phrase {phrase.id!r} lacks dominant_to_tonic")
        elif phrase.cadence == "leading_tone_to_tonic" and not tonic_close(phrase, 6):
            failures.add("CM025", f"phrase {phrase.id!r} lacks leading_tone_to_tonic")

        if phrase.relation == "independent":
            continue
        source_phrase = by_id.get(phrase.source or "")
        if source_phrase is None:
            failures.add("CM024", f"phrase {phrase.id!r} names a missing source")
            continue
        _, _, source_start, source_end = bounds(source_phrase)
        _, _, target_start, target_end = bounds(phrase)
        relation_ok = True
        if phrase.relation in {"repeat", "transpose"}:
            length = target_end - target_start
            interval = 0 if phrase.relation == "repeat" else phrase.transpose_semitones
            relation_ok = source_end - source_start == length and fragment_matches(
                source_start, target_start, 0, 0, length, interval
            )
        elif phrase.relation == "answer":
            length = phrase.relation_steps or steps_per_bar
            relation_ok = fragment_matches(
                source_start,
                target_start,
                0,
                0,
                length,
                phrase.transpose_semitones,
            )
        elif phrase.relation == "sequence":
            fragment = phrase.relation_steps or steps_per_bar
            target_length = target_end - target_start
            relation_ok = fragment > 0 and target_length % fragment == 0
            if relation_ok:
                for copy in range(target_length // fragment):
                    interval = (
                        phrase.transpose_semitones
                        + copy * phrase.sequence_step_semitones
                    )
                    if not fragment_matches(
                        source_start,
                        target_start,
                        0,
                        copy * fragment,
                        fragment,
                        interval,
                    ):
                        relation_ok = False
                        break
        else:
            relation_ok = False
        if not relation_ok:
            failures.add("CM024", f"phrase {phrase.id!r} violates {phrase.relation!r}")

        if (
            phrase.role == "consequent"
            and source_phrase.role == "antecedent"
            and phrase.relation == "answer"
        ):
            source_start_beat, source_end_beat, _, _ = bounds(source_phrase)
            target_penultimate = final_beat - 1
            pair_ok = (
                0 <= source_start_beat < len(chord_degrees)
                and chord_degrees[source_start_beat] == 0
                and 0 <= source_end_beat - 1 < len(chord_degrees)
                and chord_degrees[source_end_beat - 1] == 4
                and tonic_close(phrase)
                and target_penultimate >= start_beat
                and target_penultimate < len(chord_degrees)
                and chord_degrees[target_penultimate] in {4, 6}
            )
            if not pair_ok:
                failures.add("CM026", f"period {source_phrase.id!r}->{phrase.id!r} is weak")

    return failures.decision()
