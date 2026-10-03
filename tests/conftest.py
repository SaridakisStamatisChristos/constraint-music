from __future__ import annotations

import pytest

from constraint_music.models import GenerationResult, GenerationSpec
from constraint_music.solver import ConstraintMusicSolver


@pytest.fixture(scope="session")
def solved_piece() -> GenerationResult:
    spec = GenerationSpec(
        bars=2,
        beats_per_bar=4,
        subdivisions_per_beat=1,
        max_time_seconds=10,
        workers=1,
        seed=123,
        tension_curve=(0.05, 0.75, 0.02),
    )
    return ConstraintMusicSolver().generate(spec)
