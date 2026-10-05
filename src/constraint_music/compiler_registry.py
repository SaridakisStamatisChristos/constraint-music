"""Auditable registration of hard-contract compiler phases.

Registrations describe which contract predicates a compiler phase implements and
the exact CP-SAT constraint span emitted by one compilation.  They are coverage
evidence, not a claim that the compiler and checker are equivalent.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from ortools.sat.python import cp_model

from .contract import rule_applicability

_T = TypeVar("_T")


@dataclass(frozen=True, slots=True)
class CompilerPhase:
    name: str
    implementation: str
    rule_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CompilerRegistration:
    phase: str
    implementation: str
    rule_ids: tuple[str, ...]
    constraint_start: int
    constraint_end: int

    @property
    def constraint_count(self) -> int:
        return self.constraint_end - self.constraint_start

    def to_dict(self) -> dict[str, object]:
        return {
            "phase": self.phase,
            "implementation": self.implementation,
            "rule_ids": list(self.rule_ids),
            "constraint_start": self.constraint_start,
            "constraint_end": self.constraint_end,
            "constraint_count": self.constraint_count,
        }


COMPILER_PHASES: tuple[CompilerPhase, ...] = (
    CompilerPhase(
        "variable_domains",
        "constraint_music.solver.ConstraintMusicSolver._compile",
        ("CM001", "CM002", "CM003", "CM004", "CM017", "CM027", "CM033", "CM043"),
    ),
    CompilerPhase(
        "harmony",
        "constraint_music.compiler_tonal.add_harmony_constraints",
        ("CM004", "CM005", "CM006", "CM007", "CM016"),
    ),
    CompilerPhase(
        "secondary_harmony",
        "constraint_music.secondary_leading_tone_complete_compiler."
        "add_complete_secondary_harmony_constraints",
        ("CM004", "CM005", "CM006", "CM007", "CM016", "CM037", "CM041", "CM052", "CM055"),
    ),
    CompilerPhase(
        "melody",
        "constraint_music.compiler_tonal.add_melodic_constraints",
        ("CM002", "CM005", "CM008", "CM009", "CM010", "CM011", "CM012", "CM016"),
    ),
    CompilerPhase(
        "secondary_melody",
        "constraint_music.secondary_leading_tone_complete_compiler."
        "add_complete_secondary_melodic_constraints",
        ("CM002", "CM005", "CM008", "CM009", "CM010", "CM011", "CM012", "CM016"),
    ),
    CompilerPhase(
        "bass",
        "constraint_music.compiler_tonal.add_bass_constraints",
        ("CM003", "CM006", "CM013", "CM014", "CM016"),
    ),
    CompilerPhase(
        "outer_voice_leading",
        "constraint_music.compiler_tonal.add_voice_leading_constraints",
        ("CM015",),
    ),
    CompilerPhase(
        "satb",
        "constraint_music.satb.add_satb_constraints",
        tuple(f"CM{number:03d}" for number in range(27, 41)),
    ),
    CompilerPhase(
        "borrowed_seventh_satb",
        "constraint_music.borrowed_seventh_runtime.add_borrowed_seventh_satb_constraints",
        tuple(f"CM{number:03d}" for number in range(27, 43))
        + tuple(f"CM{number:03d}" for number in range(49, 52)),
    ),
    CompilerPhase(
        "secondary_triad_satb",
        "constraint_music.secondary_leading_tone_runtime."
        "add_secondary_leading_tone_satb_constraints",
        tuple(f"CM{number:03d}" for number in range(27, 41))
        + tuple(f"CM{number:03d}" for number in range(52, 55)),
    ),
    CompilerPhase(
        "secondary_seventh_satb",
        "constraint_music.secondary_leading_tone_seventh_runtime."
        "add_secondary_leading_tone_seventh_satb_constraints",
        tuple(f"CM{number:03d}" for number in range(27, 58)),
    ),
    CompilerPhase(
        "modulated_satb",
        "constraint_music.modulation_runtime.add_modulated_satb_constraints",
        tuple(f"CM{number:03d}" for number in range(27, 49)),
    ),
    CompilerPhase(
        "rhythm",
        "constraint_music.compiler_structure.add_rhythm_constraints",
        ("CM017", "CM018", "CM019", "CM021"),
    ),
    CompilerPhase(
        "motif",
        "constraint_music.compiler_structure.add_motif_constraints",
        ("CM020",),
    ),
    CompilerPhase(
        "phrase",
        "constraint_music.compiler_structure.add_phrase_constraints",
        tuple(f"CM{number:03d}" for number in range(22, 27)),
    ),
)

_PHASE_BY_NAME = {phase.name: phase for phase in COMPILER_PHASES}
if len(_PHASE_BY_NAME) != len(COMPILER_PHASES):  # pragma: no cover - module invariant
    raise RuntimeError("Compiler phase names must be unique")

COMPILED_HARD_CONSTRAINT_IDS: tuple[str, ...] = tuple(
    sorted(
        {rule_id for phase in COMPILER_PHASES for rule_id in phase.rule_ids},
        key=lambda rule_id: int(rule_id[2:]),
    )
)


class CompilerRecorder:
    """Capture ordered, non-overlapping constraint spans for one compilation."""

    def __init__(self, model: cp_model.CpModel, spec: object) -> None:
        self._model = model
        self._spec = spec
        self._registrations: list[CompilerRegistration] = []

    @property
    def registrations(self) -> tuple[CompilerRegistration, ...]:
        return tuple(self._registrations)

    def call(self, phase_name: str, function: Callable[[], _T]) -> _T:
        start = len(self._model.proto.constraints)
        result = function()
        self.record_span(phase_name, start, len(self._model.proto.constraints))
        return result

    def record_span(self, phase_name: str, start: int, end: int) -> None:
        phase = _PHASE_BY_NAME[phase_name]
        if start < 0 or end < start:
            raise ValueError("Compiler constraint spans must be ordered and non-negative")
        if self._registrations and start < self._registrations[-1].constraint_end:
            raise ValueError("Compiler constraint spans must not overlap")
        applicable = tuple(
            rule_id
            for rule_id in phase.rule_ids
            if rule_applicability(rule_id, self._spec)[0]
        )
        self._registrations.append(
            CompilerRegistration(
                phase=phase.name,
                implementation=phase.implementation,
                rule_ids=applicable,
                constraint_start=start,
                constraint_end=end,
            )
        )


def compiler_phase_catalog() -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "phase": phase.name,
            "implementation": phase.implementation,
            "rule_ids": list(phase.rule_ids),
        }
        for phase in COMPILER_PHASES
    )
