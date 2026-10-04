from __future__ import annotations

from research.run_corruption_benchmark import run

from constraint_music.models import GenerationResult
from constraint_music.provenance import artifact_payload


def test_historical_fault_classes_never_strictly_accept(
    solved_piece: GenerationResult,
) -> None:
    results = run(artifact_payload(solved_piece), solved_piece.spec)
    assert {row["outcome"] for row in results} <= {"REJECT", "BLOCKED"}
    assert {row["case_id"] for row in results} == {
        "music.alto-pitch",
        "integrity.empty-rule-claim",
        "shape.missing-tenor",
        "harmony.illegal-inversion",
    }
