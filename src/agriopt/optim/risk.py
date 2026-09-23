"""Historical profit-risk model (Phase 5): a covariance matrix of relative
per-hectare revenue deviations across crops, used both as a portfolio-risk
objective (`portfolio_risk`) and for bootstrap profit-distribution estimates
(`bootstrap_profit`).

Crop_Year convention (ASSUMPTION -- see note below)
-----------------------------------------------------
`yield_clean.parquet`'s `year` column comes from the Kaggle dataset's raw
`Crop_Year` field, which is NOT documented beyond its dtype (see
reports/eda/eda_report.md). This module assumes the standard convention used
by India's data.gov.in APY-style crop datasets (which this Kaggle dataset is
derived from): `Crop_Year` is the year the growing season STARTED, i.e.:
  - Kharif crops (sown ~Jun-Jul): Crop_Year=t -> harvested/sold Oct-Dec of
    year t (same calendar year).
  - Rabi crops (sown ~Oct-Dec): Crop_Year=t -> harvested/sold Mar-May of
    year t+1 (the following calendar year).
This is FLAGGED AMBIGUOUS/UNVERIFIED -- there is no field in the raw dataset
that confirms it, and it could not be cross-checked against an independent
Maharashtra-specific harvest calendar in this pass. If reported wrong, the
main effect would be a one-year shift in the Rabi-crop revenue series (and
whatever correlations depend on it), not a wholesale invalidation of the
approach.

Revenue construction
---------------------
For crop `i`, year `t`:
  yield_t = saleable_yield_t (Maharashtra, MAIN_SEASON[i], via
            YIELD_TO_SALEABLE_QTL_PER_HA) -- same basis as build_crop_params.
  price_t = mean CEDA modal price over the crop's harvest-window months for
            year `t` (see convention above); sugarcane has no mandi series,
            so its price is held CONSTANT at the crop_reference.csv FRP for
            every year -- sugarcane's revenue variance comes from yield only.
  revenue_t = yield_t * price_t

Each crop's log(revenue) series is linearly detrended (OLS vs year); the
relative deviation d_it = exp(residual_it) - 1 is what feeds the covariance
matrix, so Sigma captures co-movement around each crop's own trend, not
raw revenue level trends common to yield/price growth over time.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from agriopt.config import CROPS, MAIN_SEASON, STATE, YIELD_CLEAN_PARQUET, YIELD_TO_SALEABLE_QTL_PER_HA
from agriopt.data.reference import load_reference
from agriopt.models.price_model import build_wide_price_table, load_price_frame
from agriopt.models.yield_model import CANON_TO_YIELD_NAME

HARVEST_WINDOW_MONTHS = {
    "Kharif": [(0, 10), (0, 11), (0, 12)],  # (year_offset, month) -- Oct-Dec of year t
    "Rabi": [(1, 3), (1, 4), (1, 5)],  # Mar-May of year t+1
}

MIN_EIGENVALUE_FLOOR = 1e-8


def _yield_series(crop: str, state: str = STATE) -> pd.Series:
    """Maharashtra saleable yield (qtl/ha) by year, for crop's MAIN_SEASON."""
    df = pd.read_parquet(YIELD_CLEAN_PARQUET)
    season = MAIN_SEASON[crop]
    name = CANON_TO_YIELD_NAME[crop]
    sub = df[(df["state"] == state) & (df["crop"] == name) & (df["season"] == season)]
    by_year = sub.groupby("year")["yield"].mean()
    return by_year.apply(YIELD_TO_SALEABLE_QTL_PER_HA[crop]).sort_index()


