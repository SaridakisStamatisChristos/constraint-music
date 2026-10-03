from __future__ import annotations

from itertools import pairwise

from ortools.sat.python import cp_model

from .models import GenerationSpec, RhythmState


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
