"""Deterministic, verifiable constraint-programming music synthesis."""

from .models import GenerationResult, GenerationSpec, RhythmState, ValidationReport
from .phrase import PhraseSpec
from .solver import ConstraintMusicSolver, InternalVerificationError, NoSolutionError
from .verifier import verify_result

__all__ = [
    "ConstraintMusicSolver",
    "GenerationResult",
    "GenerationSpec",
    "InternalVerificationError",
    "NoSolutionError",
    "PhraseSpec",
    "RhythmState",
    "ValidationReport",
    "verify_result",
]

__version__ = "2.2.0a1"
