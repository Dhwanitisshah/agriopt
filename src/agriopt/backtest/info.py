"""Phase 7: leak-free information sets for the decision backtest.

Every function here answers "what would AgriOpt have known before sowing in
year t?" -- see docs/backtest.md for the full writeup. The core discipline:
nothing computed for decision year t is allowed to read yield/price data
from year >= t (yield model training, rainfall medians, risk deviations) or
price data published after the crop's sowing decision month (naive price
forecast). `realized_*` functions are the only ones allowed to look at
year t itself -- they represent the OUTCOME, evaluated only after harvest.

ASSUMPTION (RF hyperparameters): models/yield_best.json does not persist the
RandomForest hyperparameters actually used (only metrics/feature lists), so
there is nothing "saved" to reuse for the 5 refits this phase needs. Instead
each decision year retunes RF via the exact same fit/valid protocol Phase 1
used (`agriopt.models.yield_model.tune_rf`, `tuning_split`-style 3-year
validation window immediately before the tuning fit cutoff), just slid to
end at t-1 instead of 2015. For t=2016 this reproduces Phase 1's original
window exactly (fit <2013, validate 2013-2015).
"""
from __future__ import annotations

import json

import joblib
import numpy as np
import pandas as pd

from agriopt.config import (
    BACKTEST_MODELS_DIR,
    CROPS,
    MAIN_SEASON,
    MSP_HISTORY_CSV,
    RANDOM_SEED,
    STATE,
    YIELD_CLEAN_PARQUET,
    YIELD_TO_SALEABLE_QTL_PER_HA,
)
from agriopt.data.rainfall import net_irrigation_mm
from agriopt.data.reference import fert_total_kg_ha, load_reference, water_mm
from agriopt.models.price_model import build_wide_price_table, load_price_frame
from agriopt.models.yield_model import (
    CANON_TO_YIELD_NAME,
    CORE_NUM_COLS,
    SklearnYieldModel,
    _force_single_threaded_predict,
    load_model_frame,
    tune_rf,
)
from agriopt.optim.baselines import historical_area_share, mix_from_shares
from agriopt.optim.params import MM_TO_M3_PER_HA, SUGARCANE_REVENUE_CV, economic_row, seasons_occupied
from agriopt.optim.risk import HARVEST_WINDOW_MONTHS, detrend_relative_deviation, nearest_psd
from sklearn.ensemble import RandomForestRegressor

PRICE_STD_LOOKBACK_MONTHS = 36

# ASSUMPTION -- ONE planning date. The optimizer chooses a single joint
# kharif+rabi allocation (long-duration crops such as cotton, tur and
# sugarcane commit land in both seasons), so every price it sees must be known
# on the day the kharif crops are sown: 1 MAY of year t (PLAN_MONTH). Rabi
# crops' prices are therefore the naive carry-forward of the last mandi price
# at or before May -- NOT the October price, which a May decision cannot see.
# Sugarcane has no mandi series -- its "price forecast" is simply the FRP for
# year t from msp_history.csv, which is legitimately known ahead of sowing
# (FRP is announced by the government before the season, not discovered at
# harvest).
#
# info_set="season" is the earlier, look-ahead convention (rabi prices read in
# OCTOBER while the plan is made in May). It is kept only to quantify how much
# that look-ahead was worth; never use it for a headline number.
PLAN_MONTH = 5
DECISION_MONTH = {"Kharif": 5, "Rabi": 10}  # legacy, info_set="season" only
INFO_SETS = ("may", "season")


def _plan_month(crop: str, info_set: str) -> int:
    if info_set not in INFO_SETS:
        raise ValueError(f"info_set must be one of {INFO_SETS}, got {info_set!r}")
    return PLAN_MONTH if info_set == "may" else DECISION_MONTH[MAIN_SEASON[crop]]


# --- 0) MSP/cost history --------------------------------------------------


def load_msp_history(path=MSP_HISTORY_CSV) -> pd.DataFrame:
    df = pd.read_csv(path)
    return df.set_index(["crop", "year"])


