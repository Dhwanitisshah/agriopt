"""Price forecasting: Naive / Seasonal-Naive baselines + a pooled XGBoost
model, evaluated by rolling-origin backtest, and the expected_price()
inference API.

Target is log(modal_price_rs_per_qtl) (plain log, not log1p -- price is
always > 0); all evaluation metrics are on the original scale. Forecasting
is DIRECT (one model per horizon h in {3, 6, 12} months), not recursive.

Sugarcane has no mandi series -- it's excluded from PRICE_CROPS and served
by expected_price() via the FRP in crop_reference.csv instead (method "FRP").

IMPORTANT (documented per the Phase 2 brief): there is no further held-out
test set beyond the rolling-origin backtest, so "best model for h=12
selected on backtest MAE" is effectively a VALIDATION-based choice, not a
true test-set evaluation -- the backtest numbers reported for the winning
model are the same numbers used to select it.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from xgboost import XGBRegressor

from agriopt.config import (
    CROP_NAME_MAP,
    PRICE_MODEL_METADATA_PATH,
    PRICE_MODEL_PATH,
    PRICES_MONTHLY_PARQUET,
    RANDOM_SEED,
)
from agriopt.data.reference import load_reference

HORIZONS = [3, 6, 12]
LAGS = [0, 1, 2, 3, 6, 12]
FEATURE_COLS = [f"lag_{lag}" for lag in LAGS] + [
    "roll_mean_3",
    "roll_std_3",
    "roll_mean_12",
    "roll_std_12",
    "yoy_change",
    "month_of_year",
]
CAT_COLS = ["crop"]

BACKTEST_START = pd.Timestamp("2021-11-01")
REFIT_EVERY = 6

XGB_PARAMS = dict(n_estimators=200, max_depth=4, learning_rate=0.1)

PRICE_CROPS = [k for k, v in CROP_NAME_MAP.items() if v["ceda_commodity"] is not None]  # 7 crops, excl. sugarcane


# --- Data loading -------------------------------------------------------------


def load_price_frame(path=PRICES_MONTHLY_PARQUET) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df["month"] = pd.to_datetime(df["month"])
    return df.sort_values(["crop", "month"]).reset_index(drop=True)


def build_wide_price_table(df: pd.DataFrame) -> pd.DataFrame:
    """month (full monthly frequency) x crop -> modal_price_rs_per_qtl.
    Small calendar gaps (a handful of months per crop, see
    reports/eda/eda_report.md "Price coverage") are forward-filled -- mandi
    prices don't jump overnight, and a missing report is not a missing
    price."""
    wide = df.pivot(index="month", columns="crop", values="modal_price_rs_per_qtl")
    wide = wide.asfreq("MS")
    return wide.ffill()


# --- Feature engineering (leakage-safe: only data <= origin) -----------------


def build_base_features(wide: pd.DataFrame, lags: list[int] = LAGS) -> pd.DataFrame:
    """One row per (crop, origin month), with lag/rolling/YoY features
    computed using only data up to and including the origin month. Rows
    without a full lag_12 history are dropped (insufficient warm-up)."""
    frames = []
    for crop in wide.columns:
        s = wide[crop]
        feat = pd.DataFrame(index=s.index)
        for lag in lags:
            feat[f"lag_{lag}"] = s.shift(lag)
        feat["roll_mean_3"] = s.rolling(3).mean()
        feat["roll_std_3"] = s.rolling(3).std()
        feat["roll_mean_12"] = s.rolling(12).mean()
        feat["roll_std_12"] = s.rolling(12).std()
        feat["yoy_change"] = (s - s.shift(12)) / s.shift(12)
        feat["crop"] = crop
        feat["origin_month"] = feat.index
        frames.append(feat)
    out = pd.concat(frames, ignore_index=True)
    return out.dropna(subset=[f"lag_{max(lags)}"]).reset_index(drop=True)


def build_horizon_table(base: pd.DataFrame, wide: pd.DataFrame, h: int) -> pd.DataFrame:
    """Add target_month / month_of_year (of the TARGET) / target_price
    (actual price at origin+h, NaN if beyond available data) for horizon h."""
    out = base.copy()
    out["target_month"] = out["origin_month"] + pd.DateOffset(months=h)
    out["month_of_year"] = out["target_month"].dt.month
    long_price = wide.stack()  # pandas 3.x: no longer drops NaN by default
    long_price.index.names = ["month", "crop"]
    lookup_idx = pd.MultiIndex.from_arrays([out["target_month"], out["crop"]])
    out["target_price"] = long_price.reindex(lookup_idx).to_numpy()
    return out


# --- Naive baselines -----------------------------------------------------------


def naive_forecast(wide: pd.DataFrame, crop: str, origin_month: pd.Timestamp) -> float:
    """Last observed value (the origin month's own price)."""
    return float(wide.loc[origin_month, crop]) if origin_month in wide.index else np.nan


def seasonal_naive_forecast(wide: pd.DataFrame, crop: str, origin_month: pd.Timestamp, h: int) -> float:
    """Value 12 months before the TARGET month (target = origin + h)."""
    target_month = origin_month + pd.DateOffset(months=h)
    ref_month = target_month - pd.DateOffset(months=12)
    return float(wide.loc[ref_month, crop]) if ref_month in wide.index else np.nan


# --- XGBoost (pooled across crops) ----------------------------------------------


def _prep_xgb_features(rows: pd.DataFrame) -> pd.DataFrame:
    X = rows[FEATURE_COLS].copy()
    X["crop"] = pd.Categorical(rows["crop"], categories=PRICE_CROPS)
    return X


def fit_xgb(train_rows: pd.DataFrame, random_seed: int = RANDOM_SEED, **params) -> XGBRegressor:
    X = _prep_xgb_features(train_rows)
    y = np.log(train_rows["target_price"].to_numpy())
    model = XGBRegressor(tree_method="hist", enable_categorical=True, random_state=random_seed, **{**XGB_PARAMS, **params})
    model.fit(X, y)
    return model


def predict_xgb(model: XGBRegressor, rows: pd.DataFrame) -> np.ndarray:
    X = _prep_xgb_features(rows)
    return np.exp(model.predict(X))


# --- Rolling-origin backtest ---------------------------------------------------


def backtest_origins(wide: pd.DataFrame, h: int, backtest_start: pd.Timestamp = BACKTEST_START) -> pd.DatetimeIndex:
    last_month = wide.index.max()
    last_origin = last_month - pd.DateOffset(months=h)
    return pd.date_range(backtest_start, last_origin, freq="MS")


def rolling_origin_backtest(df: pd.DataFrame, h: int, refit_every: int = REFIT_EVERY) -> pd.DataFrame:
    """For horizon h: at every origin month (monthly steps, 2021-11 to
    last_month - h), predict target = origin + h with Naive, Seasonal-Naive,
    and XGBoost (refit only every `refit_every` origins -- reused for the
    origins in between). XGB trains ONLY on (crop, origin') rows whose
    target_month <= current origin (i.e. already realized by the time we
    stand at this origin) -- no future leakage."""
    wide = build_wide_price_table(df)
    base = build_base_features(wide)
    horizon_table = build_horizon_table(base, wide, h)

    origins = backtest_origins(wide, h)

    rows = []
    fitted_model = None
    for i, origin in enumerate(origins):
        if i % refit_every == 0 or fitted_model is None:
            train_rows = horizon_table[
                (horizon_table["target_month"] <= origin) & horizon_table["target_price"].notna()
            ]
            fitted_model = fit_xgb(train_rows)

        test_rows = horizon_table[horizon_table["origin_month"] == origin]
        if test_rows.empty:
            continue
        xgb_preds = predict_xgb(fitted_model, test_rows)

        for (_, row), xgb_pred in zip(test_rows.iterrows(), xgb_preds):
            rows.append(
                {
                    "horizon": h,
                    "origin_month": origin,
                    "target_month": row["target_month"],
                    "crop": row["crop"],
                    "actual": row["target_price"],
                    "pred_naive": naive_forecast(wide, row["crop"], origin),
                    "pred_seasonal_naive": seasonal_naive_forecast(wide, row["crop"], origin, h),
                    "pred_xgb": float(xgb_pred),
                }
            )
    return pd.DataFrame(rows)


# --- Metrics --------------------------------------------------------------


def compute_price_metrics(actual: np.ndarray, pred: np.ndarray) -> dict:
    actual = np.asarray(actual, dtype=float)
    pred = np.asarray(pred, dtype=float)
    valid = ~(np.isnan(actual) | np.isnan(pred))
    a, p = actual[valid], pred[valid]
    if len(a) == 0:
        return {"MAE": float("nan"), "RMSE": float("nan"), "MAPE": float("nan"), "n": 0}
    err = a - p
    return {
        "MAE": float(np.mean(np.abs(err))),
        "RMSE": float(np.sqrt(np.mean(err**2))),
        "MAPE": float(np.mean(np.abs(err / a)) * 100),
        "n": int(len(a)),
    }


# --- Save / load --------------------------------------------------------------


def save_price_model(model, metadata: dict, model_path=PRICE_MODEL_PATH, metadata_path=PRICE_MODEL_METADATA_PATH) -> None:
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)
    metadata = dict(metadata)
    metadata["saved_at"] = datetime.now(timezone.utc).isoformat()
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, default=str)


