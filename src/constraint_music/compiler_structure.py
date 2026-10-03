from __future__ import annotations

from itertools import pairwise

from ortools.sat.python import cp_model

from .models import GenerationSpec, RhythmState
from .phrase import PhraseSpec, phrase_by_id


def _state_indicator(
    model: cp_model.CpModel,
    variable: cp_model.IntVar,
    state: RhythmState,
    name: str,
) -> cp_model.IntVar:
    flag = model.new_bool_var(name)
    model.add(variable == int(state)).only_enforce_if(flag)
    model.add(variable != int(state)).only_enforce_if(flag.negated())
    return flag


def _require_tonic_pitch(
    model: cp_model.CpModel,
    variable: cp_model.IntVar,
    allowed_notes: tuple[int, ...],
) -> None:
    model.add_allowed_assignments([variable], [(note,) for note in allowed_notes])


def _phrase_bounds(spec: GenerationSpec, phrase: PhraseSpec) -> tuple[int, int, int, int]:
    start_beat = phrase.start_bar * spec.beats_per_bar
    end_beat = phrase.end_bar * spec.beats_per_bar
    start_step = phrase.start_bar * spec.steps_per_bar
    end_step = phrase.end_bar * spec.steps_per_bar
    return start_beat, end_beat, start_step, end_step


def add_rhythm_constraints(
    model: cp_model.CpModel,
    spec: GenerationSpec,
    rhythm: list[cp_model.IntVar],
    melody_note: list[cp_model.IntVar],
) -> None:
    onset = int(RhythmState.ONSET)
    rest = int(RhythmState.REST)
    tie = int(RhythmState.TIE)
    if not spec.rhythm_enabled:
        for state in rhythm:
            model.add(state == onset)
        return

    model.add(rhythm[0] != tie)
    allowed_transitions = [
        (left, right)
        for left in range(3)
        for right in range(3)
        if not (left == rest and right == tie)
    ]
    for left, right in pairwise(rhythm):
        model.add_allowed_assignments([left, right], allowed_transitions)

    for step in range(1, spec.total_steps):
        is_tie = _state_indicator(model, rhythm[step], RhythmState.TIE, f"is_tie_{step}")
        model.add(melody_note[step] == melody_note[step - 1]).only_enforce_if(is_tie)

    rest_window = spec.max_consecutive_rests + 1
    if rest_window <= len(rhythm):
        forbidden = [(rest,) * rest_window]
        for start in range(len(rhythm) - rest_window + 1):
            model.add_forbidden_assignments(rhythm[start : start + rest_window], forbidden)

    tie_window = spec.max_tie_steps + 1
    if tie_window <= len(rhythm):
        forbidden = [(tie,) * tie_window]
        for start in range(len(rhythm) - tie_window + 1):
            model.add_forbidden_assignments(rhythm[start : start + tie_window], forbidden)

    for bar in range(spec.bars):
        start = bar * spec.steps_per_bar
        bar_vars = rhythm[start : start + spec.steps_per_bar]
        onset_flags = [
            _state_indicator(model, state, RhythmState.ONSET, f"bar_{bar}_onset_{i}")
            for i, state in enumerate(bar_vars)
        ]
        rest_flags = [
            _state_indicator(model, state, RhythmState.REST, f"bar_{bar}_rest_{i}")
            for i, state in enumerate(bar_vars)
        ]
        tie_flags = [
            _state_indicator(model, state, RhythmState.TIE, f"bar_{bar}_tie_{i}")
            for i, state in enumerate(bar_vars)
        ]
        model.add(sum(onset_flags) >= spec.min_onsets_per_bar)
        model.add(sum(onset_flags) <= spec.max_onsets_per_bar)
        model.add(sum(rest_flags) >= spec.min_rests_per_bar)
        model.add(sum(rest_flags) <= spec.max_rests_per_bar)
        model.add(sum(tie_flags) >= spec.min_ties_per_bar)
        model.add(sum(tie_flags) <= spec.max_ties_per_bar)
        if spec.require_bar_downbeat_onset:
            model.add(bar_vars[0] == onset)

    if spec.require_authentic_cadence:
        model.add(rhythm[-1] == onset)


def add_motif_constraints(
    model: cp_model.CpModel,
    spec: GenerationSpec,
    rhythm: list[cp_model.IntVar],
    melody_note: list[cp_model.IntVar],
) -> None:
    if spec.motif_relation == "none":
        return
    source = spec.motif_source_start
    target = spec.motif_target_start
    interval = 0 if spec.motif_relation == "repeat" else spec.motif_transpose_semitones
    for offset in range(spec.motif_length_steps):
        model.add(melody_note[target + offset] == melody_note[source + offset] + interval)
        model.add(rhythm[target + offset] == rhythm[source + offset])


