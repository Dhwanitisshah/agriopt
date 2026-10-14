"""Phase 7.1: backtest fairness, water-matched oracle, and profit
decomposition -- built on Phase 7's leak-free info sets and
`scripts/60_backtest.py`'s `run_year()` (reused, not resolved a second
time). See `scripts/61_backtest_v2.py` for the orchestration that turns
these primitives into `reports/results/*_v2` outputs, and
`tests/test_backtest_v2.py` for the invariants each function must satisfy.

Nothing here writes to or mutates any Phase 7 output path -- every function
just takes params_df/x/Scenario in and returns a value/DataFrame out.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from agriopt.optim.baselines import closest_feasible_mix, evaluate
from agriopt.optim.problem import Scenario
from agriopt.optim.solvers import solve_lp_profit_max

FEASIBILITY_TOL = 1e-6
ALLOC_TOL_HA = 1e-4  # "identical allocation" tolerance for the B2-vs-ORACLE check


def b1_closest_feasible(x1: np.ndarray, params_df: pd.DataFrame, scenario: Scenario) -> tuple[np.ndarray, float, float]:
    """B1_SCALED: the allocation closest to B1 (fewest hectares moved, L1) that
    satisfies EVERY scenario constraint -- water budget, food share, season
    land, max share. It is the fair "what if the current mix had actually
    respected the constraints" baseline. The previous version scaled every
    crop down uniformly: that fixed the water budget but could never fix a
    food-share shortfall (so B1_SCALED stayed infeasible in 10/10 cells) and
    threw away land instead of swapping crops.
    Returns (x_feasible, hectares_moved, water_before). hectares_moved is 0 if
    B1 already satisfies everything; if NO allocation is feasible, B1 is
    returned unchanged with hectares_moved = nan."""
    x1 = np.asarray(x1, dtype=float)
    water_before = float(x1 @ params_df["water_m3_ha"].to_numpy(dtype=float))
    x_new, moved = closest_feasible_mix(x1, params_df, scenario)
    if x_new is None:
        return x1.copy(), float("nan"), water_before
    return x_new, moved, water_before


def oracle_water_matched(
    x: np.ndarray, forecast_params: pd.DataFrame, realized_params: pd.DataFrame, scenario: Scenario
) -> tuple[np.ndarray | None, float | None, float]:
    """ORACLE_W: "given perfect foresight AND the same water this strategy
    actually used, what's the best possible profit?" -- a perfect-foresight
    LP profit-max on REALIZED params, with the water budget replaced by x's
    OWN realized water use (water_m3_ha is a physical/agronomic property,
    not a forecast -- identical whether read off forecast_params or
    realized_params -- so "x's own water use" is unambiguous and is taken
    from forecast_params here, matching evaluate_realized_profit's own
    convention in scripts/60_backtest.py). land/food/max_share constraints
    are carried over unchanged from `scenario`. Returns
    (x_oraclew, profit_oraclew, water_used); x_oraclew/profit_oraclew are
    None only if the water-capped LP is infeasible, which should not
    happen in practice since x itself is always a feasible point at
    exactly that water level."""
    water_v = forecast_params["water_m3_ha"].to_numpy(dtype=float)
    water_used = float(np.asarray(x, dtype=float) @ water_v)
    scenario_w = Scenario(
        water_budget_m3=water_used,
        land_ha=scenario.land_ha,
        food_share_min=scenario.food_share_min,
        max_share=scenario.max_share,
        price_mode=scenario.price_mode,
    )
    x_w, _ = solve_lp_profit_max(scenario_w, realized_params)
    if x_w is None:
        return None, None, water_used
    profit_w = float(evaluate(x_w, realized_params, scenario_w)["profit"])
    return x_w, profit_w, water_used


def decompose_profit(x: np.ndarray, forecast_params: pd.DataFrame, realized_params: pd.DataFrame) -> pd.DataFrame:
    """Per-crop decomposition of (realized profit - planned profit) for
    allocation `x` into yield/price/interaction/cost effects. Algebraic
    identity (profit_i = x_i*(Y_i*P_i - C_i)):

        (Y_r*P_r - C_r) - (Y_p*P_p - C_p)
      = (Y_r-Y_p)*P_p            <- yield effect
      + Y_p*(P_r-P_p)            <- price effect
      + (Y_r-Y_p)*(P_r-P_p)      <- interaction
      - (C_r-C_p)                <- cost effect

    so summing yield_effect+price_effect+interaction+cost_effect over crops
    reproduces (realized_profit - planned_profit) EXACTLY (up to float
    error) for any x -- verified in tests/test_backtest_v2.py. Cost effect
    is expected to be exactly 0: `agriopt.backtest.info.cost_for_year(crop,
    t)` is called identically when building forecast_params and
    realized_params for the same decision year t (cost is never "revealed"
    at harvest the way yield/price are -- see docs/backtest.md section 2),
    so C_real_i == C_plan_i by construction for every crop, not merely
    approximately.

    realized_params is reindexed to forecast_params.index first -- a crop
    missing from realized_params (only happens when ALL crops are missing,
    i.e. year 2020, per docs/backtest.md) produces NaN effects for that
    crop rather than a silent 0, so callers must exclude years with any
    missing crop before relying on the identity holding numerically."""
    crops = list(forecast_params.index)
    x = np.asarray(x, dtype=float)
    realized = realized_params.reindex(crops)

    Y_plan = forecast_params["yield_qtl_ha"].to_numpy(dtype=float)
    P_plan = forecast_params["price"].to_numpy(dtype=float)
    C_plan = forecast_params["cost_ha"].to_numpy(dtype=float)
    Y_real = realized["yield_qtl_ha"].to_numpy(dtype=float)
    P_real = realized["price"].to_numpy(dtype=float)
    C_real = realized["cost_ha"].to_numpy(dtype=float)

    dY = Y_real - Y_plan
    dP = P_real - P_plan
    dC = C_real - C_plan

    yield_effect = x * dY * P_plan
    price_effect = x * Y_plan * dP
    interaction = x * dY * dP
    cost_effect = -x * dC

    return pd.DataFrame(
        {
            "crop": crops,
            "x_ha": x,
            "yield_effect_rs": yield_effect,
            "price_effect_rs": price_effect,
            "interaction_rs": interaction,
            "cost_effect_rs": cost_effect,
            "total_effect_rs": yield_effect + price_effect + interaction + cost_effect,
        }
    ).set_index("crop")
