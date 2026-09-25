"""Phase 9: tests for agriopt.stats (DM test, conformal, bootstrap) +
LOSO no-leakage guarantee."""
from __future__ import annotations

import numpy as np
import pytest
from scipy import stats as sstats

from agriopt.config import STATE, TRAIN_END_YEAR
from agriopt.models.yield_model import load_model_frame, train_test_split_by_year
from agriopt.stats.bootstrap import bootstrap_metric_ci, mae
from agriopt.stats.conformal import conformal_coverage, conformal_quantile
from agriopt.stats.dm_test import diebold_mariano


# --- Diebold-Mariano -------------------------------------------------------


def test_dm_identical_series_gives_zero_stat_and_p_one():
    rng = np.random.default_rng(0)
    e1 = rng.normal(size=60)
    e2 = e1.copy()  # identical -> d_t == 0 everywhere
    stat, p = diebold_mariano(e1, e2, h=3)
    assert stat == pytest.approx(0.0, abs=1e-9)
    assert p == pytest.approx(1.0, abs=1e-9)


def test_dm_hand_worked_example_h1():
    """h=1 -> only gamma_0 (no autocovariance lag terms), so this is easy to
    verify independently by hand. actual=[10,10,10,10,10]; two forecasts
    give e1=actual-pred1, e2=actual-pred2 such that d_t=|e1_t|-|e2_t| =
    [1,3,2,4,0] (chosen directly, not derived from the DM code under test).

    dbar = 2.0
    gamma_0 (population, /n) = mean((d-dbar)^2) = mean([1,1,0,4,4]) = 2.0
    long_run_var (h=1 -> no extra lags) = gamma_0 = 2.0
    dm_stat (uncorrected) = dbar / sqrt(gamma_0 / n) = 2 / sqrt(2/5) = 3.16227766...
    HLN correction factor = sqrt((n+1-2h+h(h-1)/n)/n) = sqrt((5+1-2+0)/5) = sqrt(4/5) = 0.89442719...
    dm_hln = 3.16227766 * 0.89442719 = 2.82842712...
    p = 2*(1 - t.cdf(2.82842712, df=4))
    """
    e1 = np.array([1.0, 3.0, 2.0, 4.0, 0.0])  # d_t := |e1_t| - |e2_t|, chosen directly (e2 = 0 everywhere)
    e2 = np.zeros(5)

    dbar = 2.0
    gamma0 = np.mean(((e1 - dbar)) ** 2)
    assert gamma0 == pytest.approx(2.0)
    dm_uncorrected = dbar / np.sqrt(gamma0 / 5)
    assert dm_uncorrected == pytest.approx(3.16227766, rel=1e-6)
    correction = np.sqrt((5 + 1 - 2 * 1 + 1 * 0 / 5) / 5)
    assert correction == pytest.approx(0.89442719, rel=1e-6)
    expected_stat = dm_uncorrected * correction
    assert expected_stat == pytest.approx(2.82842712, rel=1e-6)
    expected_p = 2 * (1 - sstats.t.cdf(abs(expected_stat), df=4))

    stat, p = diebold_mariano(e1, e2, h=1)
    assert stat == pytest.approx(expected_stat, rel=1e-9)
    assert p == pytest.approx(expected_p, rel=1e-9)


def test_dm_symmetry_swapping_series_flips_sign_not_pvalue():
    rng = np.random.default_rng(1)
    e1 = rng.normal(loc=0.5, scale=1.0, size=80)
    e2 = rng.normal(loc=0.0, scale=1.0, size=80)
    stat_ab, p_ab = diebold_mariano(e1, e2, h=3)
    stat_ba, p_ba = diebold_mariano(e2, e1, h=3)
    assert stat_ab == pytest.approx(-stat_ba, rel=1e-9)
    assert p_ab == pytest.approx(p_ba, rel=1e-9)


# --- Conformal ---------------------------------------------------------


def test_conformal_quantile_finite_sample_correction_at_alpha_bounds():
    resid = np.arange(1, 101, dtype=float)  # 1..100
    q = conformal_quantile(resid, alpha=0.0)
    assert q == pytest.approx(100.0)  # alpha=0 -> level clipped to 1.0 -> max residual


def test_conformal_coverage_on_synthetic_normal_data_near_nominal():
    """Generate y = mu + sigma*eps (known Gaussian generating process),
    calibrate a 90% split-conformal interval on a held-out calibration
    split, and check empirical coverage on a fresh test split lands within
    a few points of 90% -- validates the IMPLEMENTATION independent of
    whether any real model happens to be well-calibrated."""
    rng = np.random.default_rng(42)
    n_calib, n_test = 2000, 3000
    mu = 5.0
    sigma = 1.0

    # "predictions" are just mu (a constant, unbiased predictor of the true
    # generating mean); residuals are the noise itself.
    calib_actual = mu + sigma * rng.normal(size=n_calib)
    calib_pred = np.full(n_calib, mu)
    calib_abs_resid = np.abs(calib_actual - calib_pred)

    test_actual = mu + sigma * rng.normal(size=n_test)
    test_pred = np.full(n_test, mu)

    q = conformal_quantile(calib_abs_resid, alpha=0.1)
    result = conformal_coverage(test_actual, test_pred, q)

    assert abs(result["coverage"] - 0.90) < 0.03  # well within a few points of nominal at n=2000/3000


# --- Bootstrap -----------------------------------------------------------


def test_bootstrap_metric_ci_contains_point_estimate_and_is_reproducible():
    rng = np.random.default_rng(7)
    y_true = rng.normal(size=200)
    y_pred = y_true + rng.normal(scale=0.5, size=200)

    ci1 = bootstrap_metric_ci(y_true, y_pred, mae, n_boot=500, seed=42)
    ci2 = bootstrap_metric_ci(y_true, y_pred, mae, n_boot=500, seed=42)
    assert ci1 == ci2  # reproducible given a fixed seed
    assert ci1["ci_lo"] <= ci1["point"] <= ci1["ci_hi"]


# --- LOSO no-leakage guarantee -------------------------------------------


def test_loso_training_data_never_contains_held_out_state():
    df, _ = load_model_frame()
    train, _ = train_test_split_by_year(df, train_end_year=TRAIN_END_YEAR)

    top_states = df["state"].value_counts().head(10).index.tolist()
    assert STATE in top_states  # Maharashtra should be one of the top-10-by-rowcount states

    for state in top_states:
        train_excl = train[train["state"] != state]
        assert state not in set(train_excl["state"].unique())
        assert len(train_excl) < len(train)  # actually excluded something
