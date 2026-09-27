"""Baseline allocation strategies + the shared evaluate() scorer.

B1 current_mix: historical Maharashtra area share, scaled to fit the
   scenario's land constraints. NOT force-fixed against water/food --
   evaluate() reports feasibility as-is.
B2 profit_max: LP profit maximization (solvers.solve_lp_profit_max).
B3 same_profit_min_water: LP epsilon-constraint, min water at B1's profit
   (solvers.solve_lp_eps).
OURS nsga2_recommended: pseudo-weights pick from the NSGA-II front.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from agriopt.config import CROP_NAME_MAP, FOOD_CROPS, STATE, YIELD_CLEAN_PARQUET
from agriopt.optim.problem import Scenario
from agriopt.optim.solvers import recommend, solve_lp_eps, solve_lp_profit_max, solve_nsga2

CANON_TO_YIELD_NAME = {k: v["yield"] for k, v in CROP_NAME_MAP.items()}

FEASIBILITY_TOL = 1e-6


# --- Shared scorer -------------------------------------------------------------


def evaluate(x: np.ndarray, params_df: pd.DataFrame, scenario: Scenario) -> dict:
    """Score one allocation vector x (hectares per crop, same order as
    params_df.index) against the scenario's constraints and objectives."""
    crops = list(params_df.index)
    x = np.asarray(x, dtype=float)

    profit_v = params_df["profit_ha"].to_numpy(dtype=float)
    water_v = params_df["water_m3_ha"].to_numpy(dtype=float)
    fert_v = params_df["fert_kg_ha"].to_numpy(dtype=float)
    std_v = params_df["profit_std_ha"].to_numpy(dtype=float)
    kharif_mask = np.array(["kharif" in params_df.loc[c, "seasons_occupied"] for c in crops])
    rabi_mask = np.array(["rabi" in params_df.loc[c, "seasons_occupied"] for c in crops])
    food_mask = np.array([c in FOOD_CROPS for c in crops])

    profit = float(x @ profit_v)
    water_m3 = float(x @ water_v)
    fert_kg = float(x @ fert_v)
    kharif_land = float(x[kharif_mask].sum())
    rabi_land = float(x[rabi_mask].sum())
    food_land = float(x[food_mask].sum())
    food_share = food_land / scenario.land_ha if scenario.land_ha else float("nan")
    n_crops = int((x > 0.1).sum())

    # profit_risk = sqrt(sum((x_i * profit_std_i)^2)) -- treats each crop's
    # price risk as INDEPENDENT of every other crop's (no covariance term),
    # which is almost certainly wrong in practice (monsoon-driven crops'
    # prices tend to move together), but is a simple, clearly-labeled
    # reported risk metric, not an optimization objective.
    profit_risk = float(np.sqrt(np.sum((x * std_v) ** 2)))

    feasible = (
        kharif_land <= scenario.land_ha + FEASIBILITY_TOL
        and rabi_land <= scenario.land_ha + FEASIBILITY_TOL
        and water_m3 <= scenario.water_budget_m3 + FEASIBILITY_TOL
        and food_land >= scenario.food_share_min * scenario.land_ha - FEASIBILITY_TOL
        and (x >= -FEASIBILITY_TOL).all()
        and (x <= scenario.max_share * scenario.land_ha + FEASIBILITY_TOL).all()
    )

    return {
        "profit": profit,
        "water_m3": water_m3,
        "fert_kg": fert_kg,
        "food_share": food_share,
        "n_crops": n_crops,
        "kharif_land": kharif_land,
        "rabi_land": rabi_land,
        "profit_risk": profit_risk,
        "feasible": bool(feasible),
    }


# --- B1: current mix ------------------------------------------------------------


