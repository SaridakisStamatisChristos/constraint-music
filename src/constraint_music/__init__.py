"""Deterministic, verifiable constraint-programming music synthesis."""

from .models import GenerationResult, GenerationSpec, RhythmState, ValidationReport
from .objective import evaluate_objective_vector
from .phrase import PhraseSpec
from .search import dominates, pareto_indices
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
    "dominates",
    "evaluate_objective_vector",
    "pareto_indices",
    "verify_result",
]

__version__ = "2.3.0a1"
