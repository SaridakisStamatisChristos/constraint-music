"""Independently specified reference relations for research evaluation.

Modules in this package must not import ``constraint_music``.  They are kept
small and mathematical so production-table changes cannot silently rewrite the
expected decisions.
"""

from .secondary_seventh import (
    OracleDecision,
    SeventhQuality,
    adjudicate_secondary_seventh,
    secondary_seventh_pitch_classes,
)

__all__ = [
    "OracleDecision",
    "SeventhQuality",
    "adjudicate_secondary_seventh",
    "secondary_seventh_pitch_classes",
]