def historical_area_share(crops: list[str], n_years: int = 5, state: str = STATE) -> dict[str, float]:
    """Extracted from current_mix() (Phase 10) so scripts/40_build_cache.py
    can precompute this once, offline, into the cache's
    "current_mix_shares" block -- the ONLY thing current_mix() needs from
    data/processed/yield_clean.parquet (gitignored, not in the app's
    committed cache). Reads the parquet directly; not for use in the app's
    own live path."""
    df = pd.read_parquet(YIELD_CLEAN_PARQUET)
    mh = df[df["state"] == state]

    raw_area = {}
    for crop in crops:
        name = CANON_TO_YIELD_NAME[crop]
        sub = mh[mh["crop"] == name]
        by_year = sub.groupby("year")["area_ha"].sum()
        recent = by_year.sort_index(ascending=False).head(n_years)
        raw_area[crop] = float(recent.mean()) if len(recent) else 0.0

    total_raw = sum(raw_area.values())
    return {c: (raw_area[c] / total_raw if total_raw > 0 else 0.0) for c in crops}


def current_mix(
    params_df: pd.DataFrame,
    scenario: Scenario,
    n_years: int = 5,
    state: str = STATE,
    precomputed_share: dict[str, float] | None = None,
) -> np.ndarray:
    """Historical Maharashtra area share (mean of each crop's last 5
    available years, summed across seasons), converted to a hectare
    allocation for `scenario.land_ha` and uniformly scaled down (if needed)
    so BOTH season totals fit within land_ha. Water/food constraints are
    NOT enforced here -- evaluate() will report if they're violated.

    Phase 10 deploy-readiness: `precomputed_share` (crop -> share in [0,1],
    summing to 1) lets a caller skip reading data/processed/yield_clean.parquet
    entirely -- this parquet is gitignored and not part of the Streamlit
    app's committed cache, so the app (via app/pipeline.py) always passes
    the share precomputed offline by scripts/40_build_cache.py instead.
    Every OTHER caller (all pre-Phase-10 scripts/tests, which run with the
    full gitignored dataset present) is unaffected: omitting this argument
    reproduces the exact same parquet read as before."""
    crops = list(params_df.index)
    if precomputed_share is not None:
        share = {c: float(precomputed_share.get(c, 0.0)) for c in crops}
    else:
        share = historical_area_share(crops, n_years=n_years, state=state)
    x_unscaled = np.array([share[c] * scenario.land_ha for c in crops])

    kharif_mask = np.array(["kharif" in params_df.loc[c, "seasons_occupied"] for c in crops])
    rabi_mask = np.array(["rabi" in params_df.loc[c, "seasons_occupied"] for c in crops])
    kharif_total = x_unscaled[kharif_mask].sum()
    rabi_total = x_unscaled[rabi_mask].sum()

    scale = 1.0
    if kharif_total > scenario.land_ha:
        scale = min(scale, scenario.land_ha / kharif_total)
    if rabi_total > scenario.land_ha:
        scale = min(scale, scenario.land_ha / rabi_total)

    return x_unscaled * scale


# --- B2 / B3 / OURS ---------------------------------------------------------------


def profit_max(params_df: pd.DataFrame, scenario: Scenario) -> np.ndarray | None:
    x, _ = solve_lp_profit_max(scenario, params_df)
    return x


def same_profit_min_water(params_df: pd.DataFrame, scenario: Scenario, min_profit: float) -> np.ndarray | None:
    x, _ = solve_lp_eps(scenario, min_profit, params_df)
    return x


def nsga2_recommended(
    params_df: pd.DataFrame, scenario: Scenario, weights=(0.5, 0.3, 0.2), pop: int = 100, gens: int = 200, seed: int = 42
) -> tuple[np.ndarray | None, np.ndarray, np.ndarray, float]:
    """Returns (x_recommended, X_front, F_front, runtime)."""
    X, F, runtime = solve_nsga2(scenario, params_df, pop=pop, gens=gens, seed=seed)
    if len(X) == 0:
        return None, X, F, runtime
    idx = recommend(F, weights)
    return X[idx], X, F, runtime
