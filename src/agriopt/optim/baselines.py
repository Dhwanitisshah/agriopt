"""Baseline allocation strategies + the shared evaluate() scorer.

B1 current_mix: the historical Maharashtra crop mix built per SEASON (see
   mix_from_shares), so it uses the farm's land as fully as the other
   strategies can. NOT force-fixed against water/food -- evaluate() reports
   feasibility as-is. closest_feasible_mix() is the fair feasible version: the
   LP-nearest allocation to B1 that meets every scenario constraint.
B2 profit_max: LP profit maximization (solvers.solve_lp_profit_max).
B3 same_profit_min_water: LP epsilon-constraint, min water at B1's profit
   (solvers.solve_lp_eps).
OURS nsga2_recommended: pseudo-weights pick from the NSGA-II front after every
   point is LP-polished (profit, water, fert are all linear, so a raw NSGA-II
   point is dominated by the LP optimum at the same water and fertilizer).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from agriopt.config import CROP_NAME_MAP, STATE, YIELD_CLEAN_PARQUET
from agriopt.optim.problem import Scenario, food_requirement, food_share as food_share_of, food_weights
from agriopt.optim.solvers import (
    polish_front,
    recommend,
    solve_lp_closest,
    solve_lp_eps,
    solve_lp_profit_max,
    solve_nsga2,
)

CANON_TO_YIELD_NAME = {k: v["yield"] for k, v in CROP_NAME_MAP.items()}

FEASIBILITY_TOL = 1e-6


# --- Shared scorer -------------------------------------------------------------


def evaluate(x: np.ndarray, params_df: pd.DataFrame, scenario: Scenario, Sigma: np.ndarray | None = None) -> dict:
    """Score one allocation vector x (hectares per crop, same order as
    params_df.index) against the scenario's constraints and objectives.

    `Sigma` (crops x crops revenue covariance, Rs^2, same order as params_df)
    makes `profit_risk` the real portfolio risk sqrt(x' Sigma x), which counts
    the crops' co-movement (rice and soybean prices rise and fall together, so
    diversifying across them buys less than independence suggests). Without
    it `profit_risk` falls back to the independent-crops figure -- an
    UNDERSTATEMENT of risk for concentrated, correlated plans -- so callers
    that show risk to a user should pass Sigma."""
    crops = list(params_df.index)
    x = np.asarray(x, dtype=float)

    profit_v = params_df["profit_ha"].to_numpy(dtype=float)
    water_v = params_df["water_m3_ha"].to_numpy(dtype=float)
    fert_v = params_df["fert_kg_ha"].to_numpy(dtype=float)
    std_v = params_df["profit_std_ha"].to_numpy(dtype=float)
    kharif_mask = np.array(["kharif" in params_df.loc[c, "seasons_occupied"] for c in crops])
    rabi_mask = np.array(["rabi" in params_df.loc[c, "seasons_occupied"] for c in crops])
    food_w = food_weights(params_df)

    profit = float(x @ profit_v)
    water_m3 = float(x @ water_v)
    fert_kg = float(x @ fert_v)
    kharif_land = float(x[kharif_mask].sum())
    rabi_land = float(x[rabi_mask].sum())
    food_season_ha = float(x @ food_w)
    food_share = food_share_of(x, params_df, scenario.land_ha)
    n_crops = int((x > 0.1).sum())

    if Sigma is not None:
        profit_risk = float(np.sqrt(max(float(x @ np.asarray(Sigma, dtype=float) @ x), 0.0)))
    else:
        # fallback: sqrt(sum((x_i * profit_std_i)^2)) treats each crop's price
        # risk as INDEPENDENT of every other crop's (no covariance term).
        profit_risk = float(np.sqrt(np.sum((x * std_v) ** 2)))

    feasible = (
        kharif_land <= scenario.land_ha + FEASIBILITY_TOL
        and rabi_land <= scenario.land_ha + FEASIBILITY_TOL
        and water_m3 <= scenario.water_budget_m3 + FEASIBILITY_TOL
        and food_season_ha >= food_requirement(scenario) - FEASIBILITY_TOL
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


def historical_area_share(
    crops: list[str], n_years: int = 5, state: str = STATE, max_year: int | None = None
) -> dict[str, float]:
    """Extracted from current_mix() (Phase 10) so scripts/40_build_cache.py
    can precompute this once, offline, into the cache's
    "current_mix_shares" block -- the ONLY thing current_mix() needs from
    data/processed/yield_clean.parquet (gitignored, not in the app's
    committed cache). Reads the parquet directly; not for use in the app's
    own live path.

    Returns each crop's share of the summed 5-year-mean area (shares sum to
    1). Only the RATIOS matter to mix_from_shares. `max_year` restricts the
    rows used (the backtest passes t-1 so early decision years can't see
    their own future)."""
    df = pd.read_parquet(YIELD_CLEAN_PARQUET)
    mh = df[df["state"] == state]
    if max_year is not None:
        mh = mh[mh["year"] <= max_year]

    raw_area = {}
    for crop in crops:
        name = CANON_TO_YIELD_NAME[crop]
        sub = mh[mh["crop"] == name]
        by_year = sub.groupby("year")["area_ha"].sum()
        recent = by_year.sort_index(ascending=False).head(n_years)
        raw_area[crop] = float(recent.mean()) if len(recent) else 0.0

    total_raw = sum(raw_area.values())
    return {c: (raw_area[c] / total_raw if total_raw > 0 else 0.0) for c in crops}


def mix_from_shares(share: dict[str, float], params_df: pd.DataFrame, scenario: Scenario) -> np.ndarray:
    """Hectare allocation for the farm that mirrors the state's historical
    crop mix, built per season.

    The old construction normalised every crop's area over ALL crops, so the
    farm filled only ~76% of its kharif and ~62% of its rabi land (a crop in
    both seasons was counted once in the denominator but twice in the land
    use) and B1 looked worse than any strategy allowed to use all its land.
    Here:
      * a crop that occupies BOTH seasons (cotton, sugarcane, tur) is fixed
        at its historical share of the LARGER season's cropped area -- its
        hectares count in both seasons, so it is set explicitly, once;
      * single-season crops fill the REST of their own season's land in
        proportion to their historical areas (kharif crops normalised over
        kharif area, rabi over rabi).
    Both seasons end up fully used whenever they have a single-season crop.
    Water/food are NOT enforced (see closest_feasible_mix)."""
    crops = list(params_df.index)
    a = np.array([float(share.get(c, 0.0)) for c in crops])
    kharif = np.array(["kharif" in params_df.loc[c, "seasons_occupied"] for c in crops])
    rabi = np.array(["rabi" in params_df.loc[c, "seasons_occupied"] for c in crops])
    both = kharif & rabi
    land = scenario.land_ha

    biggest_season = max(a[kharif].sum(), a[rabi].sum())
    x = np.zeros(len(crops))
    if biggest_season <= 0:
        return x
    x[both] = land * a[both] / biggest_season
    remaining = max(land - x[both].sum(), 0.0)
    for only in (kharif & ~rabi, rabi & ~kharif):
        if a[only].sum() > 0:
            x[only] = remaining * a[only] / a[only].sum()
    return x


def current_mix(
    params_df: pd.DataFrame,
    scenario: Scenario,
    n_years: int = 5,
    state: str = STATE,
    precomputed_share: dict[str, float] | None = None,
) -> np.ndarray:
    """B1: the historical Maharashtra crop mix (mean of each crop's last 5
    available years' area) as a hectare allocation for `scenario.land_ha`,
    built per season by mix_from_shares. Water/food constraints are NOT
    enforced here -- evaluate() reports if they're violated, and
    closest_feasible_mix() gives the feasible version.

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
    return mix_from_shares(share, params_df, scenario)


def closest_feasible_mix(
    x_current: np.ndarray, params_df: pd.DataFrame, scenario: Scenario
) -> tuple[np.ndarray | None, float | None]:
    """B1 made feasible: the allocation meeting every scenario constraint
    (water budget, food share, season land, max share) that moves the fewest
    hectares away from `x_current`. Replaces uniformly shrinking B1, which
    kept every crop's ratio but could not fix a food-share shortfall and
    cut high- and low-water crops alike. Returns (x, hectares_moved) or
    (None, None) if the scenario is infeasible for every allocation."""
    return solve_lp_closest(scenario, params_df, x_current)


# --- B2 / B3 / OURS ---------------------------------------------------------------


def profit_max(params_df: pd.DataFrame, scenario: Scenario) -> np.ndarray | None:
    x, _ = solve_lp_profit_max(scenario, params_df)
    return x


def same_profit_min_water(params_df: pd.DataFrame, scenario: Scenario, min_profit: float) -> np.ndarray | None:
    x, _ = solve_lp_eps(scenario, min_profit, params_df)
    return x


def nsga2_recommended(
    params_df: pd.DataFrame,
    scenario: Scenario,
    weights=(0.5, 0.3, 0.2),
    pop: int = 100,
    gens: int = 200,
    seed: int = 42,
    polish: bool = True,
) -> tuple[np.ndarray | None, np.ndarray, np.ndarray, float]:
    """Returns (x_recommended, X_front, F_front, runtime).

    With `polish=True` (default) the NSGA-II front is LP-polished before the
    pseudo-weights pick (see solvers.polish_front), so the recommendation --
    and the front returned for display -- are Pareto-efficient rather than
    merely the best NSGA-II found in `gens` generations. `polish=False` gives
    the raw heuristic front. runtime covers the NSGA-II search only."""
    X, F, runtime = solve_nsga2(scenario, params_df, pop=pop, gens=gens, seed=seed)
    if len(X) == 0:
        return None, X, F, runtime
    if polish:
        X, F = polish_front(X, F, scenario, params_df)
    idx = recommend(F, weights)
    return X[idx], X, F, runtime
