"""The multi-objective crop allocation problem: x_i = hectares of crop i.

Objectives (pymoo minimize-form): f1 = -profit, f2 = water_m3, f3 = fert_kg.
Constraints (pymoo G <= 0 form):
  kharif land: sum(x over kharif-occupying crops) - LAND <= 0
  rabi land:   sum(x over rabi-occupying crops)   - LAND <= 0
  water:       water_m3 - WATER_BUDGET_M3 <= 0
  food:        FOOD_SHARE_MIN*LAND - sum(x over FOOD_CROPS) <= 0
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from pymoo.core.problem import Problem

from agriopt.config import FOOD_CROPS


@dataclass
class Scenario:
    water_budget_m3: float
    land_ha: float = 10.0
    food_share_min: float = 0.3
    max_share: float = 0.5
    price_mode: str = "market"
    # Phase 8: which water quantity water_m3_ha is computed from in
    # build_crop_params -- "total_need" (default, FAO TM3 total crop water
    # requirement, unchanged from Phase 1-7) or "net_irrigation" (total need
    # minus effective monsoon/season rainfall, agriopt.data.rainfall). MUST
    # default to "total_need" so every existing caller/result reproduces
    # byte-for-byte with no code changes -- see docs/water.md.
    water_basis: str = "total_need"
    # Phase 8: which rainfall scenario ("normal" 30-yr mean or "dry" 20th
    # percentile year) net_irrigation_mm() uses, when water_basis="net_irrigation".
    rainfall_scenario: str = "normal"
    # Phase 8.1: which region's own rainfall net_irrigation_mm() uses, when
    # water_basis="net_irrigation" -- "maharashtra" (default, area-weighted
    # state-wide average) or one of the 4 IMD subdivisions: "konkan",
    # "madhya_maharashtra", "marathwada", "vidarbha" (agriopt.data.rainfall.REGIONS).
    # MUST default to "maharashtra" so every existing caller/result reproduces
    # the state-wide-average behavior with no code changes -- see docs/water.md.
    region: str = "maharashtra"


class CropAllocationProblem(Problem):
    """Vectorized pymoo Problem: n_var = n_crops, n_obj = 3, n_constr = 4."""

    def __init__(self, params_df: pd.DataFrame, scenario: Scenario):
        self.crops = list(params_df.index)
        self.params = params_df
        self.scenario = scenario

        n = len(self.crops)
        xl = np.zeros(n)
        xu = np.full(n, scenario.max_share * scenario.land_ha)
        super().__init__(n_var=n, n_obj=3, n_constr=4, xl=xl, xu=xu)

        self.profit = params_df["profit_ha"].to_numpy(dtype=float)
        self.water = params_df["water_m3_ha"].to_numpy(dtype=float)
        self.fert = params_df["fert_kg_ha"].to_numpy(dtype=float)
        self.kharif_mask = np.array(["kharif" in params_df.loc[c, "seasons_occupied"] for c in self.crops])
        self.rabi_mask = np.array(["rabi" in params_df.loc[c, "seasons_occupied"] for c in self.crops])
        self.food_mask = np.array([c in FOOD_CROPS for c in self.crops])

    def _evaluate(self, X, out, *args, **kwargs):
        profit = X @ self.profit
        water = X @ self.water
        fert = X @ self.fert

        out["F"] = np.column_stack([-profit, water, fert])

        g_kharif = X[:, self.kharif_mask].sum(axis=1) - self.scenario.land_ha
        g_rabi = X[:, self.rabi_mask].sum(axis=1) - self.scenario.land_ha
        g_water = water - self.scenario.water_budget_m3
        g_food = self.scenario.food_share_min * self.scenario.land_ha - X[:, self.food_mask].sum(axis=1)

        out["G"] = np.column_stack([g_kharif, g_rabi, g_water, g_food])
