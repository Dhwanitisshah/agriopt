"""Diebold-Mariano (1995) test with the Harvey-Leybourne-Newbold (1997)
small-sample correction, for absolute-error loss.

Loss differential: d_t = |e1_t| - |e2_t|, where e1/e2 are two forecasts'
errors (actual - pred) for the SAME target observations, paired by t. Under
H0 (equal forecast accuracy), E[d_t] = 0.

The long-run variance of dbar uses a Newey-West-style HAC estimator with
`h-1` lags: a rational h-step-ahead forecast's errors are only guaranteed to
be autocorrelated up to lag h-1 (an (h)-step-ahead error at time t and t+h
can share information revealed between t and t+h, but errors more than h-1
apart in a well-specified h-step forecast should not be systematically
related) -- this is the standard DM prescription, not an arbitrary choice.

HLN small-sample correction: the plain DM statistic is asymptotically
N(0,1), but is known to over-reject in small samples; HLN scale the
statistic by sqrt((n + 1 - 2h + h(h-1)/n) / n) and compare it to a
Student-t(n-1) distribution instead of the standard normal.

This is a from-scratch, auditable implementation (no external DM-test
package); scipy.stats.t is used only for the reference CDF.
"""
from __future__ import annotations

import numpy as np
from scipy import stats


def _autocovariance(d: np.ndarray, dbar: float, lag: int) -> float:
    """Population (divide-by-n) autocovariance of `d` at `lag`, matching the
    standard DM/Newey-West convention (not the divide-by-(n-lag) sample
    estimator)."""
    n = len(d)
    if lag == 0:
        return float(np.sum((d - dbar) ** 2) / n)
    return float(np.sum((d[lag:] - dbar) * (d[:-lag] - dbar)) / n)


def diebold_mariano(e1: np.ndarray, e2: np.ndarray, h: int) -> tuple[float, float]:
    """DM test (HLN correction) that model 2 is more accurate than model 1
    is one-sided; this returns the standard TWO-SIDED test of "equal
    accuracy" (d_t = |e1_t| - |e2_t|; positive dbar means model 1's errors
    are larger on average, i.e. model 2 is more accurate).

    Returns (dm_statistic, p_value). If the loss-differential series has
    zero variance (e.g. e1 == e2 everywhere), returns (0.0, 1.0) -- no
    detectable difference, by construction, rather than raising or
    returning NaN/inf.
    """
    e1 = np.asarray(e1, dtype=float)
    e2 = np.asarray(e2, dtype=float)
    if e1.shape != e2.shape:
        raise ValueError(f"diebold_mariano: e1/e2 shape mismatch {e1.shape} vs {e2.shape}")
    if h < 1:
        raise ValueError(f"diebold_mariano: h must be >= 1, got {h}")

    d = np.abs(e1) - np.abs(e2)
    n = len(d)
    if n < 2:
        raise ValueError(f"diebold_mariano: need at least 2 paired observations, got {n}")
    dbar = float(np.mean(d))

    max_lag = min(h - 1, n - 1)
    gamma0 = _autocovariance(d, dbar, 0)
    long_run_var = gamma0 + 2.0 * sum(_autocovariance(d, dbar, k) for k in range(1, max_lag + 1))

    if long_run_var <= 0.0:
        # Degenerate loss differential (constant, e.g. e1 == e2): no
        # detectable difference -- report "no difference" rather than a
        # division-by-zero / negative-variance artifact.
        return 0.0, 1.0

    dm_stat = dbar / np.sqrt(long_run_var / n)

    correction = np.sqrt(max((n + 1 - 2 * h + h * (h - 1) / n) / n, 0.0))
    dm_hln = dm_stat * correction

    p_value = float(2.0 * (1.0 - stats.t.cdf(abs(dm_hln), df=n - 1)))
    return float(dm_hln), p_value


def dm_verdict(dm_stat: float, p_value: float, label1: str, label2: str, horizon: int, alpha: float = 0.05) -> str:
    """Plain-language verdict string. dbar = mean(|e1|-|e2|) > 0 (positive
    dm_stat) means label2 has smaller average absolute error than label1."""
    if p_value >= alpha:
        return f"No significant difference between {label1} and {label2} at h={horizon} (p={p_value:.3f})."
    winner, loser = (label2, label1) if dm_stat > 0 else (label1, label2)
    return f"{winner} significantly more accurate than {loser} at h={horizon}, p={p_value:.3f}."
