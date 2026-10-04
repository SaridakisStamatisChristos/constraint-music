"""Deterministic, verifiable constraint-programming music synthesis."""

from .modal_mixture import ModalSource
from .models import GenerationResult, GenerationSpec, RhythmState, ValidationReport
from .modulation import dominant_key
from .modulation_runtime import ModulatedSatbGenerationResult
from .objective import evaluate_objective_vector
from .phrase import PhraseSpec
from .satb import SatbGenerationResult
from .search import dominates, pareto_indices
from .secondary_leading_tone import (
    secondary_leading_tone_name,
    secondary_leading_tone_support_degree,
    secondary_leading_tone_triad_pitch_classes,
    supported_secondary_leading_tone_targets,
)
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
    "ModulatedSatbGenerationResult",
    "NoSolutionError",
    "PhraseSpec",
    "RhythmState",
    "SatbGenerationResult",
    "ValidationReport",
    "dominant_key",
    "dominates",
    "evaluate_objective_vector",
    "pareto_indices",
    "secondary_leading_tone_name",
    "secondary_leading_tone_support_degree",
    "secondary_leading_tone_triad_pitch_classes",
    "supported_secondary_leading_tone_targets",
    "verify_result",
]

__version__ = "2.10.0a1"
