"""Yield prediction: baselines, Ridge, RandomForest, XGBoost, and the
inference API used by the optimizer (Phase 2+).

Target is log1p(yield); all evaluation metrics are computed on the original
scale (expm1(pred)) -- see compute_metrics(). Categorical features (crop,
season, state) are one-hot encoded for Ridge/RandomForest and passed as
native pandas `category` dtype for XGBoost (XGBoost's built-in categorical
splits, tree_method="hist"), rather than one-hot everywhere, to avoid an
~90-column sparse block for a model that handles categories natively --
documented here per the Phase 1 brief's "pick one, document it".
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBRegressor

from agriopt.config import (
    CROP_NAME_MAP,
    MAIN_SEASON,
    RANDOM_SEED,
    STATE,
    TEST_START_YEAR,
    TRAIN_END_YEAR,
    YIELD_CLEAN_PARQUET,
    YIELD_CONFORMAL_METADATA_PATH,
    YIELD_CONFORMAL_MODEL_PATH,
    YIELD_MODEL_METADATA_PATH,
    YIELD_MODEL_PATH,
    YIELD_TO_SALEABLE_QTL_PER_HA,
)

CAT_COLS = ["crop", "season", "state"]
CORE_NUM_COLS = ["year", "rainfall_mm"]
FERT_PEST_COLS = ["fertilizer_per_ha", "pesticide_per_ha"]

VALID_START_YEAR = 2013
VALID_END_YEAR = TRAIN_END_YEAR  # 2015, inclusive
YEAR_PROXY_CV_THRESHOLD = 0.01  # "near-zero" within-year coefficient of variation

SINGLETON_OUTLIER_RATIO_THRESHOLD = 20

YIELD_NAME_TO_CANON = {v["yield"]: k for k, v in CROP_NAME_MAP.items()}
CANON_TO_YIELD_NAME = {k: v["yield"] for k, v in CROP_NAME_MAP.items()}


# --- Data loading & cleaning -------------------------------------------------


def flag_singleton_extreme_outliers(df: pd.DataFrame, ratio_threshold: float = SINGLETON_OUTLIER_RATIO_THRESHOLD) -> pd.Series:
    """True for rows that are BOTH (a) the only observation for their
    (state, crop, season) group across the whole dataset, and (b) more than
    `ratio_threshold`x that crop's national median yield.

    This narrowly targets single-row data-entry errors (e.g. Maharashtra
    Maize/Autumn/1997 at 989.87 t/ha -- physically impossible, and the ONLY
    row ever recorded for that group) while preserving legitimate multi-year
    patterns (e.g. Chhattisgarh Bajra/Whole Year consistently running
    30-70x other states' Bajra median across 13 consecutive years -- a real,
    if unusual, reporting convention, not a typo -- which this filter does
    NOT flag because group_size > 1).
    """
    med = df.groupby("crop")["yield"].transform("median")
    ratio = df["yield"] / med
    group_size = df.groupby(["state", "crop", "season"])["year"].transform("count")
    return (ratio > ratio_threshold) & (group_size == 1)


def load_model_frame(path=YIELD_CLEAN_PARQUET) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load yield_clean.parquet, add log_yield + canon_crop, and drop
    singleton extreme-outlier rows (see flag_singleton_extreme_outliers).

    Returns (clean_df, dropped_rows_df) so callers can report what was removed.
    """
    df = pd.read_parquet(path)
    df["canon_crop"] = df["crop"].map(YIELD_NAME_TO_CANON)

    outlier_mask = flag_singleton_extreme_outliers(df)
    dropped = df[outlier_mask].copy()
    df = df[~outlier_mask].copy()

    df["log_yield"] = np.log1p(df["yield"])
    return df.reset_index(drop=True), dropped.reset_index(drop=True)


# --- Feature sanity check (Phase 1, step 0) ----------------------------------


