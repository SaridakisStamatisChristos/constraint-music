from __future__ import annotations

from constraint_music.contract import HARD_CONSTRAINT_IDS
from constraint_music.models import GenerationSpec
from constraint_music.solver import COMPILED_HARD_CONSTRAINT_IDS, ConstraintMusicSolver


def small_spec(**overrides: object) -> GenerationSpec:
    payload: dict[str, object] = {
        "bars": 2,
        "beats_per_bar": 4,
        "subdivisions_per_beat": 1,
        "max_time_seconds": 10,
        "workers": 1,
        "seed": 123,
        "tension_curve": (0.05, 0.75, 0.02),
    }
    payload.update(overrides)
    return GenerationSpec(**payload)


def test_solver_and_contract_declare_same_hard_rules() -> None:
    assert COMPILED_HARD_CONSTRAINT_IDS == HARD_CONSTRAINT_IDS


def test_solver_produces_independently_verified_piece() -> None:
    result = ConstraintMusicSolver().generate(small_spec())
    assert result.validation.valid, result.validation.issues
    assert result.validation.checked_rules == HARD_CONSTRAINT_IDS
    assert result.validation.failed_rules == ()


def test_seed_is_reproducible_under_single_worker() -> None:
    spec = small_spec()
    first = ConstraintMusicSolver().generate(spec)
    second = ConstraintMusicSolver().generate(spec)
    assert first.melody == second.melody
    assert first.bass == second.bass
    assert first.chord_degrees == second.chord_degrees


def test_minor_mode() -> None:
    result = ConstraintMusicSolver().generate(
        small_spec(key="D", mode="minor", melody_low=62, melody_high=82)
    )
    assert result.validation.valid, result.validation.issues


def test_progression_graph_is_configurable_per_spec() -> None:
    self_loops = {degree: [degree] for degree in range(7)}
    result = ConstraintMusicSolver().generate(
        small_spec(require_authentic_cadence=False, progression_graph=self_loops)
    )
    assert result.validation.valid, result.validation.issues
    assert len(set(result.chord_degrees)) == 1
