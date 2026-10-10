"""Independent finite voicing/path formulation; used to certify input feasibility."""

from __future__ import annotations

from itertools import combinations, product

from .contract import KEYS, RANGES, SCALE, VOICES


def candidates(request: dict, index: int) -> list[tuple[int, ...]]:
    root = request["degrees"][index]
    offsets = range(0, 8 if request["sevenths"][index] else 6, 2)
    pcs = {(KEYS[request["key"]][0] + SCALE[(root + x) % 7]) % 12 for x in offsets}
    domains = [[p for p in range(lo, hi + 1) if p % 12 in pcs] for lo, hi in RANGES[:3]]
    given = request["given_soprano"][index]
    bass = request["bass"][index]
    return [
        (*upper, bass)
        for upper in product(*domains)
        if upper[0] > upper[1] > upper[2] > bass
        and upper[0] - upper[1] <= 12
        and upper[1] - upper[2] <= 12
        and (given is None or upper[0] == given)
        and {p % 12 for p in (*upper, bass)} == pcs
    ]


def edge(request: dict, index: int, left: tuple, right: tuple) -> bool:
    movement = [b - a for a, b in zip(left, right, strict=True)]
    for a, b in combinations(range(4), 2):
        if (
            (left[a] - left[b]) % 12 in (0, 7)
            and (left[a] - left[b] - right[a] + right[b]) % 12 == 0
            and movement[a] * movement[b] > 0
        ):
            return False
    tonic = KEYS[request["key"]][0]
    if request["degrees"][index : index + 2] == [4, 0] and any(
        p % 12 == (tonic + 11) % 12 and m != 1 for p, m in zip(left, movement, strict=True)
    ):
        return False
    return not (
        request["sevenths"][index]
        and any(
            p % 12 == (tonic + 5) % 12 and m not in (-2, -1)
            for p, m in zip(left, movement, strict=True)
        )
    )


def witness(request: dict) -> list[tuple[int, ...]] | None:
    paths = {row: [row] for row in candidates(request, 0)}
    for index in range(1, len(request["degrees"])):
        following = {}
        for row in candidates(request, index):
            for previous, path in paths.items():
                if edge(request, index - 1, previous, row):
                    following[row] = [*path, row]
                    break
        paths = following
        if not paths:
            return None
    return next(iter(paths.values()), None)


def accepts(request: dict, events: list) -> bool:
    expected_times = {(v, str(i), "1") for v in VOICES for i in range(len(request["degrees"]))}
    if len(events) != len(expected_times) or {(v, a, d) for v, _, a, d in events} != expected_times:
        return False
    rows = [
        tuple(next(p for v, p, a, _ in events if v == voice and a == str(i)) for voice in VOICES)
        for i in range(len(request["degrees"]))
    ]
    return all(row in candidates(request, i) for i, row in enumerate(rows)) and all(
        edge(request, i, rows[i], rows[i + 1]) for i in range(len(rows) - 1)
    )
