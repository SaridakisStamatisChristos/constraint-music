"""Hand-constructed positive controls and exact-time equivalence controls."""

from __future__ import annotations

from typing import Any

from .contract import VOICES, content_hash, make_request
from .faults import scaled
from .render import render


def controls() -> list[tuple[str, dict[str, Any], dict[str, Any], bytes]]:
    result = []
    chords = [[79, 72, 64, 60], [81, 72, 65, 53], [79, 71, 62, 55], [79, 72, 64, 60]]
    for key, shift in (("C", 0), ("G", 7)):
        for indexes in ([0, 2, 3], [0, 1, 2, 3]):
            identity = f"hand.{key}.{len(indexes)}"
            degrees = [0, 4, 0] if len(indexes) == 3 else [0, 3, 4, 0]
            request = make_request(identity, key, degrees)
            events = sorted(
                [
                    [v, chords[i][part] + shift, str(block * 4), "4"]
                    for block, i in enumerate(indexes)
                    for part, v in enumerate(VOICES)
                ]
            )
            artifact = {"request": request, "events": events, "events_sha256": content_hash(events)}
            data = render(request, events)
            result.extend(
                [
                    (identity, request, artifact, data),
                    (identity + ".ppqn", request, artifact, scaled(data)),
                ]
            )
    return result
