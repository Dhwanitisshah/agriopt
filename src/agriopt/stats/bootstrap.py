"""Generic paired bootstrap CI for a scalar metric computed from
(y_true, y_pred) row-aligned arrays -- used here for yield-model MAE CIs,
but not specific to MAE."""
from __future__ import annotations

from typing import Callable

import numpy as np


def bootstrap_metric_ci(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    metric_fn: Callable[[np.ndarray, np.ndarray], float],
    n_boot: int = 2000,
    seed: int = 42,
    alpha: float = 0.05,
) -> dict:
    """Resample TEST ROWS with replacement (same resampled indices applied
    to both y_true and y_pred, preserving pairing), recompute metric_fn each
    resample, and report the point estimate + percentile 95% CI.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    n = len(y_true)
    if n != len(y_pred):
        raise ValueError("bootstrap_metric_ci: y_true/y_pred length mismatch")

    point = float(metric_fn(y_true, y_pred))
    rng = np.random.default_rng(seed)
    boot_vals = np.empty(n_boot, dtype=float)
    for b in range(n_boot):
        idx = rng.integers(0, n, size=n)
        boot_vals[b] = metric_fn(y_true[idx], y_pred[idx])

    lo = float(np.quantile(boot_vals, alpha / 2))
    hi = float(np.quantile(boot_vals, 1 - alpha / 2))
    return {
        "point": point,
        "ci_lo": lo,
        "ci_hi": hi,
        "n_boot": n_boot,
        "boot_mean": float(np.mean(boot_vals)),
        "boot_std": float(np.std(boot_vals)),
    }


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))
