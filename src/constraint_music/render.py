from __future__ import annotations

from .models import GenerationResult
from .theory import midi_note_name


def render_grid(result: GenerationResult) -> str:
    spec = result.spec
    lines = [
        f"Key: {spec.tonal_key} | {spec.bars} bars | {spec.tempo_bpm} BPM | "
        f"status={result.solver_status} | objective={result.objective_value:.1f}",
        f"Validation: {'PASS' if result.validation.valid else 'FAIL'}",
        "",
        "bar beat | chord | bass | melody                 | tension target/actual",
        "---------+-------+------+------------------------+----------------------",
    ]
    for beat in range(spec.total_beats):
        bar = beat // spec.beats_per_bar + 1
        beat_in_bar = beat % spec.beats_per_bar + 1
        start = beat * spec.subdivisions_per_beat
        notes = result.melody[start : start + spec.subdivisions_per_beat]
        note_names = " ".join(f"{midi_note_name(note):>4}" for note in notes)
        lines.append(
            f"{bar:>3} {beat_in_bar:>4} | {result.chord_names[beat]:>5} | "
            f"{midi_note_name(result.bass[beat]):>4} | {note_names:<22} | "
            f"{result.target_tension[beat]:>3}/{result.actual_tension[beat]:<3}"
        )
    if result.validation.issues:
        lines.extend(("", "Validation issues:"))
        lines.extend(f"- {issue}" for issue in result.validation.issues)
    return "\n".join(lines)