def feature_variance_audit(df: pd.DataFrame) -> pd.DataFrame:
    """Within-year coefficient of variation (std/mean) for fertilizer_per_ha
    and pesticide_per_ha, across all (state, crop, season) rows in each year.
    Near-zero CV means the column is really just a single national rate per
    year -- a year proxy that should be excluded from the main feature set
    (year is already a feature)."""
    rows = []
    for col in FERT_PEST_COLS:
        by_year = df.groupby("year")[col]
        std = by_year.std()
        mean = by_year.mean()
        cv = (std / mean.replace(0, np.nan)).mean()
        rows.append(
            {
                "column": col,
                "mean_within_year_std": std.mean(),
                "mean_within_year_mean": mean.mean(),
                "mean_within_year_cv": cv,
                "year_proxy": bool(cv < YEAR_PROXY_CV_THRESHOLD),
            }
        )
    return pd.DataFrame(rows)


def decide_fertilizer_pesticide_inclusion(audit: pd.DataFrame) -> bool:
    """True if fertilizer/pesticide carry real (non-year-proxy) signal and
    should be included in the main feature set."""
    return not audit["year_proxy"].any()


def row_counts_report(df: pd.DataFrame, crops: list[str], state: str = STATE) -> pd.DataFrame:
    """Train (<=TRAIN_END_YEAR) vs test (>=TEST_START_YEAR) row counts, all-India
    and state-only, per target crop."""
    rows = []
    for crop in crops:
        name = CANON_TO_YIELD_NAME[crop]
        sub = df[df["crop"] == name]
        mh = sub[sub["state"] == state]
        rows.append(
            {
                "crop": crop,
                "all_india_train": int((sub["year"] <= TRAIN_END_YEAR).sum()),
                "all_india_test": int((sub["year"] >= TEST_START_YEAR).sum()),
                f"{state.lower()}_train": int((mh["year"] <= TRAIN_END_YEAR).sum()),
                f"{state.lower()}_test": int((mh["year"] >= TEST_START_YEAR).sum()),
            }
        )
    return pd.DataFrame(rows)


# --- Splits -------------------------------------------------------------------


def train_test_split_by_year(df: pd.DataFrame, train_end_year: int = TRAIN_END_YEAR, test_start_year: int = TEST_START_YEAR):
    train = df[df["year"] <= train_end_year].reset_index(drop=True)
    test = df[df["year"] >= test_start_year].reset_index(drop=True)
    return train, test


def tuning_split(df: pd.DataFrame, valid_start_year: int = VALID_START_YEAR, valid_end_year: int = VALID_END_YEAR):
    """fit-for-tuning years (< valid_start_year) vs validation years [valid_start_year, valid_end_year]."""
    fit = df[df["year"] < valid_start_year].reset_index(drop=True)
    valid = df[(df["year"] >= valid_start_year) & (df["year"] <= valid_end_year)].reset_index(drop=True)
    return fit, valid


