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
import pandas as pd  # noqa: F401  (type hints for the panel helpers)
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

    return dm_from_loss_diff(np.abs(e1) - np.abs(e2), h)


def dm_from_loss_diff(d: np.ndarray, h: int) -> tuple[float, float]:
    """HLN-corrected DM statistic and two-sided p-value for a loss-differential
    series d_t (positive mean = model 1 worse). `diebold_mariano` builds d from
    two forecasts' absolute errors; the panel test below builds it from a
    cross-section average per month."""
    d = np.asarray(d, dtype=float)
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


def panel_diebold_mariano(loss_diff: "pd.DataFrame", h: int) -> tuple[float, float, int]:
    """Panel DM with TIME-CLUSTERED variance. `loss_diff` is origin month x crop,
    d_{t,c} = |e1_{t,c}| - |e2_{t,c}| (NaN where a crop has no forecast that month).

    Stacking the 7 crops into one long series and running the plain DM treats
    n_months x 7 errors as independent, but crops' prices (and so their
    forecast errors) move together within a month and overlapping h-step
    forecasts are serially dependent -- the stacked n is far larger than the
    information, and the p-value far too small. Here each month is one cluster:
    the cross-section is averaged to D_t (equal weight per month), and the
    HLN-corrected DM with h-1 HAC lags is run on the T-month series D_t, so the
    effective sample size is the number of months. Returns (dm_stat, p, n_months)."""
    D = loss_diff.mean(axis=1, skipna=True).dropna().sort_index()
    stat, p = dm_from_loss_diff(D.to_numpy(dtype=float), h)
    return stat, p, int(len(D))


def block_bootstrap_pvalue(
    loss_diff: "pd.DataFrame", block_len: int, n_boot: int = 5000, seed: int = 0
) -> tuple[float, int]:
    """Two-sided moving-block-bootstrap p-value for H0: mean loss differential = 0,
    resampling whole MONTHS (cross-section averaged, so a month's crops always move
    together) in overlapping blocks of `block_len` consecutive months to keep the
    serial dependence of overlapping forecasts. The t-like statistic mean/se is
    recomputed on each centred resample; p = share of resamples at least as extreme
    as the observed statistic (with +1 smoothing). Returns (p, n_months). A
    robustness check on panel_diebold_mariano that does not lean on the HAC
    estimator or the t reference distribution."""
    D = loss_diff.mean(axis=1, skipna=True).dropna().sort_index().to_numpy(dtype=float)
    T = len(D)
    if T < 2 * block_len:
        raise ValueError(f"block_bootstrap_pvalue: {T} months is too few for block_len={block_len}")
    if D.std(ddof=1) == 0.0:  # identical forecasts (e.g. Naive vs Seasonal-Naive at h=12): no difference to test
        return 1.0, T
    obs = D.mean() / (D.std(ddof=1) / np.sqrt(T))
    centred = D - D.mean()
    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(T / block_len))
    starts_max = T - block_len
    extreme = 0
    for _ in range(n_boot):
        starts = rng.integers(0, starts_max + 1, size=n_blocks)
        sample = np.concatenate([centred[s : s + block_len] for s in starts])[:T]
        sd = sample.std(ddof=1)
        stat = sample.mean() / (sd / np.sqrt(T)) if sd > 0 else 0.0
        extreme += abs(stat) >= abs(obs)
    return float((extreme + 1) / (n_boot + 1)), T


def dm_verdict(dm_stat: float, p_value: float, label1: str, label2: str, horizon: int, alpha: float = 0.05) -> str:
    """Plain-language verdict string. dbar = mean(|e1|-|e2|) > 0 (positive
    dm_stat) means label2 has smaller average absolute error than label1."""
    if p_value >= alpha:
        return f"No significant difference between {label1} and {label2} at h={horizon} (p={p_value:.3f})."
    winner, loser = (label2, label1) if dm_stat > 0 else (label1, label2)
    return f"{winner} significantly more accurate than {loser} at h={horizon}, p={p_value:.3f}."
