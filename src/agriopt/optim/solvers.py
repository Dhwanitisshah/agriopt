"""Solvers for the crop allocation problem: NSGA-II (pymoo), LP profit-max
and epsilon-constraint (scipy HiGHS), an exact lexicographic LP reference
front, and a pseudo-weights recommender.
"""
from __future__ import annotations

import time

import numpy as np
import pandas as pd
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.mcdm.pseudo_weights import PseudoWeights
from pymoo.optimize import minimize as pymoo_minimize
from scipy.optimize import linprog

from agriopt.config import FOOD_CROPS
from agriopt.optim.params import build_crop_params
from agriopt.optim.problem import CropAllocationProblem, Scenario


def _lp_arrays(params_df: pd.DataFrame, scenario: Scenario):
    crops = list(params_df.index)
    profit = params_df["profit_ha"].to_numpy(dtype=float)
    water = params_df["water_m3_ha"].to_numpy(dtype=float)
    fert = params_df["fert_kg_ha"].to_numpy(dtype=float)
    kharif_mask = np.array(["kharif" in params_df.loc[c, "seasons_occupied"] for c in crops], dtype=float)
    rabi_mask = np.array(["rabi" in params_df.loc[c, "seasons_occupied"] for c in crops], dtype=float)
    food_mask = np.array([c in FOOD_CROPS for c in crops], dtype=float)
    bounds = [(0.0, scenario.max_share * scenario.land_ha) for _ in crops]

    base_A = np.vstack([kharif_mask, rabi_mask, water, -food_mask])
    base_b = np.array(
        [scenario.land_ha, scenario.land_ha, scenario.water_budget_m3, -scenario.food_share_min * scenario.land_ha]
    )
    return crops, profit, water, fert, base_A, base_b, bounds


# --- a) NSGA-II ---------------------------------------------------------------


def solve_nsga2(scenario: Scenario, params_df: pd.DataFrame | None = None, pop: int = 100, gens: int = 200, seed: int = 42):
    """Returns (X, F, runtime_seconds). F columns = [profit (positive),
    water_m3, fert_kg] -- profit is flipped back to positive for output
    (internally the problem minimizes -profit)."""
    if params_df is None:
        params_df = build_crop_params(scenario.price_mode, verbose=False)
    problem = CropAllocationProblem(params_df, scenario)
    algorithm = NSGA2(pop_size=pop)

    t0 = time.perf_counter()
    res = pymoo_minimize(problem, algorithm, ("n_gen", gens), seed=seed, verbose=False)
    runtime = time.perf_counter() - t0

    if res.X is None:
        return np.empty((0, len(params_df))), np.empty((0, 3)), runtime

    X = np.atleast_2d(res.X)
    F = np.atleast_2d(res.F).copy()
    F[:, 0] = -F[:, 0]
    return X, F, runtime


# --- b) LP profit-max -----------------------------------------------------


def solve_lp_profit_max(scenario: Scenario, params_df: pd.DataFrame | None = None):
    """Returns (x, profit) or (None, None) if infeasible."""
    if params_df is None:
        params_df = build_crop_params(scenario.price_mode, verbose=False)
    _, profit, _, _, base_A, base_b, bounds = _lp_arrays(params_df, scenario)

    res = linprog(-profit, A_ub=base_A, b_ub=base_b, bounds=bounds, method="highs")
    if not res.success:
        return None, None
    return res.x, float(profit @ res.x)


# --- c) LP epsilon-constraint (min water s.t. profit >= min_profit) -------------


def solve_lp_eps(scenario: Scenario, min_profit: float, params_df: pd.DataFrame | None = None):
    """Minimize water subject to profit >= min_profit and all other
    constraints. Returns (x, water) or (None, None) if infeasible."""
    if params_df is None:
        params_df = build_crop_params(scenario.price_mode, verbose=False)
    _, profit, water, _, base_A, base_b, bounds = _lp_arrays(params_df, scenario)

    A_ub = np.vstack([base_A, -profit])
    b_ub = np.append(base_b, -min_profit)

    res = linprog(water, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method="highs")
    if not res.success:
        return None, None
    return res.x, float(water @ res.x)


# --- d) Exact lexicographic LP reference front -----------------------------------


def exact_front_lp(scenario: Scenario, n: int = 50, params_df: pd.DataFrame | None = None):
    """Epsilon-constraint sweep over profit levels (min feasible -> max
    feasible), minimizing water at each level, then (fixing water at that
    minimum) minimizing fertilizer -- a lexicographic profit > water > fert
    reference front. Returns (X, F) with F columns [profit, water, fert],
    profit positive, same convention as solve_nsga2."""
    if params_df is None:
        params_df = build_crop_params(scenario.price_mode, verbose=False)
    crops, profit, water, fert, base_A, base_b, bounds = _lp_arrays(params_df, scenario)

    res_min = linprog(profit, A_ub=base_A, b_ub=base_b, bounds=bounds, method="highs")
    res_max = linprog(-profit, A_ub=base_A, b_ub=base_b, bounds=bounds, method="highs")
    if not (res_min.success and res_max.success):
        raise RuntimeError("exact_front_lp: base constraints are infeasible for this scenario (no allocation at all works).")

    min_profit_val = float(profit @ res_min.x)
    max_profit_val = float(profit @ res_max.x)

    X_rows, F_rows = [], []
    for p in np.linspace(min_profit_val, max_profit_val, n):
        A1 = np.vstack([base_A, -profit])
        b1 = np.append(base_b, -p)
        res_w = linprog(water, A_ub=A1, b_ub=b1, bounds=bounds, method="highs")
        if not res_w.success:
            continue
        water_p = float(water @ res_w.x)
        x_p, fert_p = res_w.x, float(fert @ res_w.x)

        A2 = np.vstack([A1, water])
        b2 = np.append(b1, water_p + 1e-6)
        res_f = linprog(fert, A_ub=A2, b_ub=b2, bounds=bounds, method="highs")
        if res_f.success:
            x_p, fert_p = res_f.x, float(fert @ res_f.x)

        X_rows.append(x_p)
        F_rows.append([float(profit @ x_p), float(water @ x_p), fert_p])

    return np.array(X_rows), np.array(F_rows)


# --- e) Recommend one solution from a Pareto front via pseudo-weights -----------


def recommend(F: np.ndarray, weights=(0.5, 0.3, 0.2)) -> int:
    """Index into F (profit-positive convention, as returned by solve_nsga2 /
    exact_front_lp) of the pseudo-weights-recommended solution. PseudoWeights
    itself operates on minimization-form F, so profit is flipped back to
    minimize-form internally before calling it."""
    F_min = np.asarray(F, dtype=float).copy()
    F_min[:, 0] = -F_min[:, 0]
    return int(PseudoWeights(np.array(weights)).do(F_min))
