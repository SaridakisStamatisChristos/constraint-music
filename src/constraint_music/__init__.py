"""Deterministic, verifiable constraint-programming music synthesis."""

from .modal_mixture import ModalSource
from .models import GenerationResult, GenerationSpec, RhythmState, ValidationReport
from .objective import evaluate_objective_vector
from .phrase import PhraseSpec
from .satb import SatbGenerationResult
from .search import dominates, pareto_indices
from .solver import ConstraintMusicSolver, InternalVerificationError, NoSolutionError
from .theory import ChordKind
from .verifier import verify_result

__all__ = [
    "ChordKind",
    "ConstraintMusicSolver",
    "GenerationResult",
    "GenerationSpec",
    "InternalVerificationError",
    "ModalSource",
    "NoSolutionError",
    "PhraseSpec",
    "RhythmState",
    "SatbGenerationResult",
    "ValidationReport",
    "dominates",
    "evaluate_objective_vector",
    "pareto_indices",
    "verify_result",
]

__version__ = "2.7.0a1"
