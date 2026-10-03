"""Deterministic, verifiable constraint-programming music synthesis."""

from .models import GenerationResult, GenerationSpec, RhythmState, ValidationReport
from .solver import ConstraintMusicSolver, InternalVerificationError, NoSolutionError
from .verifier import verify_result

__all__ = [
    "ConstraintMusicSolver",
    "GenerationResult",
    "GenerationSpec",
    "InternalVerificationError",
    "NoSolutionError",
    "RhythmState",
    "ValidationReport",
    "verify_result",
]

__version__ = "2.1.0a1"