def cost_for_year(crop: str, year: int, msp_hist: pd.DataFrame | None = None, ref: pd.DataFrame | None = None) -> tuple[float, str]:
    """Historical cost Rs/qtl for `crop` at crop-year `year`.

    1) if msp_history.csv has a published cost_a2fl_rs_per_qtl for this
       crop-year, use it directly ("cacp_a2fl").
    2) else ASSUMPTION: cost_t = cost_2025 * (MSP_t / MSP_2025), using
       crop_reference.csv's 2025-26 cost_rs_per_qtl as the anchor and MSP as
       a cost-plus index (CACP sets MSP as a markup over cost, so MSP growth
       is a reasonable proxy for cost growth when no direct cost figure is
       published for year t) ("msp_index").
    Raises if msp_rs_per_qtl itself is missing for (crop, year) -- see
    docs/backtest.md for which crop-years fall through this gap.
    """
    msp_hist = msp_hist if msp_hist is not None else load_msp_history()
    ref = ref if ref is not None else load_reference()

    row = msp_hist.loc[(crop, year)]
    cost_a2fl = row["cost_a2fl_rs_per_qtl"]
    if pd.notna(cost_a2fl):
        return float(cost_a2fl), "cacp_a2fl"

    msp_t = row["msp_rs_per_qtl"]
    if pd.isna(msp_t):
        raise ValueError(f"cost_for_year: no msp_rs_per_qtl for ({crop}, {year}) in msp_history.csv -- cannot index cost.")

    ref_row = ref[ref["crop"] == crop].iloc[0]
    cost_2025 = float(ref_row["cost_rs_per_qtl"])
    msp_2025 = float(msp_hist.loc[(crop, 2025), "msp_rs_per_qtl"])
    cost_t = cost_2025 * (float(msp_t) / msp_2025)
    return float(cost_t), "msp_index"


# --- 1) Yield forecast: refit RF on year <= t-1 ---------------------------


def _tune_fit_valid_windows(train_df: pd.DataFrame, t: int):
    """Mirrors agriopt.models.yield_model.tuning_split, slid to end at t-1:
    fit on year < t-3, validate on [t-3, t-1]. For t=2016 this is exactly
    Phase 1's original window (fit <2013, validate 2013-2015)."""
    fit = train_df[train_df["year"] < t - 3].reset_index(drop=True)
    valid = train_df[(train_df["year"] >= t - 3) & (train_df["year"] <= t - 1)].reset_index(drop=True)
    return fit, valid


def refit_yield_model_for_year(t: int, cache_dir=BACKTEST_MODELS_DIR):
    """Refit RandomForest on year <= t-1 (no year >= t rows at all -- the
    core no-leakage guarantee this phase's tests assert on). Returns
    (model, num_cols, meta) where meta["train_max_year"] == t-1 and
    meta["rf_params"] is what tune_rf picked on the t-3..t-1 validation
    window. Caches to `cache_dir`/yield_t{t}.joblib (+.json) so the 5 refits
    (one per decision year) aren't repeated across script/test runs."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    model_path = cache_dir / f"yield_t{t}.joblib"
    meta_path = cache_dir / f"yield_t{t}.json"
    num_cols = CORE_NUM_COLS  # fert/pest excluded, matches models/yield_best.json (fert_pest_included=false)

    if model_path.exists() and meta_path.exists():
        model = joblib.load(model_path)
        # Phase 8 reproducibility fix (see agriopt.models.yield_model._force_single_threaded_predict):
        # cached models here were saved with RandomForestRegressor(n_jobs=-1) baked in, which makes
        # predict() non-reproducible across process runs -- force n_jobs=1 on load, same as load_model().
        _force_single_threaded_predict(model)
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        return model, num_cols, meta

    df, _ = load_model_frame()
    train_df = df[df["year"] <= t - 1].reset_index(drop=True)
    if train_df.empty or int(train_df["year"].max()) != t - 1:
        raise ValueError(f"refit_yield_model_for_year: expected data up to {t - 1}, got max year {train_df['year'].max() if len(train_df) else None}")

    fit_df, valid_df = _tune_fit_valid_windows(train_df, t)
    rf_params = tune_rf(fit_df, valid_df, num_cols)

    model = SklearnYieldModel("RandomForest", RandomForestRegressor(random_state=RANDOM_SEED, n_jobs=-1, **rf_params), num_cols)
    model.fit(train_df)
    # Phase 8 reproducibility fix: force single-threaded predict before caching (see
    # agriopt.models.yield_model._force_single_threaded_predict for why n_jobs=-1 predict() is
    # not bit-reproducible across process runs).
    _force_single_threaded_predict(model)

    meta = {"train_max_year": int(train_df["year"].max()), "rf_params": rf_params, "decision_year": t}
    joblib.dump(model, model_path, compress=3)
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return model, num_cols, meta


def rainfall_median_before(df: pd.DataFrame, t: int, state: str = STATE, n_years: int = 5) -> float:
    """Maharashtra median rainfall over the 5 years STRICTLY BEFORE t (years
    <= t-1) -- no peeking at year t's own rainfall."""
    mh = df[(df["state"] == state) & (df["year"] <= t - 1)][["year", "rainfall_mm"]].drop_duplicates()
    recent = mh.sort_values("year", ascending=False).head(n_years)
    return float(recent["rainfall_mm"].median())


