"""Exact paired test and conservative paired risk-difference confidence bounds."""

from __future__ import annotations

import math


def binomial_cdf(k: int, n: int, p: float) -> float:
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k + 1))


def clopper_pearson(k: int, n: int, alpha: float) -> tuple[float, float]:
    if not 0 <= k <= n or n < 1 or not 0 < alpha < 1:
        raise ValueError("invalid binomial confidence input")

    def inverse(k: int, probability: float) -> float:
        lo, hi = 0.0, 1.0
        for _ in range(80):
            midpoint = (lo + hi) / 2
            if binomial_cdf(k, n, midpoint) > probability:
                lo = midpoint
            else:
                hi = midpoint
        return (lo + hi) / 2

    return (
        0.0 if k == 0 else inverse(k - 1, 1 - alpha / 2),
        1.0 if k == n else inverse(k, alpha / 2),
    )


def paired(left: list[bool], right: list[bool], alpha: float = 0.05 / 3) -> dict:
    if not left or len(left) != len(right) or any(type(x) is not bool for x in [*left, *right]):
        raise ValueError("paired binary observations required")
    n = len(left)
    wins = sum(a and not b for a, b in zip(left, right, strict=True))
    losses = sum(b and not a for a, b in zip(left, right, strict=True))
    both = sum(a and b for a, b in zip(left, right, strict=True))
    discordant = wins + losses
    p = (
        min(
            1.0,
            2 * sum(math.comb(discordant, i) for i in range(min(wins, losses) + 1)) / 2**discordant,
        )
        if discordant
        else 1.0
    )
    # p10 and p01 are marginal binomial counts from the same paired table.
    # Bonferroni bounds require no independence between them.
    win_lo, win_hi = clopper_pearson(wins, n, alpha / 2)
    loss_lo, loss_hi = clopper_pearson(losses, n, alpha / 2)
    lower, upper = win_lo - loss_hi, win_hi - loss_lo
    return {
        "n": n,
        "both_pass": both,
        "left_only": wins,
        "right_only": losses,
        "neither_pass": n - wins - losses - both,
        "difference": (wins - losses) / n,
        "confidence": 1 - alpha,
        "conservative_paired_ci": [lower, upper],
        "exact_mcnemar_two_sided_p": p,
        "bonferroni_p": min(1.0, 3 * p),
        "practical_margin": 0.10,
        "superiority_gate": lower > 0.10 and p < alpha,
    }
