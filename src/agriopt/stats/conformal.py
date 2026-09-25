"""Split conformal prediction intervals (Lei et al. 2018 / Vovk et al.):
fit on a training set, calibrate a single fixed quantile on a held-out
calibration set's absolute residuals, apply that quantile as a symmetric
band around any future prediction. Distribution-free finite-sample marginal
coverage guarantee (over calibration + test set randomness), PROVIDED
calibration and test residuals are exchangeable.

Finite-sample correction: the naive (1-alpha) quantile of n calibration
residuals under-covers a fresh test point; the standard fix uses the
ceil((1-alpha)(n+1))-th order statistic instead, equivalently the empirical
quantile at level (1-alpha)(1+1/n) with "higher" interpolation, clipped to 1
(see conformal_quantile below). This module implements that correction
explicitly rather than calling a plain np.quantile(residuals, 1-alpha).
"""
from __future__ import annotations

import numpy as np


def conformal_quantile(calib_abs_resid: np.ndarray, alpha: float) -> float:
    """Split-conformal calibrated half-width, at the (1-alpha) level, given
    n calibration ABSOLUTE residuals. Uses the finite-sample-corrected
    quantile level q_level = min(1, (1-alpha) * (1 + 1/n)), with "higher"
    interpolation (i.e. the ceil((1-alpha)(n+1))-th order statistic among
    the n residuals, which is the standard split-conformal prescription --
    NOT a plain (1-alpha) quantile, which would under-cover for finite n)."""
    resid = np.asarray(calib_abs_resid, dtype=float)
    n = len(resid)
    if n < 1:
        raise ValueError("conformal_quantile: need at least 1 calibration residual")
    q_level = min(1.0, (1.0 - alpha) * (1.0 + 1.0 / n))
    return float(np.quantile(resid, q_level, method="higher"))


def conformal_coverage(actual: np.ndarray, pred: np.ndarray, q: float) -> dict:
    """Empirical coverage + mean interval width of the fixed-width interval
    [pred - q, pred + q] against `actual`, both already on whatever scale
    `pred`/`q` are expressed in (caller is responsible for any log-scale ->
    original-scale transform BEFORE calling this, or for calling it directly
    in log-space -- see yield_model.predict_yield_interval for the
    log1p-space version, which transforms the already-verified log-space
    comparison to original units only for reporting)."""
    actual = np.asarray(actual, dtype=float)
    pred = np.asarray(pred, dtype=float)
    lower = pred - q
    upper = pred + q
    covered = (actual >= lower) & (actual <= upper)
    return {
        "coverage": float(np.mean(covered)),
        "mean_width": float(np.mean(upper - lower)),
        "n": int(len(actual)),
    }
