from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

PHRASE_ROLES = frozenset({"statement", "antecedent", "consequent", "transition", "cadential"})
PHRASE_RELATIONS = frozenset({"independent", "repeat", "transpose", "sequence", "answer"})
PHRASE_CADENCES = frozenset(
    {"none", "tonic_close", "dominant_open", "dominant_to_tonic", "leading_tone_to_tonic"}
)


@dataclass(frozen=True, slots=True)
class PhraseSpec:
    """Declarative phrase span plus an optional relation to earlier material."""

    id: str
    start_bar: int
    bars: int
    role: str = "statement"
    cadence: str = "none"
    relation: str = "independent"
    source: str | None = None
    transpose_semitones: int = 0
    relation_steps: int = 0
    sequence_step_semitones: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", str(self.id).strip())
        object.__setattr__(self, "role", str(self.role).strip().lower())
        object.__setattr__(self, "cadence", str(self.cadence).strip().lower())
        object.__setattr__(self, "relation", str(self.relation).strip().lower())
        if self.source is not None:
            object.__setattr__(self, "source", str(self.source).strip())
        self.validate()

    @property
    def end_bar(self) -> int:
        return self.start_bar + self.bars

    def validate(self) -> None:
        if not self.id:
            raise ValueError("phrase id cannot be empty")
        if self.start_bar < 0:
            raise ValueError(f"phrase {self.id!r}: start_bar must be non-negative")
        if self.bars < 1:
            raise ValueError(f"phrase {self.id!r}: bars must be at least 1")
        if self.role not in PHRASE_ROLES:
            raise ValueError(
                f"phrase {self.id!r}: role must be one of {', '.join(sorted(PHRASE_ROLES))}"
            )
        if self.cadence not in PHRASE_CADENCES:
            raise ValueError(
                f"phrase {self.id!r}: cadence must be one of {', '.join(sorted(PHRASE_CADENCES))}"
            )
        if self.relation not in PHRASE_RELATIONS:
            raise ValueError(
                f"phrase {self.id!r}: relation must be one of {', '.join(sorted(PHRASE_RELATIONS))}"
            )
        if not -24 <= self.transpose_semitones <= 24:
            raise ValueError(f"phrase {self.id!r}: transpose_semitones must be in -24..24")
        if self.relation_steps < 0:
            raise ValueError(f"phrase {self.id!r}: relation_steps cannot be negative")
        if not -24 <= self.sequence_step_semitones <= 24:
            raise ValueError(f"phrase {self.id!r}: sequence_step_semitones must be in -24..24")
        if self.relation == "independent":
            if self.source is not None:
                raise ValueError(f"phrase {self.id!r}: independent relation cannot name a source")
        elif not self.source:
            raise ValueError(f"phrase {self.id!r}: relation {self.relation!r} requires source")
        if self.source == self.id:
            raise ValueError(f"phrase {self.id!r}: a phrase cannot relate to itself")
        if self.relation == "repeat" and self.transpose_semitones != 0:
            raise ValueError(f"phrase {self.id!r}: repeat requires transpose_semitones=0")
        if self.relation != "sequence" and self.sequence_step_semitones != 0:
            raise ValueError(
                f"phrase {self.id!r}: sequence_step_semitones is only valid for sequence"
            )

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> PhraseSpec:
        known = {item.name for item in cls.__dataclass_fields__.values()}
        unknown = sorted(set(data) - known)
        if unknown:
            raise ValueError(f"Unknown phrase keys: {', '.join(unknown)}")
        return cls(**dict(data))


def normalize_phrases(value: object) -> tuple[PhraseSpec, ...]:
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError("phrases must be an array")
    phrases: list[PhraseSpec] = []
    for index, raw in enumerate(value):
        if isinstance(raw, PhraseSpec):
            phrase = raw
        elif isinstance(raw, Mapping):
            phrase = PhraseSpec.from_mapping(raw)
        else:
            raise ValueError(f"phrases[{index}] must be an object")
        phrases.append(phrase)
    return tuple(phrases)


def phrase_by_id(phrases: tuple[PhraseSpec, ...]) -> dict[str, PhraseSpec]:
    return {phrase.id: phrase for phrase in phrases}
