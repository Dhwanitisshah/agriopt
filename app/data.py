"""Cache-only data access for the Streamlit app.

The app never calls agriopt.optim.params.build_crop_params() directly --
that would load models/yield_best.joblib (~528 MB) on every cold start.
Instead it reads scripts/40_build_cache.py's precomputed
data/processed/crop_params_cache.json. If that cache is missing, callers
should show an actionable st.error rather than crash.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from agriopt.config import DATA_PROCESSED, YIELD_CLEAN_PARQUET
from agriopt.optim.risk import RiskInputs

CACHE_PATH = DATA_PROCESSED / "crop_params_cache.json"
BUILD_CACHE_CMD = "python scripts\\40_build_cache.py"

SUGARCANE_RISK_MODES = {
    "conservative": "conservative",
    "frp_based": "frp_based",
}


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


def risk_inputs_from_cache(raw: dict, sugarcane_mode: str = "conservative") -> RiskInputs:
    """Reconstructs agriopt.optim.risk.RiskInputs from the cache's "risk"
    block (built offline by scripts/40_build_cache.py) -- the app never
    recomputes the deviation matrix or Sigma from raw yield/price data.
    `sugarcane_mode` selects which precomputed Sigma variant to use (see
    Phase 5.1's sugarcane risk-sensitivity analysis / Phase 6 item 10)."""
    r = raw["risk"]
    crops = r["crops"]

    dev_df = pd.DataFrame(r["deviation_matrix"]).set_index("year")
    dev_df = dev_df.reindex(columns=crops)

    cv_table = pd.DataFrame(r["cv_table"]).set_index("crop").reindex(crops)

    Sigma = np.array(r["Sigma"][sugarcane_mode], dtype=float)

    return RiskInputs(
        crops=crops,
        deviation_matrix=dev_df,
        revenue_matrix=pd.DataFrame(),  # not cached; not needed by the app
        Sigma=Sigma,
        min_eigenvalue_raw=r["min_eigenvalue_raw"],
        trend_info={},
        cv_table=cv_table,
    )


def revenue_vector_from_cache(raw: dict) -> np.ndarray:
    """R_i = current expected revenue/ha (yield_qtl_ha * price), in the same
    crop order as risk_inputs_from_cache -- precomputed alongside Sigma
    since Sigma = correlation x outer(R, R)."""
    return np.array(raw["risk"]["R"], dtype=float)