def yield_forecast_for_year(t: int, model, num_cols: list[str], train_max_year: int, crops: list[str] = CROPS, state: str = STATE) -> dict:
    """Saleable qtl/ha forecast per crop for decision year t, using the
    model refit on year <= t-1 and a rainfall input that only looks at years
    <= t-1 too."""
    df, _ = load_model_frame()
    df = df[df["year"] <= train_max_year]
    rainfall = rainfall_median_before(df, t, state=state)

    out = {}
    for crop in crops:
        season = MAIN_SEASON[crop]
        # model is a SklearnYieldModel wrapper (predict() -> original scale) --
        # call it directly rather than agriopt.models.yield_model.predict_yield,
        # which only knows how to load the SAVED yield_best model from disk.
        row = pd.DataFrame([{"crop": CANON_TO_YIELD_NAME[crop], "season": season, "state": state, "year": t, "rainfall_mm": rainfall}])
        dataset_yield = float(model.predict(row)[0])
        saleable = YIELD_TO_SALEABLE_QTL_PER_HA[crop](dataset_yield)
        out[crop] = {"value": saleable, "dataset_yield": dataset_yield, "rainfall_mm": rainfall, "season": season}
    return out


# --- 2) Price forecast: naive at the decision month -----------------------


def price_forecast_for_year(t: int, crops: list[str], msp_hist: pd.DataFrame, info_set: str = "may") -> dict:
    """Naive price forecast Rs/qtl per crop: last observed monthly modal
    price at (or before, ffilled) the planning month of year t (1 May for
    every crop by default -- see PLAN_MONTH).
    Sugarcane uses FRP_t from msp_history.csv (announced ahead of the
    season, so legitimately known at decision time, not a forecast)."""
    price_df = load_price_frame()
    wide = build_wide_price_table(price_df)

    out = {}
    for crop in crops:
        if crop == "sugarcane":
            frp = msp_hist.loc[(crop, t), "msp_rs_per_qtl"]
            if pd.isna(frp):
                raise ValueError(f"price_forecast_for_year: no sugarcane FRP for year {t}")
            out[crop] = {"value": float(frp), "method": "FRP", "origin_month": None}
            continue

        month = _plan_month(crop, info_set)
        origin = pd.Timestamp(year=t, month=month, day=1)
        # ffilled lookup at-or-before origin, matching build_wide_price_table's
        # own ffill convention -- never look past `origin`.
        available = wide.index[wide.index <= origin]
        if len(available) == 0 or crop not in wide.columns:
            raise ValueError(f"price_forecast_for_year: no price data at/before {origin.date()} for {crop}")
        lookup_month = available.max()
        value = wide.loc[lookup_month, crop]
        if pd.isna(value):
            raise ValueError(f"price_forecast_for_year: NaN price for {crop} at {lookup_month.date()}")
        out[crop] = {"value": float(value), "method": "naive", "origin_month": str(origin.date()), "lookup_month": str(lookup_month.date())}
    return out


def _price_std_leakfree(crop: str, origin: pd.Timestamp, wide: pd.DataFrame, lookback_months: int = PRICE_STD_LOOKBACK_MONTHS) -> float:
    if crop not in wide.columns:
        return 0.0
    sub = wide.loc[wide.index <= origin, crop].dropna().tail(lookback_months)
    return float(sub.std()) if len(sub) > 1 else 0.0


# --- 3) Assemble a params_df (forecast OR realized) ------------------------


