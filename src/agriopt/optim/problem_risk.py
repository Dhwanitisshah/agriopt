"""Phase 5 Model B: the 4-objective crop allocation problem (adds a
portfolio-risk objective to problem.CropAllocationProblem's 3).

Objectives (pymoo minimize-form): f1 = -profit, f2 = water_m3, f3 = fert_kg,
f4 = portfolio_risk(x) = sqrt(x' Sigma x)  (nonlinear, from agriopt.optim.risk).
Constraints: identical to CropAllocationProblem (kharif/rabi land, water,
food share) -- risk is an objective here, not a constraint.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from pymoo.core.problem import Problem

from agriopt.config import FOOD_CROPS
from agriopt.optim.problem import Scenario
from agriopt.optim.risk import portfolio_risk_vectorized


class CropAllocationProblemRisk(Problem):
    """Vectorized pymoo Problem: n_var = n_crops, n_obj = 4, n_constr = 4."""

    def __init__(self, params_df: pd.DataFrame, scenario: Scenario, Sigma: np.ndarray):
        self.crops = list(params_df.index)
        self.params = params_df
        self.scenario = scenario
        self.Sigma = Sigma

        n = len(self.crops)
        xl = np.zeros(n)
        xu = np.full(n, scenario.max_share * scenario.land_ha)
        super().__init__(n_var=n, n_obj=4, n_constr=4, xl=xl, xu=xu)

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
        risk = portfolio_risk_vectorized(X, self.Sigma)

        out["F"] = np.column_stack([-profit, water, fert, risk])

        g_kharif = X[:, self.kharif_mask].sum(axis=1) - self.scenario.land_ha
        g_rabi = X[:, self.rabi_mask].sum(axis=1) - self.scenario.land_ha
        g_water = water - self.scenario.water_budget_m3
        g_food = self.scenario.food_share_min * self.scenario.land_ha - X[:, self.food_mask].sum(axis=1)

        out["G"] = np.column_stack([g_kharif, g_rabi, g_water, g_food])