def _price_series(crop: str, wide: pd.DataFrame) -> pd.Series:
    """Mean modal price (Rs/qtl) over crop's harvest-window months, by
    crop-year t. Sugarcane: constant FRP for every year present in `wide`'s
    index span (handled by the caller, which never calls this for sugarcane)."""
    season = MAIN_SEASON[crop]
    if season not in HARVEST_WINDOW_MONTHS:
        raise ValueError(f"{crop}: MAIN_SEASON={season!r} has no harvest-window convention defined")
    if crop not in wide.columns:
        raise ValueError(f"{crop}: no price series in prices_monthly.parquet")

    windows = HARVEST_WINDOW_MONTHS[season]
    years = sorted(wide.index.year.unique())

    out = {}
    for t in years:
        vals = []
        for offset, month in windows:
            target_year = t + offset
            key = pd.Timestamp(year=target_year, month=month, day=1)
            if key in wide.index:
                v = wide.loc[key, crop]
                if pd.notna(v):
                    vals.append(v)
        if vals:
            out[t] = float(np.mean(vals))
    return pd.Series(out).sort_index()


def build_revenue_series(crop: str, wide: pd.DataFrame, state: str = STATE) -> pd.Series:
    """Rs/ha revenue by year (index = Crop_Year t), yield x harvest-window price."""
    yld = _yield_series(crop, state)
    if crop == "sugarcane":
        ref = load_reference()
        frp = float(ref[ref["crop"] == "sugarcane"].iloc[0]["admin_price_rs_per_qtl"])
        price = pd.Series(frp, index=yld.index)
    else:
        price = _price_series(crop, wide)
    common = yld.index.intersection(price.index)
    return (yld.loc[common] * price.loc[common]).sort_index()


def detrend_relative_deviation(revenue: pd.Series) -> tuple[pd.Series, dict]:
    """OLS-detrend log(revenue) vs year; relative deviation d_t = exp(resid_t) - 1.
    Returns (deviation_series, {"slope":..., "intercept":..., "n":...})."""
    revenue = revenue.dropna()
    if len(revenue) < 3:
        return pd.Series(dtype=float), {"slope": float("nan"), "intercept": float("nan"), "n": len(revenue)}

    years = revenue.index.to_numpy(dtype=float)
    log_rev = np.log(revenue.to_numpy(dtype=float))
    slope, intercept = np.polyfit(years, log_rev, deg=1)
    fitted = slope * years + intercept
    resid = log_rev - fitted
    deviation = pd.Series(np.expm1(resid), index=revenue.index)
    return deviation, {"slope": float(slope), "intercept": float(intercept), "n": len(revenue)}


def nearest_psd(sigma: np.ndarray, min_eig: float = MIN_EIGENVALUE_FLOOR) -> tuple[np.ndarray, float]:
    """Clip negative eigenvalues to `min_eig`, reconstruct, symmetrize.
    Returns (psd_matrix, min_eigenvalue_before_clipping)."""
    sigma = (sigma + sigma.T) / 2
    vals, vecs = np.linalg.eigh(sigma)
    min_eig_observed = float(vals.min())
    clipped = np.clip(vals, min_eig, None)
    psd = vecs @ np.diag(clipped) @ vecs.T
    psd = (psd + psd.T) / 2
    return psd, min_eig_observed


@dataclass
class RiskInputs:
    crops: list[str]
    deviation_matrix: pd.DataFrame  # years x crops, NaN where unavailable
    revenue_matrix: pd.DataFrame  # years x crops, raw Rs/ha revenue
    Sigma: np.ndarray  # crops x crops, PSD Rs^2
    min_eigenvalue_raw: float
    trend_info: dict = field(default_factory=dict)
    cv_table: pd.DataFrame = field(default_factory=pd.DataFrame)


