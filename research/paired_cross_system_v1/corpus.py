"""Declare request families and sample sizes without consulting generated outcomes."""

from __future__ import annotations

import copy
from pathlib import Path

from .adapter import save
from .contract import make_request

ROOT = Path(__file__).resolve().parent


def corpus() -> list[dict[str, object]]:
    rows = []
    for key in ("C", "G"):
        for family, degrees in (("plagal-preparation", [0, 3, 4, 0]), ("short-cadence", [0, 4, 0])):
            rows.append(
                {
                    "phase": "development",
                    "family": family,
                    "eligible": True,
                    "request": make_request(f"dev.{family}.{key}", key, degrees),
                }
            )
    for index, key in enumerate(("D", "A", "E", "F", "Bb", "Eb")):
        for family, degrees in (
            ("supertonic-preparation", [0, 1, 4, 0]),
            ("extended-submediant", [0, 5, 3, 1, 4, 0]),
        ):
            rows.append(
                {
                    "phase": "heldout",
                    "family": family,
                    "eligible": True,
                    "request": make_request(
                        f"heldout.{family}.{key}", key, degrees, (90, 108, 132)[index % 3]
                    ),
                }
            )
    for property_name, value in (
        ("mode", "minor"),
        ("rests", True),
        ("ties", True),
        ("given_voice", [60, 62, 67, 60]),
    ):
        request = copy.deepcopy(
            make_request(f"heldout.unsupported.{property_name}", "C", [0, 1, 4, 0])
        )
        request[property_name] = value
        rows.append(
            {
                "phase": "heldout",
                "family": "unsupported-" + property_name,
                "eligible": False,
                "request": request,
            }
        )
    return rows


if __name__ == "__main__":
    path = ROOT / "corpus.json"
    if path.exists():
        raise ValueError("corpus already declared")
    save(path, corpus())
