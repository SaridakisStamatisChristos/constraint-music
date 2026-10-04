"""Deterministic, verifiable constraint-programming music synthesis."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .certification import CertificationReport, certify_delivery, verify_artifact
from .delivery import DeliveryReport, RenderProfile, verify_delivery
from .errors import InternalVerificationError, NoSolutionError
from .modal_mixture import ModalSource
from .models import GenerationResult, GenerationSpec, RhythmState, ValidationReport
from .modulation import dominant_key
from .modulation_runtime import ModulatedSatbGenerationResult
from .objective import evaluate_objective_vector
from .phrase import PhraseSpec
from .satb import SatbGenerationResult
from .search import dominates, pareto_indices
from .secondary_leading_tone import (
    SecondaryLeadingToneSeventhQuality,
    secondary_leading_tone_name,
    secondary_leading_tone_seventh_name,
    secondary_leading_tone_seventh_pitch_class_variants,
    secondary_leading_tone_seventh_pitch_classes,
    secondary_leading_tone_seventh_qualities,
    secondary_leading_tone_seventh_support_degree,
    secondary_leading_tone_support_degree,
    secondary_leading_tone_triad_pitch_classes,
    supported_secondary_leading_tone_seventh_targets,
    supported_secondary_leading_tone_targets,
)
from .theory import ChordKind
from .verifier import verify_result

if TYPE_CHECKING:
    from .solver import ConstraintMusicSolver

__all__ = [
    "CertificationReport",
    "ChordKind",
    "ConstraintMusicSolver",
    "DeliveryReport",
    "GenerationResult",
    "GenerationSpec",
    "InternalVerificationError",
    "ModalSource",
    "ModulatedSatbGenerationResult",
    "NoSolutionError",
    "PhraseSpec",
    "RenderProfile",
    "RhythmState",
    "SatbGenerationResult",
    "SecondaryLeadingToneSeventhQuality",
    "ValidationReport",
    "certify_delivery",
    "dominant_key",
    "dominates",
    "evaluate_objective_vector",
    "pareto_indices",
    "secondary_leading_tone_name",
    "secondary_leading_tone_seventh_name",
    "secondary_leading_tone_seventh_pitch_class_variants",
    "secondary_leading_tone_seventh_pitch_classes",
    "secondary_leading_tone_seventh_qualities",
    "secondary_leading_tone_seventh_support_degree",
    "secondary_leading_tone_support_degree",
    "secondary_leading_tone_triad_pitch_classes",
    "supported_secondary_leading_tone_seventh_targets",
    "supported_secondary_leading_tone_targets",
    "verify_artifact",
    "verify_delivery",
    "verify_result",
]

__version__ = "2.13.0a1"


def __getattr__(name: str) -> Any:
    if name == "ConstraintMusicSolver":
        from .solver import ConstraintMusicSolver

        return ConstraintMusicSolver
    raise AttributeError(name)
