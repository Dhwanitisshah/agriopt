"""Scenario orchestration for the Streamlit app: wires together the existing
Phase 3 optimizer APIs (agriopt.optim.baselines/solvers/problem) into one
call per Run click. No new modeling -- this only composes existing
build_crop_params-derived params, Scenario, and the B1/B2/B3/OURS solvers,
the same way scripts/30_run_optimizer.py does for the offline experiment.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from agriopt.optim.baselines import current_mix, evaluate, nsga2_recommended, same_profit_min_water
from agriopt.optim.problem import Scenario
from agriopt.optim.solvers import solve_lp_profit_max

NSGA_POP = 80
NSGA_GENS = 120


def weights_from_priority(t: float) -> tuple[float, float, float]:
    """t=0.0 -> all-profit end (0.8 profit / 0.6 water / 0.4 fert of the
    remainder), t=1.0 -> all-sustainability end (0.2 profit / ...), per the
    Phase 4 brief's "profit weight 0.8->0.2, water/fert split the rest
    60/40" mapping."""
    t = max(0.0, min(1.0, t))
    profit_w = 0.8 - 0.6 * t
    remainder = 1.0 - profit_w
    return (profit_w, 0.6 * remainder, 0.4 * remainder)


def current_mix_water(params_df: pd.DataFrame, land_ha: float) -> float:
    """Water usage of the historical current mix at this land size --
    price-mode independent, used as the water-budget slider's default."""
    dummy = Scenario(water_budget_m3=1e15, land_ha=land_ha)
    x1 = current_mix(params_df, dummy)
    return float(x1 @ params_df["water_m3_ha"].to_numpy())


def diagnose_infeasibility(params_df: pd.DataFrame, scenario: Scenario) -> str:
    """Called only when solve_lp_profit_max(scenario) is infeasible (which
    means the whole scenario -- and therefore NSGA-II too -- has no feasible
    allocation). Probes which constraint is binding by relaxing one at a
    time, so the app can show a plain-language st.warning instead of
    silently returning nothing or crashing."""
    huge_water = Scenario(**{**scenario.__dict__, "water_budget_m3": 1e15})
    if solve_lp_profit_max(huge_water, params_df)[0] is not None:
        return (
            f"Water budget ({scenario.water_budget_m3:,.0f} m3) is too low for the other settings "
            "(land, min food-crop share, max share per crop). Try raising the water budget, lowering "
            "the min food-crop share, or increasing the max share per crop."
        )

    no_food_min = Scenario(**{**scenario.__dict__, "food_share_min": 0.0})
    if solve_lp_profit_max(no_food_min, params_df)[0] is not None:
        return (
            f"The min food-crop share ({scenario.food_share_min:.0%}) is too high to reach given the "
            "water budget and max share per crop. Try lowering the min food-crop share, raising the "
            "water budget, or increasing the max share per crop."
        )

    full_share = Scenario(**{**scenario.__dict__, "max_share": 1.0})
    if solve_lp_profit_max(full_share, params_df)[0] is not None:
        return (
            f"The max share per crop ({scenario.max_share:.0%}) is too tight to fit the min food-crop "
            "share within the water budget. Try raising the max share per crop."
        )

    return (
        "No allocation satisfies land, water, and food-share constraints together at these settings. "
        "Try raising the water budget, lowering the min food-crop share, or increasing land."
    )


@dataclass
class ScenarioResult:
    feasible: bool
    message: str | None
    scenario: Scenario
    weights: tuple[float, float, float]
    x: dict | None = None
    evals: dict | None = None
    X_front: np.ndarray | None = None
    F_front: np.ndarray | None = None
    nsga_runtime: float | None = None


def run_pipeline(
    params_df: pd.DataFrame,
    scenario: Scenario,
    weights: tuple[float, float, float],
    pop: int = NSGA_POP,
    gens: int = NSGA_GENS,
    seed: int = 42,
) -> ScenarioResult:
    x2, _ = solve_lp_profit_max(scenario, params_df)
    if x2 is None:
        return ScenarioResult(
            feasible=False,
            message=diagnose_infeasibility(params_df, scenario),
            scenario=scenario,
            weights=weights,
        )

    x1 = current_mix(params_df, scenario)
    r1 = evaluate(x1, params_df, scenario)
    r2 = evaluate(x2, params_df, scenario)

    x3 = same_profit_min_water(params_df, scenario, min_profit=r1["profit"])
    r3 = evaluate(x3, params_df, scenario) if x3 is not None else None

    x4, X_front, F_front, runtime = nsga2_recommended(params_df, scenario, weights=weights, pop=pop, gens=gens, seed=seed)
    r4 = evaluate(x4, params_df, scenario) if x4 is not None else None

    if x4 is None:
        return ScenarioResult(
            feasible=False,
            message="The optimizer found no feasible solutions for these settings. Try relaxing a constraint.",
            scenario=scenario,
            weights=weights,
        )

    return ScenarioResult(
        feasible=True,
        message=None,
        scenario=scenario,
        weights=weights,
        x={"B1": x1, "B2": x2, "B3": x3, "OURS": x4},
        evals={"B1": r1, "B2": r2, "B3": r3, "OURS": r4},
        X_front=X_front,
        F_front=F_front,
        nsga_runtime=runtime,
    )


def pct_delta(new: float, base: float) -> float:
    if base == 0:
        return float("nan")
    return (new - base) / abs(base) * 100


def summary_sentence(r1: dict, r4: dict) -> str:
    profit_d = pct_delta(r4["profit"], r1["profit"])
    water_d = pct_delta(r4["water_m3"], r1["water_m3"])
    fert_d = pct_delta(r4["fert_kg"], r1["fert_kg"])
    return (
        f"The recommended allocation earns ₹{r4['profit']:,.0f} in profit ({profit_d:+.1f}% vs the current mix), "
        f"uses {r4['water_m3']:,.0f} m³ of water ({water_d:+.1f}%) and {r4['fert_kg']:,.0f} kg of fertilizer ({fert_d:+.1f}%), "
        f"and keeps {r4['food_share']:.0%} of land in food crops."
    )
