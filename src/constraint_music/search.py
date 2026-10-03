from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TypeAlias

OBJECTIVE_COMPONENTS: tuple[str, ...] = (
    "tension_deviation",
    "melody_motion",
    "bass_motion",
    "harmonic_repetition",
    "contour_mismatch",
)
DEFAULT_OBJECTIVE_WEIGHTS: tuple[tuple[str, int], ...] = (
    ("tension_deviation", 8),
    ("melody_motion", 2),
    ("bass_motion", 3),
    ("harmonic_repetition", 1),
    ("contour_mismatch", 4),
)
DISTINCT_DIMENSIONS: tuple[str, ...] = ("melody", "rhythm", "bass", "harmony")

ObjectiveVector: TypeAlias = tuple[tuple[str, int], ...]


def normalize_distinct_on(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        items = tuple(part.strip().lower() for part in value.split(",") if part.strip())
    elif isinstance(value, Sequence):
        items = tuple(str(item).strip().lower() for item in value)
    else:
        raise ValueError("distinct_on must be a sequence or comma-separated string")
    if not items:
        raise ValueError("distinct_on must select at least one dimension")
    if len(items) != len(set(items)):
        raise ValueError("distinct_on cannot contain duplicates")
    unknown = sorted(set(items) - set(DISTINCT_DIMENSIONS))
    if unknown:
        raise ValueError(f"Unknown distinctness dimensions: {', '.join(unknown)}")
    return items


def normalize_objective_weights(value: object) -> ObjectiveVector:
    weights = dict(DEFAULT_OBJECTIVE_WEIGHTS)
    if isinstance(value, Mapping):
        supplied = {str(name): int(weight) for name, weight in value.items()}
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        supplied: dict[str, int] = {}
        for item in value:
            if not isinstance(item, Sequence) or isinstance(item, (str, bytes)) or len(item) != 2:
                raise ValueError("objective_weights entries must be [name, weight] pairs")
            supplied[str(item[0])] = int(item[1])
    else:
        raise ValueError("objective_weights must be a mapping or sequence of pairs")
    unknown = sorted(set(supplied) - set(OBJECTIVE_COMPONENTS))
    if unknown:
        raise ValueError(f"Unknown objective components: {', '.join(unknown)}")
    weights.update(supplied)
    if any(weight < 0 or weight > 1000 for weight in weights.values()):
        raise ValueError("objective weights must be in 0..1000")
    if not any(weights.values()):
        raise ValueError("at least one objective weight must be positive")
    return tuple((name, weights[name]) for name in OBJECTIVE_COMPONENTS)


def objective_mapping(vector: ObjectiveVector) -> dict[str, int]:
    return {name: int(value) for name, value in vector}


def dominates(left: ObjectiveVector, right: ObjectiveVector) -> bool:
    left_map = objective_mapping(left)
    right_map = objective_mapping(right)
    if set(left_map) != set(right_map):
        raise ValueError("objective vectors must use the same components")
    return all(left_map[name] <= right_map[name] for name in left_map) and any(
        left_map[name] < right_map[name] for name in left_map
    )


def pareto_indices(vectors: Sequence[ObjectiveVector]) -> tuple[int, ...]:
    front: list[int] = []
    for index, vector in enumerate(vectors):
        if any(
            other_index != index and dominates(other, vector)
            for other_index, other in enumerate(vectors)
        ):
            continue
        front.append(index)
    return tuple(front)


def scalarization_profiles(base: ObjectiveVector, count: int) -> tuple[ObjectiveVector, ...]:
    if count < 1:
        raise ValueError("count must be positive")
    base_map = objective_mapping(base)
    profiles: list[ObjectiveVector] = [base]
    multipliers = (2, 4, 8, 16)
    cursor = 0
    while len(profiles) < count:
        component = OBJECTIVE_COMPONENTS[cursor % len(OBJECTIVE_COMPONENTS)]
        multiplier = multipliers[(cursor // len(OBJECTIVE_COMPONENTS)) % len(multipliers)]
        profile: list[tuple[str, int]] = []
        for name in OBJECTIVE_COMPONENTS:
            weight = base_map[name]
            weight = (
                max(1, weight) * multiplier
                if name == component
                else max(1, weight // 2)
            )
            profile.append((name, min(weight, 1000)))
        profiles.append(tuple(profile))
        cursor += 1
    return tuple(profiles)
