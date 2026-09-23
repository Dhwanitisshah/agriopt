"""Solvers for the crop allocation problem: NSGA-II (pymoo), LP profit-max
and epsilon-constraint (scipy HiGHS), an exact lexicographic LP reference
front, and a pseudo-weights recommender.
"""
from __future__ import annotations

import time

import numpy as np
import pandas as pd
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.algorithms.moo.nsga3 import NSGA3
from pymoo.mcdm.pseudo_weights import PseudoWeights
from pymoo.optimize import minimize as pymoo_minimize
from pymoo.util.ref_dirs import get_reference_directions
from scipy.optimize import linprog, minimize as scipy_minimize

from agriopt.config import FOOD_CROPS
from agriopt.optim.params import build_crop_params
from agriopt.optim.problem import CropAllocationProblem, Scenario
from agriopt.optim.problem_risk import CropAllocationProblemRisk


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
    minimize-form internally before calling it. Works for any number of
    objectives (F's column count), so it's reused for Model B's 4-objective
    front too -- only column 0 (profit) needs the sign flip."""
    F_min = np.asarray(F, dtype=float).copy()
    F_min[:, 0] = -F_min[:, 0]
    return int(PseudoWeights(np.array(weights)).do(F_min))


# --- f) NSGA-III (Phase 5 Model B: profit/water/fert/risk) --------------------

NSGA3_N_PARTITIONS = 7  # -> C(7+3,3) = 120 reference directions for 4 objectives


def solve_nsga3(
    scenario: Scenario,
    params_df: pd.DataFrame,
    Sigma: np.ndarray,
    n_partitions: int = NSGA3_N_PARTITIONS,
    gens: int = 200,
    seed: int = 42,
):
    """Returns (X, F, runtime_seconds). F columns = [profit (positive),
    water_m3, fert_kg, risk_rs] -- same profit sign-flip convention as
    solve_nsga2. Population size = number of Das-Dennis reference
    directions (standard NSGA-III practice)."""
    ref_dirs = get_reference_directions("das-dennis", 4, n_partitions=n_partitions)
    problem = CropAllocationProblemRisk(params_df, scenario, Sigma)
    algorithm = NSGA3(ref_dirs=ref_dirs, pop_size=len(ref_dirs))

    t0 = time.perf_counter()
    res = pymoo_minimize(problem, algorithm, ("n_gen", gens), seed=seed, verbose=False)
    runtime = time.perf_counter() - t0

    if res.X is None:
        return np.empty((0, len(params_df))), np.empty((0, 4)), runtime

    X = np.atleast_2d(res.X)
    F = np.atleast_2d(res.F).copy()
    F[:, 0] = -F[:, 0]
    return X, F, runtime


def nsga3_recommended(
    params_df: pd.DataFrame,
    scenario: Scenario,
    Sigma: np.ndarray,
    weights=(0.4, 0.2, 0.1, 0.3),
    n_partitions: int = NSGA3_N_PARTITIONS,
    gens: int = 200,
    seed: int = 42,
):
    """Returns (x_recommended, X_front, F_front, runtime)."""
    X, F, runtime = solve_nsga3(scenario, params_df, Sigma, n_partitions=n_partitions, gens=gens, seed=seed)
    if len(X) == 0:
        return None, X, F, runtime
    idx = recommend(F, weights)
    return X[idx], X, F, runtime


# --- g) Min-risk reference (SLSQP, convex QP) ----------------------------------


def solve_min_risk(
    scenario: Scenario,
    min_profit: float,
    params_df: pd.DataFrame,
    Sigma: np.ndarray,
    max_water: float | None = None,
    n_starts: int = 5,
    seed: int = 42,
):
    """Minimize portfolio risk sqrt(x'Sigma x) subject to profit >= min_profit,
    water <= max_water (defaults to scenario.water_budget_m3), and the usual
    land/food constraints -- a convex QP (Sigma is PSD), solved with SLSQP
    from `n_starts` random feasible-region starting points (multi-start,
    since SLSQP is only guaranteed a local optimum in general, though this
    particular objective is convex so all starts should agree up to
    tolerance). Returns (x, risk) or (None, None) if infeasible."""
    if max_water is None:
        max_water = scenario.water_budget_m3

    crops, profit, water, fert, base_A, base_b, bounds = _lp_arrays(params_df, scenario)
    A = base_A.copy()
    b = base_b.copy()
    b[2] = max_water  # row order from _lp_arrays: [kharif, rabi, water, -food]

    A_full = np.vstack([A, -profit])
    b_full = np.append(b, -min_profit)

    # feasibility check via LP (cheap, avoids wasting SLSQP starts on an infeasible region)
    feas = linprog(np.zeros(len(crops)), A_ub=A_full, b_ub=b_full, bounds=bounds, method="highs")
    if not feas.success:
        return None, None

    # scale the objective for numerical conditioning -- Sigma entries are
    # ~1e6-1e9 (Rs^2) while x is O(1-10) ha, which otherwise makes SLSQP's
    # line search unreliable (spurious "positive directional derivative"
    # failures even at/near the true optimum).
    obj_scale = max(float(np.trace(Sigma)) / len(crops), 1.0)

    def objective(x):
        return float(x @ Sigma @ x) / obj_scale

    def objective_grad(x):
        return 2.0 * (Sigma @ x) / obj_scale

    constraints = [{"type": "ineq", "fun": lambda x, i=i: b_full[i] - A_full[i] @ x} for i in range(len(b_full))]

    rng = np.random.default_rng(seed)
    best_x, best_val = None, np.inf
    starts = [feas.x] + [np.array([rng.uniform(lo, hi) for lo, hi in bounds]) for _ in range(n_starts - 1)]
    for x0 in starts:
        res = scipy_minimize(
            objective,
            x0,
            jac=objective_grad,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 300, "ftol": 1e-12},
        )
        # SLSQP sometimes reports success=False ("positive directional
        # derivative") at a point that is in fact feasible and at/near the
        # optimum -- so accept on feasibility + objective improvement, not
        # on the solver's own success flag, across the multi-start pool.
        margins = b_full - A_full @ res.x
        feasible = (margins >= -1e-6).all() and (res.x >= -1e-6).all()
        if feasible and objective(res.x) < best_val:
            best_x, best_val = np.clip(res.x, 0, None), objective(res.x)

    if best_x is None:
        return None, None
    return best_x, float(np.sqrt(max(best_val * obj_scale, 0.0)))


def min_risk_profit_curve(scenario: Scenario, params_df: pd.DataFrame, Sigma: np.ndarray, n: int = 20):
    """Sweep feasible profit levels (min->max, ignoring risk) and solve
    solve_min_risk at each, at the scenario's current water budget -- a
    reference curve of min-achievable-risk vs profit, analogous in spirit to
    exact_front_lp but for the risk axis. Returns (profit_levels, risk_levels, X)."""
    crops, profit, water, fert, base_A, base_b, bounds = _lp_arrays(params_df, scenario)
    res_min = linprog(profit, A_ub=base_A, b_ub=base_b, bounds=bounds, method="highs")
    res_max = linprog(-profit, A_ub=base_A, b_ub=base_b, bounds=bounds, method="highs")
    if not (res_min.success and res_max.success):
        return np.array([]), np.array([]), []

    min_p, max_p = float(profit @ res_min.x), float(profit @ res_max.x)
    profit_levels, risk_levels, X_list = [], [], []
    for p in np.linspace(min_p, max_p, n):
        x, risk = solve_min_risk(scenario, min_profit=p, params_df=params_df, Sigma=Sigma)
        if x is None:
            continue
        profit_levels.append(p)
        risk_levels.append(risk)
        X_list.append(x)
    return np.array(profit_levels), np.array(risk_levels), X_list


# --- h) Proper 3-objective LP reference grid (Phase 5, Model A) ---------------


def exact_front_lp_grid(scenario: Scenario, params_df: pd.DataFrame, n_profit: int = 25, n_fert: int = 12):
    """A denser, non-lexicographic reference front for the 3-objective
    problem (profit, water, fert): for each of `n_profit` profit levels,
    sweep `n_fert` fertilizer caps spanning that profit level's feasible
    fert range, minimizing water at each (profit, fert-cap) combo. Unlike
    exact_front_lp (a single lexicographic profit>water>fert curve), this
    traces a 2-D grid across the Pareto SURFACE, then filters to the
    non-dominated subset -- a much better approximation of the true 3-D
    front for hypervolume/IGD comparisons. Returns (X, F) non-dominated,
    F columns = [profit, water, fert], profit positive."""
    crops, profit, water, fert, base_A, base_b, bounds = _lp_arrays(params_df, scenario)

    res_min = linprog(profit, A_ub=base_A, b_ub=base_b, bounds=bounds, method="highs")
    res_max = linprog(-profit, A_ub=base_A, b_ub=base_b, bounds=bounds, method="highs")
    if not (res_min.success and res_max.success):
        raise RuntimeError("exact_front_lp_grid: base constraints are infeasible for this scenario.")

    min_profit_val = float(profit @ res_min.x)
    max_profit_val = float(profit @ res_max.x)

    X_rows, F_rows = [], []
    for p in np.linspace(min_profit_val, max_profit_val, n_profit):
        A1 = np.vstack([base_A, -profit])
        b1 = np.append(base_b, -p)

        res_fmin = linprog(fert, A_ub=A1, b_ub=b1, bounds=bounds, method="highs")
        res_fmax = linprog(-fert, A_ub=A1, b_ub=b1, bounds=bounds, method="highs")
        if not (res_fmin.success and res_fmax.success):
            continue
        fmin_val, fmax_val = float(fert @ res_fmin.x), float(fert @ res_fmax.x)
        if fmax_val <= fmin_val:
            fert_levels = [fmin_val]
        else:
            fert_levels = np.linspace(fmin_val, fmax_val, n_fert)

        for fcap in fert_levels:
            A2 = np.vstack([A1, fert])
            b2 = np.append(b1, fcap + 1e-6)
            res_w = linprog(water, A_ub=A2, b_ub=b2, bounds=bounds, method="highs")
            if res_w.success:
                x = res_w.x
                X_rows.append(x)
                F_rows.append([float(profit @ x), float(water @ x), float(fert @ x)])

    if not F_rows:
        return np.empty((0, len(crops))), np.empty((0, 3))

    X_all = np.array(X_rows)
    F_all = np.array(F_rows)

    # non-dominated filter, minimize-form (-profit, water, fert)
    M = np.column_stack([-F_all[:, 0], F_all[:, 1], F_all[:, 2]])
    n_pts = len(M)
    dominated = np.zeros(n_pts, dtype=bool)
    for i in range(n_pts):
        if dominated[i]:
            continue
        le = np.all(M <= M[i] + 1e-9, axis=1)
        lt = np.any(M < M[i] - 1e-9, axis=1)
        dominates_i = le & lt
        if dominates_i.any():
            dominated[i] = True

    keep = ~dominated
    return X_all[keep], F_all[keep]
