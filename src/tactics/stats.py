"""Small-sample statistics for win rates.

Why this exists: a player's "win rate after a cross-court drop in game 3 at 18+" might be 5
out of 6. That is not a tactic, it is noise. Every rate the reports show therefore carries

* a 95% Wilson score interval (better than the normal approximation when n is small or the
  rate is near 0 or 1),
* a shrunk estimate pulled toward the player's baseline rate, so that rare patterns cannot
  top a ranking just by being rare, and
* a reliability flag based on a minimum sample size.

Shrinkage is Beta-binomial: treat the baseline as `prior_strength` pseudo-observations.
With prior_strength = 20, a 5/6 pattern against a 50% baseline becomes (5 + 10) / (6 + 20)
= 58%, while 50/60 stays at 69%.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

Z95 = 1.959963984540054


def wilson_ci(k, n, z: float = Z95):
    """Wilson score interval for k successes in n trials. Works on scalars or arrays."""
    k = np.asarray(k, dtype=float)
    n = np.asarray(n, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        p = np.where(n > 0, k / n, np.nan)
        denom = 1 + z**2 / n
        centre = (p + z**2 / (2 * n)) / denom
        half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return centre - half, centre + half


def shrink(k, n, baseline: float, prior_strength: float):
    """Posterior-mean rate with a Beta prior centred on `baseline` worth `prior_strength` trials."""
    k = np.asarray(k, dtype=float)
    n = np.asarray(n, dtype=float)
    return (k + prior_strength * baseline) / (n + prior_strength)


@dataclass(frozen=True, slots=True)
class RateSettings:
    min_n: int = 30
    prior_strength: float = 20.0
    z: float = Z95


def rate_table(
    df: pd.DataFrame,
    by: list[str] | str,
    outcome: str,
    baseline: float,
    settings: RateSettings | None = None,
) -> pd.DataFrame:
    """Win-rate table for each group in `by`, relative to `baseline`.

    Columns: n, wins, rate, ci_lo, ci_hi, shrunk, lift (shrunk - baseline), reliable,
    ci_excludes_baseline. Sorted by |lift| among reliable rows first.
    """
    settings = settings or RateSettings()
    by = [by] if isinstance(by, str) else list(by)
    g = df.groupby(by, observed=True, dropna=True)[outcome]
    out = g.agg(n="size", wins="sum").reset_index()
    out["wins"] = out["wins"].astype(int)
    out["rate"] = out["wins"] / out["n"]
    out["ci_lo"], out["ci_hi"] = wilson_ci(out["wins"], out["n"], settings.z)
    out["shrunk"] = shrink(out["wins"], out["n"], baseline, settings.prior_strength)
    out["lift"] = out["shrunk"] - baseline
    out["reliable"] = out["n"] >= settings.min_n
    out["ci_excludes_baseline"] = (out["ci_lo"] > baseline) | (out["ci_hi"] < baseline)
    out["baseline"] = baseline
    return out.sort_values(
        ["reliable", "lift"],
        key=lambda s: s.abs() if s.name == "lift" else s,
        ascending=[False, False],
    ).reset_index(drop=True)


def two_proportion_z(k1, n1, k2, n2) -> float:
    """Two-sided p-value that two win rates differ (pooled z-test). Used to compare splits."""
    from math import erf, sqrt

    if min(n1, n2) == 0:
        return float("nan")
    p1, p2, p = k1 / n1, k2 / n2, (k1 + k2) / (n1 + n2)
    se = sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0
    z = (p1 - p2) / se
    return 2 * (1 - 0.5 * (1 + erf(abs(z) / sqrt(2))))


def fmt_rate(rate: float, lo: float, hi: float) -> str:
    return f"{rate:.0%} (95% CI {lo:.0%}-{hi:.0%})"
