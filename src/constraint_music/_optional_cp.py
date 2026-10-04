"""Type-safe optional access to OR-Tools for mixed compiler/checker modules."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from ortools.sat.python import cp_model as cp_model
else:
    try:
        from ortools.sat.python import cp_model as cp_model
    except ModuleNotFoundError:

        class _MissingCpModel:
            def __getattr__(self, name: str) -> Any:
                raise ModuleNotFoundError(
                    "Generation requires the optional 'generation' extra: "
                    "pip install 'constraint-music[generation]'"
                )

        cp_model = cast(Any, _MissingCpModel())

