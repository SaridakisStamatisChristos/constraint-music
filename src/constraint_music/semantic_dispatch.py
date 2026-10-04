from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from .theory import Key


class ContextualHarmonyFamily(StrEnum):
    """Mutually exclusive contextual meanings reconstructed from an artifact."""

    BORROWED_SEVENTH = "borrowed_seventh"
    SECONDARY_LEADING_TONE_TRIAD = "secondary_leading_tone_triad"
    SECONDARY_LEADING_TONE_SEVENTH = "secondary_leading_tone_seventh"


@dataclass(frozen=True, slots=True)
class ContextualHarmony:
    """A locally proven harmonic interpretation, independent of diagnostic text."""

    beat: int
    family: ContextualHarmonyFamily
    active_key: Key
    support_degree: int
    pitch_classes: tuple[int, ...]
    inversion: int
    target_degree: int | None = None
    modal_source: int | None = None
    qualities: frozenset[str] = frozenset()


SemanticDispatch = Mapping[int, ContextualHarmony]


def merge_semantic_dispatch(
    inherited: SemanticDispatch | None,
    additions: Iterable[ContextualHarmony],
) -> SemanticDispatch:
    """Merge proven interpretations and reject contradictory dispatch at one beat."""

    merged = dict(inherited or {})
    for interpretation in additions:
        previous = merged.get(interpretation.beat)
        if previous is not None and previous != interpretation:
            raise ValueError(
                f"Conflicting semantic interpretations at beat {interpretation.beat}"
            )
        merged[interpretation.beat] = interpretation
    return MappingProxyType(merged)


def has_family(
    dispatch: SemanticDispatch | None,
    beat: int,
    *families: ContextualHarmonyFamily,
) -> bool:
    interpretation = None if dispatch is None else dispatch.get(beat)
    return interpretation is not None and interpretation.family in families
