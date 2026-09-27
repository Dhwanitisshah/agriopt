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


def params_records_for(raw: dict, region: str, water_basis: str, rainfall_scenario: str, price_mode: str) -> list[dict]:
    """Phase 10: looks up one params variant from the cache's nested
    "params" block: params[region][water_basis][price_mode] for
    water_basis="total_need" (rainfall_scenario is irrelevant to
    build_crop_params in that branch, so it is not a key there -- see
    scripts/40_build_cache.py's docstring for the full schema), or
    params[region][water_basis][rainfall_scenario][price_mode] for
    water_basis="net_irrigation"."""
    block = raw["params"][region][water_basis]
    if water_basis == "net_irrigation":
        block = block[rainfall_scenario]
    return block[price_mode]


def params_df_for(raw: dict, region: str, water_basis: str, rainfall_scenario: str, price_mode: str) -> pd.DataFrame:
    return params_df_from_records(params_records_for(raw, region, water_basis, rainfall_scenario, price_mode))


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


def match_preset(
    scenario,
    priority: float,
    risk_aware: bool,
    risk_aversion: float,
    sugarcane_mode: str,
    price_multipliers: dict,
    sugarcane_frp_override: float,
    sugarcane_default_frp: float,
    params_df_for_water_ref: pd.DataFrame,
    cache_raw: dict | None = None,
) -> str | None:
    """Demo-hardening Item 4: returns the matching preset name if every
    current sidebar input exactly equals that preset's values at the app's
    default settings (scripts/40_build_cache.py precomputed exactly these
    combinations), else None. Any active what-if price shock, or any
    non-default constraint/priority/risk setting, disqualifies a cache hit
    -- those combinations were never precomputed, so falling through to a
    live run is correct, not a bug.

    Phase 10: each preset now also has its own region/water_basis/
    rainfall_scenario (app/presets.py); a scenario only matches a preset if
    those three fields also match exactly, and the preset's own water
    reference (region/water_basis-specific current-mix water, looked up
    from `cache_raw["params"]` when provided) is used instead of always
    assuming Maharashtra/net_irrigation -- otherwise the 5th (Marathwada)
    preset's water_budget_m3 would never match."""
    from app.pipeline import current_mix_water
    from app.presets import (
        DEFAULT_FOOD_SHARE_MIN,
        DEFAULT_LAND_HA,
        DEFAULT_MAX_SHARE,
        DEFAULT_PRICE_MODE,
        DEFAULT_PRIORITY,
        DEFAULT_RISK_AVERSION,
        DEFAULT_SUGARCANE_RISK_MODE,
        PRESETS,
    )

    if scenario.food_share_min != DEFAULT_FOOD_SHARE_MIN or scenario.max_share != DEFAULT_MAX_SHARE:
        return None
    if scenario.price_mode != DEFAULT_PRICE_MODE:
        return None
    if abs(priority - DEFAULT_PRIORITY) > 1e-9:
        return None
    if any(m != 1.0 for m in price_multipliers.values()):
        return None
    if abs(sugarcane_frp_override - sugarcane_default_frp) > 1e-6:
        return None
    if risk_aware and (abs(risk_aversion - DEFAULT_RISK_AVERSION) > 1e-9 or sugarcane_mode != DEFAULT_SUGARCANE_RISK_MODE):
        return None

    for name, preset in PRESETS.items():
        preset_region = preset.get("region", "maharashtra")
        preset_water_basis = preset.get("water_basis", "net_irrigation")
        preset_rainfall_scenario = preset.get("rainfall_scenario", "normal")
        if scenario.region != preset_region or scenario.water_basis != preset_water_basis:
            continue
        if preset_water_basis == "net_irrigation" and scenario.rainfall_scenario != preset_rainfall_scenario:
            continue

        land_ha = float(preset["land_ha"]) if preset["land_ha"] is not None else DEFAULT_LAND_HA
        if abs(scenario.land_ha - land_ha) > 1e-6:
            continue

        if cache_raw is not None:
            ref_df = params_df_for(cache_raw, preset_region, preset_water_basis, preset_rainfall_scenario, DEFAULT_PRICE_MODE)
        else:
            ref_df = params_df_for_water_ref
        current_mix_share = cache_raw.get("current_mix_shares") if cache_raw is not None else None
        expected_water = preset["water_mult"] * current_mix_water(ref_df, land_ha, current_mix_share)
        if abs(scenario.water_budget_m3 - expected_water) <= max(1.0, expected_water * 1e-6):
            return name
    return None


def scenario_result_from_cache(
    cached: dict,
    scenario,
    weights: tuple,
    weights4: tuple | None,
    risk_aware: bool,
    Sigma: np.ndarray | None,
):
    """Reconstructs an app.pipeline.ScenarioResult from a cached preset
    result (scripts/40_build_cache.py's "preset_results" block)."""
    from app.pipeline import ScenarioResult

    if not cached["feasible"]:
        return ScenarioResult(feasible=False, message=cached.get("message"), scenario=scenario, weights=weights)

    x = {k: np.array(v, dtype=float) for k, v in cached["x"].items()}
    n_crops = len(next(iter(x.values())))
    X_front = np.array(cached["X_front"], dtype=float) if cached["X_front"] else np.empty((0, n_crops))
    F_front = np.array(cached["F_front"], dtype=float) if cached["F_front"] else np.empty((0, 3))

    return ScenarioResult(
        feasible=True,
        message=None,
        scenario=scenario,
        weights=weights,
        x=x,
        evals=cached["evals"],
        X_front=X_front,
        F_front=F_front,
        nsga_runtime=cached.get("nsga_runtime"),
        risk_aware=risk_aware,
        weights4=weights4,
        Sigma=Sigma if risk_aware else None,
        risk_aware_failed=cached.get("risk_aware_failed", False),
        from_cache=True,
    )
