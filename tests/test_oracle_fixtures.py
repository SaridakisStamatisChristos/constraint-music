from __future__ import annotations

import ast
from pathlib import Path

from research.oracle.secondary_seventh import (
    SeventhQuality,
    adjudicate_secondary_seventh,
    secondary_seventh_pitch_classes,
)


def test_oracle_has_no_production_semantic_imports() -> None:
    root = Path(__file__).parents[1] / "research" / "oracle"
    for source in root.glob("*.py"):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        imports = [
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        ]
        assert not any(name.startswith("constraint_music") for name in imports)


def test_independent_oracle_accepts_exact_third_inversion() -> None:
    expected = secondary_seventh_pitch_classes(9, SeventhQuality.FULLY_DIMINISHED)
    voices = (expected[0] + 60, expected[1] + 60, expected[2] + 48, expected[3] + 36)
    decision = adjudicate_secondary_seventh(
        voices,
        target_pitch_class=9,
        quality=SeventhQuality.FULLY_DIMINISHED,
        inversion=3,
        half_diminished_eligible=True,
    )
    assert decision.valid


def test_independent_oracle_rejects_wrong_bass_and_duplicate_tone() -> None:
    expected = secondary_seventh_pitch_classes(9, SeventhQuality.FULLY_DIMINISHED)
    wrong_bass = (expected[0], expected[1], expected[2], expected[0])
    decision = adjudicate_secondary_seventh(
        wrong_bass,
        target_pitch_class=9,
        quality=SeventhQuality.FULLY_DIMINISHED,
        inversion=3,
        half_diminished_eligible=True,
    )
    assert not decision.valid
