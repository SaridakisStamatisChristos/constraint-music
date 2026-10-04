"""Dependency-free public exception types."""


class NoSolutionError(RuntimeError):
    """Raised when CP-SAT does not produce the requested composition."""


class InternalVerificationError(RuntimeError):
    """Raised when generated output fails the independent checker."""