def load_price_model(model_path=PRICE_MODEL_PATH):
    return joblib.load(model_path)


def load_price_metadata(metadata_path=PRICE_MODEL_METADATA_PATH) -> dict:
    with open(metadata_path, encoding="utf-8") as f:
        return json.load(f)


# --- Inference API --------------------------------------------------------------


def expected_price(crop: str, horizon: int = 12, msp_floor: bool = False) -> dict:
    """Expected price, Rs/quintal, `horizon` months ahead of the last
    observed month.

    - sugarcane: returns the FRP from crop_reference.csv (method "FRP"),
      never forecast.
    - other crops: uses the model selected as best for h=12 on the backtest
      (models/price_best_h12.json), refit on all data through the last
      observed month. Only horizon=12 is currently served (that's the only
      saved/refit model) -- other horizons raise.
    - msp_floor=True clips the forecast to at least the crop's MSP
      (crop_reference.csv msp_rs_per_qtl), if it has one.
    """
    if crop == "sugarcane":
        ref = load_reference()
        row = ref[ref["crop"] == "sugarcane"].iloc[0]
        return {
            "crop": crop,
            "value_rs_per_qtl": float(row["admin_price_rs_per_qtl"]),
            "method": "FRP",
            "origin_month": None,
            "target_month": None,
        }

    if horizon != 12:
        raise NotImplementedError(
            f"expected_price only serves horizon=12 (models/price_best_h12.*); got horizon={horizon}"
        )

    metadata = load_price_metadata()
    method = metadata["method"]
    origin_month = pd.Timestamp(metadata["origin_month"])
    target_month = origin_month + pd.DateOffset(months=horizon)

    if method == "XGBoost":
        model = load_price_model()
        df = load_price_frame()
        wide = build_wide_price_table(df)
        base = build_base_features(wide)
        row = base[(base["crop"] == crop) & (base["origin_month"] == origin_month)]
        if row.empty:
            raise ValueError(f"No feature row for crop={crop!r} at origin {origin_month.date()}")
        row = row.copy()
        row["month_of_year"] = target_month.month
        value = float(predict_xgb(model, row)[0])
    else:
        df = load_price_frame()
        wide = build_wide_price_table(df)
        if method == "Naive":
            value = naive_forecast(wide, crop, origin_month)
        elif method == "Seasonal-Naive":
            value = seasonal_naive_forecast(wide, crop, origin_month, horizon)
        else:
            raise ValueError(f"Unknown method in price_best_h12.json: {method!r}")

    if msp_floor:
        ref = load_reference()
        row = ref[ref["crop"] == crop]
        if not row.empty and pd.notna(row.iloc[0]["msp_rs_per_qtl"]):
            value = max(value, float(row.iloc[0]["msp_rs_per_qtl"]))

    return {
        "crop": crop,
        "value_rs_per_qtl": value,
        "method": method,
        "origin_month": str(origin_month.date()),
        "target_month": str(target_month.date()),
    }
