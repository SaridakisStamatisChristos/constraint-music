import pytest

from constraint_music.models import GenerationResult, GenerationSpec
from constraint_music.objective import _melody_tension_for_key, evaluate_objective_vector
from constraint_music.theory import DEGREE_TENSION


@pytest.mark.parametrize("octave_offset", (-24, -12, 0, 12, 24))
def test_chromatic_pitch_has_neutral_diatonic_tension(octave_offset: int) -> None:
    spec = GenerationSpec(bars=1, subdivisions_per_beat=1)
    chromatic_b_flat = 70 + octave_offset

    assert chromatic_b_flat % 12 not in spec.tonal_key.pitch_classes
    assert _melody_tension_for_key(spec.tonal_key, chromatic_b_flat) == 0


@pytest.mark.parametrize(
    ("degree", "pitch_class"),
    tuple(enumerate(GenerationSpec().tonal_key.pitch_classes)),
)
def test_diatonic_pitch_preserves_degree_tension(degree: int, pitch_class: int) -> None:
    key = GenerationSpec().tonal_key

    assert _melody_tension_for_key(key, pitch_class) == DEGREE_TENSION[degree]


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

    assert evaluate_objective_vector(result) == (
        ("tension_deviation", 326),
        ("melody_motion", 10),
        ("bass_motion", 0),
        ("harmonic_repetition", 0),
        ("contour_mismatch", 2),
    )
