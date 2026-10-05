from constraint_music.models import GenerationResult, GenerationSpec
from constraint_music.objective import _melody_tension_for_key, evaluate_objective_vector


def test_chromatic_pitch_has_neutral_diatonic_tension() -> None:
    spec = GenerationSpec(bars=1, subdivisions_per_beat=1)
    chromatic_b_flat = 70

    assert chromatic_b_flat % 12 not in spec.tonal_key.pitch_classes
    assert _melody_tension_for_key(spec.tonal_key, chromatic_b_flat) == 0


def test_objective_recomputation_accepts_chromatic_strong_beat() -> None:
    spec = GenerationSpec(bars=1, subdivisions_per_beat=1)
    result = GenerationResult(
        spec=spec,
        melody=(70, 60, 62, 64),
        bass=(36, 38, 40, 41),
        chord_degrees=(0, 1, 2, 4),
        target_tension=spec.expanded_tension(),
        actual_tension=(0,) * spec.total_beats,
        objective_value=0.0,
        solver_status="FEASIBLE",
        wall_time_seconds=0.0,
    )

    vector = dict(evaluate_objective_vector(result))

    assert set(vector) == {
        "tension_deviation",
        "melody_motion",
        "bass_motion",
        "harmonic_repetition",
        "contour_mismatch",
    }
    assert all(isinstance(value, int) for value in vector.values())