def _base_params_row(
    crop: str,
    yield_qtl_ha: float,
    price: float,
    cost_rs_per_qtl: float,
    water_ref: pd.DataFrame,
    water_basis: str = "total_need",
    rainfall_scenario: str = "normal",
    region: str = "maharashtra",
) -> dict:
    """Backtest rows go through the SAME economic_row() as the live
    pipeline. `cost_rs_per_qtl` is what cost_for_year() returns (Rs/quintal);
    it used to be passed straight in as a per-hectare cost, so every backtest
    "profit" was really revenue minus ~Rs 1-5k. economic_row() multiplies by
    yield, so that can't happen again."""
    if water_basis == "net_irrigation":
        water_mm_val = net_irrigation_mm(crop, rainfall_scenario, water_ref, region)
    else:
        water_mm_val = water_mm(crop, water_ref)
    row = economic_row(
        crop,
        yield_per_cycle_qtl_ha=yield_qtl_ha,
        gross_price=price,
        cost_rs_per_qtl=cost_rs_per_qtl,
        water_m3_per_cycle=water_mm_val * MM_TO_M3_PER_HA,
        fert_kg_per_cycle=fert_total_kg_ha(crop, water_ref),
        ref=water_ref,
    )
    row["seasons_occupied"] = seasons_occupied(crop)
    return row


def build_forecast_params_df(
    t: int,
    crops: list[str] = CROPS,
    state: str = STATE,
    water_basis: str = "total_need",
    rainfall_scenario: str = "normal",
    region: str = "maharashtra",
    info_set: str = "may",
) -> tuple[pd.DataFrame, dict]:
    """The full leak-free PLANNING info set for decision year t: refits the
    yield model on year<=t-1, forecasts price naively at the planning month
    (1 May for all crops; info_set="season" is the legacy look-ahead variant),
    and derives cost from msp_history.csv. Returns (params_df, info) where
    `info` carries the leakage-relevant internals (train_max_year, the price
    origin months used, rf_params) for tests to assert on directly."""
    ref = load_reference()
    msp_hist = load_msp_history()

    model, num_cols, meta = refit_yield_model_for_year(t)
    yields = yield_forecast_for_year(t, model, num_cols, meta["train_max_year"], crops=crops, state=state)
    prices = price_forecast_for_year(t, crops, msp_hist, info_set=info_set)

    price_df = load_price_frame()
    wide = build_wide_price_table(price_df)

    rows = []
    for crop in crops:
        yield_qtl_ha = yields[crop]["value"]
        price = prices[crop]["value"]
        cost_qtl, cost_method = cost_for_year(crop, t, msp_hist, ref)
        row = _base_params_row(crop, yield_qtl_ha, price, cost_qtl, ref, water_basis, rainfall_scenario, region)
        origin_month = prices[crop]["origin_month"]
        origin = pd.Timestamp(origin_month) if origin_month else pd.Timestamp(year=t, month=PLAN_MONTH, day=1)
        if crop == "sugarcane":
            row["profit_std_ha"] = row["yield_qtl_ha"] * row["price"] * SUGARCANE_REVENUE_CV
        else:
            row["profit_std_ha"] = row["yield_qtl_ha"] * _price_std_leakfree(crop, origin, wide)
        row["cost_method"] = cost_method
        rows.append(row)

    params_df = pd.DataFrame(rows).set_index("crop")
    info = {
        "info_set": info_set,
        "train_max_year": meta["train_max_year"],
        "rf_params": meta["rf_params"],
        "price_origin_months": {c: prices[c]["origin_month"] for c in crops},
        "price_methods": {c: prices[c]["method"] for c in crops},
    }
    return params_df, info


def realized_yield_for_year(crop: str, t: int, state: str = STATE) -> float | None:
    df = pd.read_parquet(YIELD_CLEAN_PARQUET)
    season = MAIN_SEASON[crop]
    name = CANON_TO_YIELD_NAME[crop]
    sub = df[(df["state"] == state) & (df["crop"] == name) & (df["season"] == season) & (df["year"] == t)]
    if sub.empty:
        return None
    dataset_yield = float(sub["yield"].mean())
    return YIELD_TO_SALEABLE_QTL_PER_HA[crop](dataset_yield)


