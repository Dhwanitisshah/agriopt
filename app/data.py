"""Cache-only data access for the Streamlit app.

The app never calls agriopt.optim.params.build_crop_params() directly --
that would load models/yield_best.joblib (~528 MB) on every cold start.
Instead it reads scripts/40_build_cache.py's precomputed
data/processed/crop_params_cache.json. If that cache is missing, callers
should show an actionable st.error rather than crash.
"""
from __future__ import annotations

import json

import pandas as pd

from agriopt.config import DATA_PROCESSED, YIELD_CLEAN_PARQUET

CACHE_PATH = DATA_PROCESSED / "crop_params_cache.json"
BUILD_CACHE_CMD = "python scripts\\40_build_cache.py"


def cache_exists() -> bool:
    return CACHE_PATH.exists()


def load_cache_raw() -> dict:
    with open(CACHE_PATH, encoding="utf-8") as f:
        return json.load(f)


def params_df_from_records(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(records).set_index("crop")
    df["seasons_occupied"] = df["seasons_occupied"].apply(set)
    return df


def load_yield_clean() -> pd.DataFrame:
    return pd.read_parquet(YIELD_CLEAN_PARQUET)
