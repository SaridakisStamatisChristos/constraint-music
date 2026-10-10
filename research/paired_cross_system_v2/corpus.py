"""IID draws from a declared finite grammar, conditioned on reference feasibility."""

from __future__ import annotations

import random

from .contract import KEYS, make_request
from .reference import witness

TEMPLATES = (
    (0, 5, 1, 4, 0, 3, 4, 0),
    (0, 3, 0, 1, 4, 0, 4, 0),
    (0, 1, 4, 0, 5, 3, 4, 0),
    (0, 2, 5, 1, 4, 0, 4, 0),
)


def sample(phase: str) -> dict:
    if phase not in ("development", "heldout"):
        raise ValueError("phase")
    rng = random.Random(20261009 if phase == "development" else 20261011)
    count = 8 if phase == "development" else 128
    rows, discarded = [], 0
    while len(rows) < count:
        template = rng.randrange(len(TEMPLATES))
        degrees = list(TEMPLATES[template])
        if rng.getrandbits(1):
            degrees = [0, 3, 4, 0, *degrees]
        n = len(degrees)
        key = rng.choice(list(KEYS))
        inversions = [rng.randrange(3) for _ in degrees]
        inversions[0] = inversions[-1] = 0
        sevenths = [
            bool(d == 4 and degrees[i : i + 2] == [4, 0] and rng.getrandbits(1))
            for i, d in enumerate(degrees)
        ]
        request = make_request(
            f"{phase}.{len(rows):03d}",
            key,
            degrees,
            inversions,
            sevenths,
            [None] * n,
            rng.choice((90, 108, 120, 132)),
        )
        path = witness(request)
        if path is None:
            discarded += 1
            continue
        anchor_count = rng.randrange(3)
        for i in rng.sample(range(n), anchor_count):
            request["given_soprano"][i] = path[i][0]
        rows.append({"template": template, "request": request, "witness": path})
    # Unsupported requests have distinct outcomes and are outside the primary denominator.
    unsupported = []
    for label, field, value in (
        ("minor", "mode", "minor"),
        ("rests", "rests", True),
        ("ties", "ties", True),
        ("third-inversion", "inversions", None),
    ):
        request = dict(rows[0]["request"])
        request["request_id"] = f"{phase}.unsupported.{label}"
        request[field] = [3] * len(request["degrees"]) if value is None else value
        unsupported.append({"request": request})
    return {
        "sampling_seed": 20261009 if phase == "development" else 20261011,
        "discarded_reference_infeasible": discarded,
        "primary": rows,
        "unsupported": unsupported,
    }
