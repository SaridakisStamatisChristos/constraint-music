from __future__ import annotations

from constraint_music.models import GenerationSpec
from constraint_music.objective import evaluate_objective_vector
from constraint_music.provenance import artifact_payload, verify_artifact_integrity
from constraint_music.search import dominates, pareto_indices
from constraint_music.solver import ConstraintMusicSolver


def search_spec(**overrides: object) -> GenerationSpec:
    payload: dict[str, object] = {
        "bars": 2,
        "beats_per_bar": 4,
        "subdivisions_per_beat": 1,
        "require_authentic_cadence": False,
        "max_time_seconds": 10,
        "workers": 1,
        "seed": 731,
        "tension_curve": (0.05, 0.75, 0.05),
    }
    payload.update(overrides)
    return GenerationSpec(**payload)


def test_no_good_enumeration_returns_distinct_melodies() -> None:
    results = ConstraintMusicSolver().generate_many(search_spec(), 3, ("melody",))
    assert len({result.melody for result in results}) == 3
    assert all(result.validation.valid for result in results)


def test_no_good_enumeration_can_target_harmony() -> None:
    results = ConstraintMusicSolver().generate_many(search_spec(), 2, ("harmony",))
    assert results[0].chord_degrees != results[1].chord_degrees


def test_single_worker_enumeration_is_deterministic() -> None:
    spec = search_spec()
    first = ConstraintMusicSolver().generate_many(spec, 3, ("melody", "harmony"))
    second = ConstraintMusicSolver().generate_many(spec, 3, ("melody", "harmony"))
    assert [result.melody for result in first] == [result.melody for result in second]
    assert [result.chord_degrees for result in first] == [result.chord_degrees for result in second]


def test_pareto_helpers_detect_dominance() -> None:
    left = (("a", 1), ("b", 2))
    right = (("a", 2), ("b", 2))
    tradeoff = (("a", 0), ("b", 4))
    assert dominates(left, right)
    assert not dominates(right, left)
    assert pareto_indices((left, right, tradeoff)) == (0, 2)


def test_pareto_search_returns_pairwise_nondominated_results() -> None:
    results = ConstraintMusicSolver().generate_pareto(
        search_spec(),
        count=3,
        distinct_on=("melody", "harmony"),
        candidate_multiplier=2,
    )
    assert 1 <= len(results) <= 3
    vectors = [evaluate_objective_vector(result) for result in results]
    for index, vector in enumerate(vectors):
        assert not any(
            other_index != index and dominates(other, vector)
            for other_index, other in enumerate(vectors)
        )


def test_artifact_objective_vector_is_independently_verified() -> None:
    result = ConstraintMusicSolver().generate(search_spec())
    payload = artifact_payload(result)
    assert verify_artifact_integrity(result, payload) == ()
    payload["search"]["objective_vector"]["tension_deviation"] += 1
    issues = verify_artifact_integrity(result, payload)
    assert "objective vector metadata mismatch" in issues
    assert "artifact content digest mismatch" in issues
