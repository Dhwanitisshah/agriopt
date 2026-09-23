"""Phase 6, Item 5: "Why these crops?" -- templated, numbers-driven reasons
for the recommended allocation, plus which constraints are binding. No LLM,
no new modeling -- just reading off the same params_df / Scenario / Sigma
already used to produce the recommendation.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from agriopt.config import FOOD_CROPS
from agriopt.optim.problem import Scenario

TOL = 1e-3


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def crop_reasons(
    x: np.ndarray,
    params_df: pd.DataFrame,
    scenario: Scenario,
    Sigma: np.ndarray | None = None,
) -> dict[str, str]:
    """One templated sentence per crop with x_i > 0 hectares."""
    crops = list(params_df.index)
    profit_rank = params_df["profit_ha"].rank(ascending=False, method="min").astype(int)
    water_rank = params_df["water_m3_ha"].rank(ascending=True, method="min").astype(int)
    n_crops = len(crops)

    total_var = float(x @ Sigma @ x) if Sigma is not None else 0.0
    risk_contrib = {}
    if Sigma is not None and total_var > 1e-9:
        contrib = x * (Sigma @ x)  # Euler decomposition: sum_i contrib_i == x'Sigma x
        for i, crop in enumerate(crops):
            risk_contrib[crop] = contrib[i] / total_var

    food_land = float(x[[c in FOOD_CROPS for c in crops]].sum())
    food_binding = food_land <= scenario.food_share_min * scenario.land_ha + TOL

    reasons = {}
    for i, crop in enumerate(crops):
        ha = x[i]
        if ha <= 1e-6:
            continue
        parts = [f"{_ordinal(profit_rank[crop])} highest profit/ha ({params_df.loc[crop, 'profit_ha']:,.0f} Rs/ha)"]
        parts.append(f"{_ordinal(water_rank[crop])} lowest water need ({params_df.loc[crop, 'water_m3_ha']:,.0f} m3/ha)")
        if crop in risk_contrib:
            parts.append(f"{risk_contrib[crop]:.0%} of total portfolio risk")
        if crop in FOOD_CROPS and food_binding:
            parts.append("counts toward the (binding) minimum food-crop share")

        reasons[crop] = f"{ha:.2f} ha ({n_crops} crops total): " + "; ".join(parts) + "."

    return reasons


def binding_constraints(x: np.ndarray, params_df: pd.DataFrame, scenario: Scenario) -> list[dict]:
    """Which of the 4 constraints are at (or very near) their limit."""
    crops = list(params_df.index)
    kharif_mask = np.array(["kharif" in params_df.loc[c, "seasons_occupied"] for c in crops])
    rabi_mask = np.array(["rabi" in params_df.loc[c, "seasons_occupied"] for c in crops])
    food_mask = np.array([c in FOOD_CROPS for c in crops])
    water_v = params_df["water_m3_ha"].to_numpy(dtype=float)

    kharif_used = float(x[kharif_mask].sum())
    rabi_used = float(x[rabi_mask].sum())
    water_used = float(x @ water_v)
    food_used = float(x[food_mask].sum())
    food_limit = scenario.food_share_min * scenario.land_ha

    def binding(used, limit, tol_frac=0.01):
        return limit > 0 and used >= limit - max(TOL, tol_frac * limit)

    return [
        {"constraint": "Kharif land", "used": kharif_used, "limit": scenario.land_ha, "binding": binding(kharif_used, scenario.land_ha)},
        {"constraint": "Rabi land", "used": rabi_used, "limit": scenario.land_ha, "binding": binding(rabi_used, scenario.land_ha)},
        {"constraint": "Water budget", "used": water_used, "limit": scenario.water_budget_m3, "binding": binding(water_used, scenario.water_budget_m3)},
        {"constraint": "Min food-crop share", "used": food_used, "limit": food_limit, "binding": food_used <= food_limit + TOL if food_limit > 0 else False},
    ]
