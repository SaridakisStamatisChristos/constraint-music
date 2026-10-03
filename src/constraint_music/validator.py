"""Backward-compatible import shim for Constraint Music v1.x."""

from .verifier import validate_result, verify_result

__all__ = ["validate_result", "verify_result"]