def add_phrase_constraints(
    model: cp_model.CpModel,
    spec: GenerationSpec,
    rhythm: list[cp_model.IntVar],
    melody_note: list[cp_model.IntVar],
    bass_note: list[cp_model.IntVar],
    chord: list[cp_model.IntVar],
) -> None:
    """Compile v2.2 phrase spans, roles, relations, and cadence semantics."""
    if not spec.phrases:
        return

    onset = int(RhythmState.ONSET)
    tonic_melody = tuple(
        note
        for note in spec.tonal_key.pitches_in_range(spec.melody_low, spec.melody_high)
        if note % 12 == spec.tonal_key.tonic_pc
    )
    tonic_bass = tuple(
        note
        for note in spec.tonal_key.pitches_in_range(spec.bass_low, spec.bass_high)
        if note % 12 == spec.tonal_key.tonic_pc
    )
    phrases = phrase_by_id(spec.phrases)

    def require_phrase_close(phrase: PhraseSpec, *, strong: bool) -> None:
        start_beat, end_beat, _, end_step = _phrase_bounds(spec, phrase)
        final_beat = end_beat - 1
        final_step = end_step - 1
        model.add(chord[final_beat] == 0)
        _require_tonic_pitch(model, melody_note[final_step], tonic_melody)
        _require_tonic_pitch(model, bass_note[final_beat], tonic_bass)
        model.add(rhythm[final_step] == onset)
        if strong:
            if end_beat - start_beat < 2:
                raise ValueError(f"phrase {phrase.id!r}: strong cadence needs at least two beats")
            model.add_allowed_assignments([chord[final_beat - 1]], [(4,), (6,)])

    for phrase in spec.phrases:
        start_beat, end_beat, _, _ = _phrase_bounds(spec, phrase)
        final_beat = end_beat - 1

        if phrase.role == "antecedent":
            model.add(chord[start_beat] == 0)
            model.add(chord[final_beat] == 4)
        elif phrase.role in {"consequent", "cadential"}:
            require_phrase_close(phrase, strong=False)

        if phrase.cadence == "tonic_close":
            require_phrase_close(phrase, strong=False)
        elif phrase.cadence == "dominant_open":
            model.add(chord[final_beat] == 4)
        elif phrase.cadence == "dominant_to_tonic":
            if end_beat - start_beat < 2:
                raise ValueError(f"phrase {phrase.id!r}: dominant_to_tonic needs at least two beats")
            model.add(chord[final_beat - 1] == 4)
            require_phrase_close(phrase, strong=False)
        elif phrase.cadence == "leading_tone_to_tonic":
            if end_beat - start_beat < 2:
                raise ValueError(
                    f"phrase {phrase.id!r}: leading_tone_to_tonic needs at least two beats"
                )
            model.add(chord[final_beat - 1] == 6)
            require_phrase_close(phrase, strong=False)

        if phrase.relation == "independent":
            continue
        source = phrases[phrase.source or ""]
        _, _, source_start, _ = _phrase_bounds(spec, source)
        _, _, target_start, target_end = _phrase_bounds(spec, phrase)
        if phrase.relation in {"repeat", "transpose"}:
            interval = 0 if phrase.relation == "repeat" else phrase.transpose_semitones
            for offset in range(target_end - target_start):
                model.add(
                    melody_note[target_start + offset]
                    == melody_note[source_start + offset] + interval
                )
                model.add(rhythm[target_start + offset] == rhythm[source_start + offset])
        elif phrase.relation == "answer":
            length = phrase.relation_steps or spec.steps_per_bar
            for offset in range(length):
                model.add(
                    melody_note[target_start + offset]
                    == melody_note[source_start + offset] + phrase.transpose_semitones
                )
                model.add(rhythm[target_start + offset] == rhythm[source_start + offset])
        elif phrase.relation == "sequence":
            fragment = phrase.relation_steps or spec.steps_per_bar
            copies = (target_end - target_start) // fragment
            for copy in range(copies):
                interval = phrase.transpose_semitones + copy * phrase.sequence_step_semitones
                for offset in range(fragment):
                    model.add(
                        melody_note[target_start + copy * fragment + offset]
                        == melody_note[source_start + offset] + interval
                    )
                    model.add(
                        rhythm[target_start + copy * fragment + offset]
                        == rhythm[source_start + offset]
                    )

        if (
            phrase.role == "consequent"
            and source.role == "antecedent"
            and phrase.relation == "answer"
        ):
            source_start_beat, source_end_beat, _, _ = _phrase_bounds(spec, source)
            model.add(chord[source_start_beat] == 0)
            model.add(chord[source_end_beat - 1] == 4)
            require_phrase_close(phrase, strong=True)