def realized_price_for_year(crop: str, t: int, msp_hist: pd.DataFrame, wide: pd.DataFrame) -> float | None:
    if crop == "sugarcane":
        frp = msp_hist.loc[(crop, t), "msp_rs_per_qtl"]
        return float(frp) if pd.notna(frp) else None
    season = MAIN_SEASON[crop]
    windows = HARVEST_WINDOW_MONTHS[season]
    vals = []
    for offset, month in windows:
        key = pd.Timestamp(year=t + offset, month=month, day=1)
        if key in wide.index and crop in wide.columns:
            v = wide.loc[key, crop]
            if pd.notna(v):
                vals.append(v)
    return float(np.mean(vals)) if vals else None


def build_realized_params_df(
    t: int,
    crops: list[str] = CROPS,
    state: str = STATE,
    water_basis: str = "total_need",
    rainfall_scenario: str = "normal",
    region: str = "maharashtra",
) -> tuple[pd.DataFrame, list[str]]:
    """The REALIZED outcome info set for year t: actual Maharashtra yield,
    actual harvest-window mean price, and the same cost_t as planning (cost
    isn't "revealed" after the season -- it's realized as spent, same figure
    either way). Returns (params_df, missing_crops) -- missing_crops lists
    crops with no realized yield row for year t in yield_clean.parquet
    (Maharashtra's yield data tops out at 2019, so t=2020 is missing for
    EVERY crop -- see docs/backtest.md)."""
    ref = load_reference()
    msp_hist = load_msp_history()
    price_df = load_price_frame()
    wide = build_wide_price_table(price_df)

    rows, missing = [], []
    for crop in crops:
        yield_qtl_ha = realized_yield_for_year(crop, t, state)
        price = realized_price_for_year(crop, t, msp_hist, wide)
        if yield_qtl_ha is None or price is None:
            missing.append(crop)
            continue
        cost_qtl, _ = cost_for_year(crop, t, msp_hist, ref)
        row = _base_params_row(crop, yield_qtl_ha, price, cost_qtl, ref, water_basis, rainfall_scenario, region)
        row["profit_std_ha"] = 0.0  # not used for realized evaluation (no forward-looking risk on an outcome)
        rows.append(row)

    params_df = pd.DataFrame(rows).set_index("crop") if rows else pd.DataFrame()
    return params_df, missing


def hybrid_params_df(
    forecast_params: pd.DataFrame, realized_params: pd.DataFrame, realized_price: bool, realized_yield: bool
) -> pd.DataFrame:
    """Planning params with PARTIAL foresight: the forecast table with the
    realized price and/or the realized yield swapped in (per-hectare cost stays
    the planned, sowing-time cost, exactly as commit_planned_costs does for the
    full oracle). Used for the price-only and yield-only foresight oracles,
    which split "how much would perfect foresight be worth" into the part due
    to knowing prices and the part due to knowing yields. Crops without a
    realized row keep their forecast."""
    out = forecast_params.copy()
    common = out.index.intersection(realized_params.index)
    if realized_price:
        out.loc[common, "price"] = realized_params.loc[common, "price"]
    if realized_yield:
        out.loc[common, "yield_qtl_ha"] = realized_params.loc[common, "yield_qtl_ha"]
    out["profit_ha"] = out["yield_qtl_ha"] * out["price"] - out["cost_ha"]
    return out


def commit_planned_costs(realized_params: pd.DataFrame, forecast_params: pd.DataFrame) -> pd.DataFrame:
    """Cost of cultivation (seed, fertilizer, labour, ...) is spent per
    hectare at sowing, before yield is known, so the realized outcome uses
    the PLANNED per-ha cost, not cost_rs_per_qtl x realized yield. Keeps the
    yield/price/interaction decomposition clean (cost effect == 0 by
    definition) and avoids a bad harvest "saving" cost."""
    out = realized_params.copy()
    if out.empty:
        return out
    common = out.index.intersection(forecast_params.index)
    out.loc[common, "cost_ha"] = forecast_params.loc[common, "cost_ha"]
    out["profit_ha"] = out["yield_qtl_ha"] * out["price"] - out["cost_ha"]
    return out


# --- 4) B1 current mix, leak-free (years t-5..t-1 only) --------------------