def build_risk_inputs(params_df: pd.DataFrame, crops: list[str] = CROPS, state: str = STATE) -> RiskInputs:
    """Builds the deviation matrix, revenue covariance Sigma (Rs^2, PSD),
    and a per-crop CV summary table. `params_df` supplies R_i = current
    expected revenue/ha (yield_qtl_ha * price) used to scale the
    (unitless) relative-deviation covariance into Rs^2."""
    price_df = load_price_frame()
    wide = build_wide_price_table(price_df)

    revenue_cols, deviation_cols, trend_info, cv_rows = {}, {}, {}, []
    for crop in crops:
        revenue = build_revenue_series(crop, wide, state)
        deviation, info = detrend_relative_deviation(revenue)
        revenue_cols[crop] = revenue
        deviation_cols[crop] = deviation
        trend_info[crop] = info
        cv = float(revenue.std() / revenue.mean()) if len(revenue) > 1 and revenue.mean() != 0 else float("nan")
        cv_rows.append({"crop": crop, "n_years": len(revenue), "cv": cv, "trend_slope_log_per_year": info["slope"]})

    revenue_matrix = pd.DataFrame(revenue_cols)
    deviation_matrix = pd.DataFrame(deviation_cols).reindex(columns=crops)

    R = (params_df.loc[crops, "yield_qtl_ha"] * params_df.loc[crops, "price"]).to_numpy(dtype=float)
    dev_cov = deviation_matrix.cov().reindex(index=crops, columns=crops).to_numpy(dtype=float)
    dev_cov = np.nan_to_num(dev_cov, nan=0.0)
    Sigma_raw = dev_cov * np.outer(R, R)
    Sigma, min_eig_raw = nearest_psd(Sigma_raw)

    cv_table = pd.DataFrame(cv_rows).set_index("crop").reindex(crops)

    return RiskInputs(
        crops=crops,
        deviation_matrix=deviation_matrix,
        revenue_matrix=revenue_matrix,
        Sigma=Sigma,
        min_eigenvalue_raw=min_eig_raw,
        trend_info=trend_info,
        cv_table=cv_table,
    )


def portfolio_risk(x: np.ndarray, Sigma: np.ndarray) -> float:
    """sqrt(x' Sigma x), Rs. Clips tiny negative values from floating-point
    error before the sqrt."""
    x = np.asarray(x, dtype=float)
    var = float(x @ Sigma @ x)
    return float(np.sqrt(max(var, 0.0)))


def portfolio_risk_vectorized(X: np.ndarray, Sigma: np.ndarray) -> np.ndarray:
    """Vectorized portfolio_risk over a population X (n_pop x n_crops)."""
    var = np.einsum("ij,jk,ik->i", X, Sigma, X)
    return np.sqrt(np.clip(var, 0.0, None))


def bootstrap_profit(
    x: np.ndarray,
    risk_inputs: RiskInputs,
    R: np.ndarray,
    cost: np.ndarray,
    n: int = 2000,
    seed: int = 42,
    return_samples: bool = False,
) -> dict:
    """Resample YEARS (preserving cross-crop correlation) from the deviation
    matrix restricted to crops with x_i > 0 and years where ALL of those
    crops have data (pairwise-complete-within-the-allocation), then compute
    the resulting profit distribution.

    profit = sum_i x_i * (R_i * (1 + d_i) - cost_i)

    Returns {"mean", "P5", "P_loss", "CVaR5", "n_years_used"}. If fewer than
    3 overlapping years are available for the active crops, returns NaNs
    (documented, not raised) rather than a bootstrap on almost no data.
    """
    x = np.asarray(x, dtype=float)
    active = x > 1e-9
    if not active.any():
        empty = {"mean": 0.0, "P5": 0.0, "P_loss": 0.0, "CVaR5": 0.0, "n_years_used": 0}
        return (empty, np.zeros(n)) if return_samples else empty

    cols = [c for c, a in zip(risk_inputs.crops, active) if a]
    sub = risk_inputs.deviation_matrix[cols].dropna(how="any")

    if len(sub) < 3:
        nan_result = {"mean": float("nan"), "P5": float("nan"), "P_loss": float("nan"), "CVaR5": float("nan"), "n_years_used": len(sub)}
        return (nan_result, np.full(n, np.nan)) if return_samples else nan_result

    x_active = x[active]
    R_active = R[active]
    cost_active = cost[active]
    base = float(x_active @ (R_active - cost_active))

    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(sub), size=n)
    draws = sub.to_numpy(dtype=float)[idx]  # n x len(cols)
    profits = base + draws @ (x_active * R_active)

    p5 = float(np.percentile(profits, 5))
    cvar5 = float(profits[profits <= p5].mean()) if (profits <= p5).any() else p5

    result = {
        "mean": float(profits.mean()),
        "P5": p5,
        "P_loss": float((profits < 0).mean()),
        "CVaR5": cvar5,
        "n_years_used": len(sub),
    }
    return (result, profits) if return_samples else result