# --- Metrics --------------------------------------------------------------


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """MAE / RMSE / R2 / MAPE on the ORIGINAL (non-log) scale.

    MAPE excludes true-zero-yield rows (real crop-failure records exist in
    the all-India data, e.g. Onion/Kerala/2016) since MAPE is undefined for
    y_true == 0; MAE/RMSE/R2 use all rows."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    nonzero = y_true != 0
    mape = float(np.mean(np.abs((y_true[nonzero] - y_pred[nonzero]) / y_true[nonzero])) * 100) if nonzero.any() else float("nan")
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(root_mean_squared_error(y_true, y_pred)),
        "R2": float(r2_score(y_true, y_pred)),
        "MAPE": mape,
    }


# --- Baseline models --------------------------------------------------------


def _group_last_observed(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    """For each group, the mean yield among rows from that group's most
    recent year present in df (a single row for fine-grained groups like
    (state, crop, season); a same-year cross-section mean for coarser
    fallback groups like (crop, season) or (crop,))."""
    latest_year = df.groupby(group_cols)["year"].transform("max")
    last_rows = df[df["year"] == latest_year]
    return last_rows.groupby(group_cols)["yield"].mean().reset_index()


class BaselineMean:
    """Mean yield of the same (state, crop, season) in training years;
    fallback (crop, season) mean, then crop mean."""

    name = "Baseline-Mean"

    def fit(self, train_df: pd.DataFrame) -> "BaselineMean":
        self._g3 = train_df.groupby(["state", "crop", "season"])["yield"].mean().reset_index().rename(columns={"yield": "pred3"})
        self._g2 = train_df.groupby(["crop", "season"])["yield"].mean().reset_index().rename(columns={"yield": "pred2"})
        self._g1 = train_df.groupby(["crop"])["yield"].mean().reset_index().rename(columns={"yield": "pred1"})
        self._global = float(train_df["yield"].mean())
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        out = df[["state", "crop", "season"]].merge(self._g3, on=["state", "crop", "season"], how="left")
        out = out.merge(self._g2, on=["crop", "season"], how="left")
        out = out.merge(self._g1, on=["crop"], how="left")
        pred = out["pred3"].fillna(out["pred2"]).fillna(out["pred1"]).fillna(self._global)
        return pred.to_numpy()


class BaselineLast:
    """Last observed training yield for the same (state, crop, season);
    same fallback cascade as BaselineMean, but using the most recently
    observed value(s) instead of an all-years mean."""

    name = "Baseline-Last"

    def fit(self, train_df: pd.DataFrame) -> "BaselineLast":
        self._g3 = _group_last_observed(train_df, ["state", "crop", "season"]).rename(columns={"yield": "pred3"})
        self._g2 = _group_last_observed(train_df, ["crop", "season"]).rename(columns={"yield": "pred2"})
        self._g1 = _group_last_observed(train_df, ["crop"]).rename(columns={"yield": "pred1"})
        last_year = train_df["year"].max()
        self._global = float(train_df.loc[train_df["year"] == last_year, "yield"].mean())
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        out = df[["state", "crop", "season"]].merge(self._g3, on=["state", "crop", "season"], how="left")
        out = out.merge(self._g2, on=["crop", "season"], how="left")
        out = out.merge(self._g1, on=["crop"], how="left")
        pred = out["pred3"].fillna(out["pred2"]).fillna(out["pred1"]).fillna(self._global)
        return pred.to_numpy()


# --- ML models ---------------------------------------------------------------


class SklearnYieldModel:
    """Ridge / RandomForest wrapper: one-hot(crop, season, state) + scaled
    numerics -> regressor on log1p(yield). predict() returns original scale."""

    def __init__(self, name: str, estimator, num_cols: list[str]):
        self.name = name
        self.num_cols = num_cols
        self.pipeline = Pipeline(
            [
                (
                    "prep",
                    ColumnTransformer(
                        [
                            ("cat", OneHotEncoder(handle_unknown="ignore"), CAT_COLS),
                            ("num", StandardScaler(), num_cols),
                        ]
                    ),
                ),
                ("model", estimator),
            ]
        )

    def fit(self, train_df: pd.DataFrame) -> "SklearnYieldModel":
        X = train_df[CAT_COLS + self.num_cols]
        y = train_df["log_yield"]
        self.pipeline.fit(X, y)
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        X = df[CAT_COLS + self.num_cols]
        return np.expm1(self.pipeline.predict(X))


class XgbYieldModel:
    """XGBoost wrapper using NATIVE categorical support (tree_method="hist",
    enable_categorical=True) rather than one-hot -- see module docstring.
    predict() returns original scale."""

    def __init__(self, name: str, num_cols: list[str], **xgb_params):
        self.name = name
        self.num_cols = num_cols
        self.xgb_params = xgb_params
        self.model = XGBRegressor(
            tree_method="hist",
            enable_categorical=True,
            random_state=RANDOM_SEED,
            **xgb_params,
        )
        self._categories: dict[str, list] = {}

    def _prep(self, df: pd.DataFrame, fit: bool) -> pd.DataFrame:
        X = df[CAT_COLS + self.num_cols].copy()
        for col in CAT_COLS:
            if fit:
                self._categories[col] = sorted(X[col].dropna().unique().tolist())
            X[col] = pd.Categorical(X[col], categories=self._categories[col])
        return X

    def fit(self, train_df: pd.DataFrame) -> "XgbYieldModel":
        X = self._prep(train_df, fit=True)
        y = train_df["log_yield"]
        self.model.fit(X, y)
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        X = self._prep(df, fit=False)
        return np.expm1(self.model.predict(X))


# --- Hyperparameter tuning ---------------------------------------------------

RF_GRID = [
    {"n_estimators": n, "max_depth": d, "min_samples_leaf": leaf}
    for n in (100, 300)
    for d in (None, 10, 20)
    for leaf in (1, 5)
]  # 12 combos

XGB_GRID = [
    {"n_estimators": n, "max_depth": d, "learning_rate": lr}
    for n in (100, 300)
    for d in (3, 6, 9)
    for lr in (0.05, 0.1)
]  # 12 combos


def tune_rf(fit_df: pd.DataFrame, valid_df: pd.DataFrame, num_cols: list[str]) -> dict:
    """Grid search RandomForest on (fit_df -> valid_df), selecting by MAE on
    the original scale. Returns the best hyperparameter dict."""
    best_params, best_mae = None, np.inf
    for params in RF_GRID:
        model = SklearnYieldModel(
            "RandomForest",
            RandomForestRegressor(random_state=RANDOM_SEED, n_jobs=-1, **params),
            num_cols,
        ).fit(fit_df)
        mae = mean_absolute_error(valid_df["yield"], model.predict(valid_df))
        if mae < best_mae:
            best_mae, best_params = mae, params
    return best_params


def tune_xgb(fit_df: pd.DataFrame, valid_df: pd.DataFrame, num_cols: list[str]) -> dict:
    """Grid search XGBoost on (fit_df -> valid_df), selecting by MAE on the
    original scale. Returns the best hyperparameter dict."""
    best_params, best_mae = None, np.inf
    for params in XGB_GRID:
        model = XgbYieldModel("XGBoost", num_cols, **params).fit(fit_df)
        mae = mean_absolute_error(valid_df["yield"], model.predict(valid_df))
        if mae < best_mae:
            best_mae, best_params = mae, params
    return best_params


# --- Save / load --------------------------------------------------------------


def save_model(model, metadata: dict, model_path=YIELD_MODEL_PATH, metadata_path=YIELD_MODEL_METADATA_PATH) -> None:
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)
    metadata = dict(metadata)
    metadata["saved_at"] = datetime.now(timezone.utc).isoformat()
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, default=str)


def _force_single_threaded_predict(model) -> None:
    """Force n_jobs=1 on any parallel estimator this model wraps.

    ROOT CAUSE (Phase 8 reproducibility investigation): the saved
    yield_best.joblib model is a SklearnYieldModel wrapping a
    RandomForestRegressor(n_jobs=-1). sklearn's RandomForest.predict()
    with n_jobs != 1 aggregates per-tree predictions across threads via
    joblib.Parallel into a shared accumulator; the ORDER in which threads
    add their partial sums is scheduled by the OS and is not fixed by
    `random_state` (random_state only fixes tree structure at fit time,
    not the runtime accumulation order at predict time). Floating-point
    addition is not associative, so this makes predict() output differ by
    ~1e-13 relative between process runs -- exactly the magnitude
    empirically observed here (verified: calling expected_yield_saleable
    repeatedly in separate `python -c` subprocesses gave different
    dataset_yield values at the ~14th significant digit; calling
    expected_price -- which uses XGBoost, whose prediction is a strictly
    sequential sum over boosting rounds, not a parallel-reduced sum over
    trees -- was stable). This tiny per-crop noise in profit_ha then
    propagates into build_crop_params -> the NSGA-II/III objective
    evaluation, and (with pymoo's own seeding of numpy.random confirmed
    fully reproducible in isolation) was the actual source of
    solve_nsga2/solve_nsga3 non-reproducibility across process runs.

    Forcing n_jobs=1 here makes prediction strictly single-threaded, so
    there is only one possible accumulation order -- fully reproducible,
    at a small, one-time model-loading cost (not per-optimizer-generation,
    so this doesn't slow down the NSGA-II/III loops)."""
    candidates = [model]
    candidates.append(getattr(model, "model", None))
    pipeline = getattr(model, "pipeline", None)
    if pipeline is not None:
        candidates.append(pipeline)
        named_steps = getattr(pipeline, "named_steps", None)
        if named_steps:
            candidates.extend(named_steps.values())
    for obj in candidates:
        if obj is not None and hasattr(obj, "n_jobs"):
            obj.n_jobs = 1


def load_model(model_path=YIELD_MODEL_PATH):
    model = joblib.load(model_path)
    _force_single_threaded_predict(model)
    return model


def load_metadata(metadata_path=YIELD_MODEL_METADATA_PATH) -> dict:
    with open(metadata_path, encoding="utf-8") as f:
        return json.load(f)


# --- Inference API for the optimizer -----------------------------------------


def predict_yield(
    crop: str,
    season: str,
    state: str,
    year: int,
    rainfall_mm: float,
    model=None,
    num_cols: list[str] | None = None,
    **optional,
) -> float:
    """Predict yield in DATASET units (t/ha, or bales/ha for cotton -- see
    docs/units.md) for a single (crop, season, state, year, rainfall) point.
    `crop` is the canonical AgriOpt name (e.g. "rice"); it's translated to
    the dataset's raw crop string internally. `**optional` may supply
    fertilizer_per_ha/pesticide_per_ha if the model's feature set includes
    them (see metadata["num_cols"]).

    By default this loads the saved INFERENCE model (models/yield_best.joblib,
    refit on all years -- see save/refit step in scripts/10_train_yield.py).
    Pass `model`/`num_cols` explicitly to predict with a different in-memory
    model (e.g. to compare the eval model vs the refit inference model)."""
    if model is None:
        model = load_model()
    if num_cols is None:
        num_cols = load_metadata()["num_cols"]

    row = {
        "crop": CANON_TO_YIELD_NAME.get(crop, crop),
        "season": season,
        "state": state,
        "year": year,
        "rainfall_mm": rainfall_mm,
    }
    for col in num_cols:
        if col not in row:
            if col in optional:
                row[col] = optional[col]
            else:
                raise ValueError(f"predict_yield: model needs '{col}' but it was not provided")

    df = pd.DataFrame([row])
    pred = model.predict(df)
    return float(pred[0])


def maharashtra_recent_rainfall_median(df: pd.DataFrame, state: str = STATE, n_years: int = 5) -> float:
    mh = df[df["state"] == state][["year", "rainfall_mm"]].drop_duplicates()
    recent = mh.sort_values("year", ascending=False).head(n_years)
    return float(recent["rainfall_mm"].median())


def expected_yield_saleable(
    crop: str,
    state: str = STATE,
    year: int | None = None,
    rainfall_mm: float | None = None,
    model=None,
    num_cols: list[str] | None = None,
) -> dict:
    """Quintals of MARKETED product per ha, for the crop's MAIN season in
    `state` (agriopt.config.MAIN_SEASON), via
    agriopt.config.YIELD_TO_SALEABLE_QTL_PER_HA.

    Defaults: year = (latest year in the training data) + 1; rainfall_mm =
    `state`'s median rainfall over its last 5 available years.

    Uses the saved INFERENCE model (yield_best, refit on all years) unless
    `model`/`num_cols` are passed explicitly -- see predict_yield().
    """
    df, _ = load_model_frame()
    season = MAIN_SEASON[crop]

    if year is None:
        year = int(df["year"].max()) + 1
    if rainfall_mm is None:
        rainfall_mm = maharashtra_recent_rainfall_median(df, state=state)

    dataset_yield = predict_yield(crop, season, state, year, rainfall_mm, model=model, num_cols=num_cols)
    saleable_qtl_ha = YIELD_TO_SALEABLE_QTL_PER_HA[crop](dataset_yield)

    return {
        "crop": crop,
        "state": state,
        "season": season,
        "year": year,
        "rainfall_mm": rainfall_mm,
        "dataset_yield": dataset_yield,
        "value": saleable_qtl_ha,
    }


# --- Phase 9: split-conformal prediction intervals ---------------------------
#
# Calibrated by scripts/92_conformal.py: RandomForest fit on year<=2012,
# conformal quantile (see agriopt.stats.conformal.conformal_quantile)
# calibrated on 2013-2015 LOG1P-YIELD absolute residuals (this repo's
# "log_yield" column is log1p(yield), not plain log -- see
# load_model_frame() -- so the interval is built in log1p-space and
# inverted with expm1, not exp; log1p is strictly increasing, same as log,
# so the coverage-transfer argument is unaffected: expm1(logpred - q) <=
# actual <= expm1(logpred + q) iff logpred - q <= log1p(actual) <=
# logpred + q). The calibrated quantile is PERSISTED (models/yield_conformal.json)
# rather than recomputed per call, since recomputation would mean refitting
# a RandomForest on every inference call -- far too slow for interactive use
# (e.g. the Streamlit app). Call scripts/92_conformal.py to (re)calibrate.


def load_conformal_model(model_path=YIELD_CONFORMAL_MODEL_PATH):
    return joblib.load(model_path)


def load_conformal_metadata(metadata_path=YIELD_CONFORMAL_METADATA_PATH) -> dict:
    with open(metadata_path, encoding="utf-8") as f:
        return json.load(f)


def predict_yield_interval(
    crop: str,
    season: str,
    state: str,
    year: int,
    rainfall_mm: float,
    alpha: float = 0.1,
    model=None,
    conformal_meta: dict | None = None,
    **optional,
) -> dict:
    """Split-conformal (1-alpha) interval for yield (dataset units, t/ha or
    bales/ha -- see docs/units.md), at the given (crop, season, state, year,
    rainfall_mm) point.

    Uses the CONFORMAL model (RandomForest fit on year<=2012, quantile
    calibrated on 2013-2015 residuals -- see scripts/92_conformal.py), NOT
    the production yield_best model (which is refit on ALL years and has no
    calibration set left over). `alpha=0.1` (the default, 90% interval) uses
    the persisted overall quantile unless a per-crop quantile was calibrated
    and is present in conformal_meta["q_per_crop"] (preferred when
    available -- narrower/wider per crop rather than one global band).

    Raises if alpha != 0.1 and no matching calibration exists (only alpha=0.1
    is currently calibrated/persisted -- see scripts/92_conformal.py).
    """
    if model is None:
        model = load_conformal_model()
    if conformal_meta is None:
        conformal_meta = load_conformal_metadata()

    if abs(alpha - conformal_meta["alpha"]) > 1e-9:
        raise NotImplementedError(
            f"predict_yield_interval: only alpha={conformal_meta['alpha']} is calibrated/persisted "
            f"(models/yield_conformal.json); got alpha={alpha}. Rerun scripts/92_conformal.py for a "
            "different alpha."
        )

    row = pd.DataFrame([{"crop": CANON_TO_YIELD_NAME.get(crop, crop), "season": season, "state": state, "year": year, "rainfall_mm": rainfall_mm}])
    for col in conformal_meta["num_cols"]:
        if col not in row.columns:
            if col in optional:
                row[col] = optional[col]
            else:
                raise ValueError(f"predict_yield_interval: model needs '{col}' but it was not provided")

    log_pred = float(model.pipeline.predict(row[conformal_meta["cat_cols"] + conformal_meta["num_cols"]])[0])

    q_per_crop = conformal_meta.get("q_per_crop", {})
    q = float(q_per_crop[crop]) if crop in q_per_crop else float(conformal_meta["q_overall"])

    pred_yield = float(np.expm1(log_pred))
    lower = float(np.expm1(log_pred - q))
    upper = float(np.expm1(log_pred + q))
    return {
        "crop": crop,
        "season": season,
        "state": state,
        "year": year,
        "rainfall_mm": rainfall_mm,
        "pred_yield": pred_yield,
        "lower": lower,
        "upper": upper,
        "level": 1.0 - conformal_meta["alpha"],
        "q_log1p": q,
        "q_source": "per_crop" if crop in q_per_crop else "overall",
    }
