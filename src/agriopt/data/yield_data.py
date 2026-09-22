"""Loading and cleaning logic for the crop-yield dataset (all-India, Kaggle
"crop-yield-in-indian-states-dataset"). Reusable functions only -- reporting
and plotting live in scripts/01_audit_yield.py.
"""
from __future__ import annotations

import pandas as pd

from agriopt.config import CROP_NAME_MAP, YIELD_RAW_CSV

RAW_STRING_COLUMNS = ["Crop", "Season", "State"]

TARGET_YIELD_NAMES = {v["yield"] for v in CROP_NAME_MAP.values()}

CLEAN_COLUMNS = [
    "crop",
    "season",
    "year",
    "state",
    "area_ha",
    "rainfall_mm",
    "fertilizer_per_ha",
    "pesticide_per_ha",
    "yield",
    "is_target_crop",
]


def load_raw_yield(path=YIELD_RAW_CSV) -> pd.DataFrame:
    """Load the raw yield CSV, stripping whitespace from column names and
    string-typed values."""
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    for col in RAW_STRING_COLUMNS:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    return df


def leakage_yield_vs_production(df: pd.DataFrame) -> pd.Series:
    """Max abs diff between Yield and Production/Area, restricted to Area > 0.

    Returns the per-row absolute difference series (Area <= 0 rows excluded)
    so callers can summarize (max/mean/etc).
    """
    sub = df[df["Area"] > 0]
    implied_yield = sub["Production"] / sub["Area"]
    return (sub["Yield"] - implied_yield).abs()


def correlation_fert_pesticide_area(df: pd.DataFrame) -> dict:
    """Pearson correlation of raw Fertilizer/Pesticide totals against Area.

    A correlation > 0.8 indicates the columns are farm-level *totals* (scale
    with area) rather than already-normalized per-hectare rates.
    """
    return {
        "fertilizer_vs_area": df["Fertilizer"].corr(df["Area"]),
        "pesticide_vs_area": df["Pesticide"].corr(df["Area"]),
    }


def find_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    return df[df.duplicated(keep=False)]


def find_invalid_areas(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["Area"] <= 0]


def find_outliers_iqr(df: pd.DataFrame, crop_col: str = "Crop", value_col: str = "Yield") -> pd.DataFrame:
    """Per-crop IQR outlier flags. Returns a frame with one row per crop:
    crop, n, n_outliers, lower_bound, upper_bound."""
    rows = []
    for crop, sub in df.groupby(crop_col):
        q1, q3 = sub[value_col].quantile([0.25, 0.75])
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        n_outliers = ((sub[value_col] < lower) | (sub[value_col] > upper)).sum()
        rows.append(
            {
                "crop": crop,
                "n": len(sub),
                "n_outliers": int(n_outliers),
                "lower_bound": lower,
                "upper_bound": upper,
            }
        )
    return pd.DataFrame(rows).sort_values("n_outliers", ascending=False).reset_index(drop=True)


def clean_yield_data(df: pd.DataFrame) -> pd.DataFrame:
    """Produce the cleaned ALL-INDIA frame written to data/processed/yield_clean.parquet.

    - drops exact-duplicate rows
    - drops rows with Area <= 0 (per-hectare rates are undefined otherwise)
    - drops Production (LEAKAGE 1: Yield is derived from Production/Area)
    - converts Fertilizer/Pesticide totals to per-hectare rates (LEAKAGE 2:
      raw totals are highly correlated with Area, i.e. farm-level totals)
    - flags is_target_crop for the 8 canonical AgriOpt crops
    """
    out = df.drop_duplicates().copy()
    out = out[out["Area"] > 0].copy()

    out["fertilizer_per_ha"] = out["Fertilizer"] / out["Area"]
    out["pesticide_per_ha"] = out["Pesticide"] / out["Area"]
    out["is_target_crop"] = out["Crop"].isin(TARGET_YIELD_NAMES)

    out = out.rename(
        columns={
            "Crop": "crop",
            "Season": "season",
            "Crop_Year": "year",
            "State": "state",
            "Area": "area_ha",
            "Annual_Rainfall": "rainfall_mm",
            "Yield": "yield",
        }
    )

    return out[CLEAN_COLUMNS].reset_index(drop=True)


def maharashtra_target_counts(df: pd.DataFrame, state: str = "Maharashtra") -> pd.DataFrame:
    """Row counts per (canonical crop, season) for the given state, using the
    raw (unrenamed) column names."""
    mh = df[df["State"] == state]
    rows = []
    for canon, names in CROP_NAME_MAP.items():
        sub = mh[mh["Crop"] == names["yield"]]
        if sub.empty:
            rows.append({"crop": canon, "season": None, "n_rows": 0})
            continue
        for season, ssub in sub.groupby("Season"):
            rows.append({"crop": canon, "season": season, "n_rows": len(ssub)})
    return pd.DataFrame(rows)