def current_mix_leakfree(params_df: pd.DataFrame, scenario, t: int, n_years: int = 5, state: str = STATE) -> np.ndarray:
    """Same algorithm as agriopt.optim.baselines.current_mix (shared via
    mix_from_shares), but restricted to yield_clean.parquet rows with
    year <= t-1 BEFORE taking the "last n_years" area average --
    baselines.current_mix reads the whole file with no cutoff, which would
    leak years >= t for early decision years (e.g. t=2016 would otherwise
    see 2016-2019 shares)."""
    crops = list(params_df.index)
    share = historical_area_share(crops, n_years=n_years, state=state, max_year=t - 1)
    return mix_from_shares(share, params_df, scenario)


# --- 5) Leak-free risk inputs (Sigma from years <= t-1 only) ----------------


def _yield_series_leakfree(crop: str, max_year: int, state: str = STATE) -> pd.Series:
    df = pd.read_parquet(YIELD_CLEAN_PARQUET)
    season = MAIN_SEASON[crop]
    name = CANON_TO_YIELD_NAME[crop]
    sub = df[(df["state"] == state) & (df["crop"] == name) & (df["season"] == season) & (df["year"] <= max_year)]
    by_year = sub.groupby("year")["yield"].mean()
    return by_year.apply(YIELD_TO_SALEABLE_QTL_PER_HA[crop]).sort_index()


def _price_series_leakfree(crop: str, wide: pd.DataFrame, max_year: int) -> pd.Series:
    season = MAIN_SEASON[crop]
    windows = HARVEST_WINDOW_MONTHS[season]
    years = [y for y in sorted(wide.index.year.unique()) if y <= max_year]
    out = {}
    for t in years:
        vals = []
        for offset, month in windows:
            key = pd.Timestamp(year=t + offset, month=month, day=1)
            if key in wide.index and crop in wide.columns:
                v = wide.loc[key, crop]
                if pd.notna(v):
                    vals.append(v)
        if vals:
            out[t] = float(np.mean(vals))
    return pd.Series(out).sort_index()


def build_risk_inputs_leakfree(max_year: int, crops: list[str] = CROPS, state: str = STATE, R: np.ndarray | None = None):
    """Leak-free analogue of agriopt.optim.risk.build_risk_inputs: every
    deviation-matrix year is <= max_year (== t-1 for decision year t), and
    the OLS detrend fit inside detrend_relative_deviation only ever sees
    those same restricted years (no future-year leakage into the trend
    itself). Sugarcane: constant FRP-at-max_year, matching risk.py's
    "yield-only variance" treatment for sugarcane."""
    from agriopt.optim.risk import RiskInputs  # local import to avoid a cycle at module load time

    price_df = load_price_frame()
    wide_full = build_wide_price_table(price_df)
    # restrict to months <= May of (max_year+1) -- the latest month whose
    # info is needed/available for any crop-year's harvest-window revenue at
    # or before max_year (rabi crop-year `max_year`'s window is Mar-May of
    # max_year+1, and that window closing is <= the decision month of t, so
    # this is not a leak).
    cutoff = pd.Timestamp(year=max_year + 1, month=5, day=31)
    wide = wide_full.loc[wide_full.index <= cutoff]

    revenue_cols, deviation_cols, trend_info, cv_rows = {}, {}, {}, []
    ref = load_reference()
    for crop in crops:
        yld = _yield_series_leakfree(crop, max_year, state)
        if crop == "sugarcane":
            frp = float(ref[ref["crop"] == "sugarcane"].iloc[0]["admin_price_rs_per_qtl"])
            price = pd.Series(frp, index=yld.index)
        else:
            price = _price_series_leakfree(crop, wide, max_year)
        common = yld.index.intersection(price.index)
        revenue = (yld.loc[common] * price.loc[common]).sort_index()
        deviation, info = detrend_relative_deviation(revenue)
        revenue_cols[crop] = revenue
        deviation_cols[crop] = deviation
        trend_info[crop] = info
        cv = float(revenue.std() / revenue.mean()) if len(revenue) > 1 and revenue.mean() != 0 else float("nan")
        cv_rows.append({"crop": crop, "n_years": len(revenue), "cv": cv, "trend_slope_log_per_year": info["slope"]})

    revenue_matrix = pd.DataFrame(revenue_cols)
    deviation_matrix = pd.DataFrame(deviation_cols).reindex(columns=crops)

    if R is None:
        raise ValueError("build_risk_inputs_leakfree: R (expected revenue/ha per crop, forecast basis) is required")
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
