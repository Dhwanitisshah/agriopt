import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from agriopt.optim.baselines import current_mix
from agriopt.optim.params import build_crop_params
from agriopt.optim.problem import Scenario
from agriopt.optim.risk import build_risk_inputs, nearest_psd, portfolio_risk
from agriopt.optim.solvers import exact_front_lp_grid, solve_nsga3

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_ablation_module():
    spec = importlib.util.spec_from_file_location("ablation_50", REPO_ROOT / "scripts" / "50_ablation.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

TOL = 1e-6


@pytest.fixture(scope="module")
def params():
    return build_crop_params("market", verbose=False)


@pytest.fixture(scope="module")
def risk_inputs(params):
    return build_risk_inputs(params)


@pytest.fixture(scope="module")
def scenario(params):
    dummy = Scenario(water_budget_m3=1e15, land_ha=10.0)
    x1 = current_mix(params, dummy)
    b1_water = float(x1 @ params["water_m3_ha"].to_numpy())
    return Scenario(water_budget_m3=b1_water, land_ha=10.0), x1


# --- Sigma / portfolio_risk -----------------------------------------------------


def test_sigma_is_psd(risk_inputs):
    eigvals = np.linalg.eigvalsh(risk_inputs.Sigma)
    assert eigvals.min() >= -1e-6


def test_sigma_symmetric(risk_inputs):
    np.testing.assert_allclose(risk_inputs.Sigma, risk_inputs.Sigma.T, atol=1e-6)


def test_nearest_psd_clips_negative_eigenvalues():
    bad = np.array([[1.0, 2.0], [2.0, 1.0]])  # eigenvalues -1, 3 -- not PSD
    assert np.linalg.eigvalsh(bad).min() < 0
    fixed, min_eig_raw = nearest_psd(bad, min_eig=1e-8)
    assert min_eig_raw == pytest.approx(-1.0)
    assert np.linalg.eigvalsh(fixed).min() >= 0


def test_portfolio_risk_zero_at_zero_allocation(risk_inputs):
    x0 = np.zeros(len(risk_inputs.crops))
    assert portfolio_risk(x0, risk_inputs.Sigma) == pytest.approx(0.0, abs=1e-9)


def test_portfolio_risk_scales_linearly(risk_inputs):
    n = len(risk_inputs.crops)
    x1 = np.zeros(n)
    x1[0] = 3.0
    x2 = x1 * 2.5
    r1 = portfolio_risk(x1, risk_inputs.Sigma)
    r2 = portfolio_risk(x2, risk_inputs.Sigma)
    assert r2 == pytest.approx(2.5 * r1, rel=1e-6)


# --- bootstrap ---------------------------------------------------------------


def test_bootstrap_deterministic_with_seed(params, risk_inputs):
    from agriopt.optim.risk import bootstrap_profit

    crops = risk_inputs.crops
    x = np.zeros(len(crops))
    x[crops.index("rice")] = 3.0
    x[crops.index("maize")] = 2.0
    R = (params.loc[crops, "yield_qtl_ha"] * params.loc[crops, "price"]).to_numpy()
    cost = params.loc[crops, "cost_ha"].to_numpy()

    r1 = bootstrap_profit(x, risk_inputs, R, cost, n=500, seed=7)
    r2 = bootstrap_profit(x, risk_inputs, R, cost, n=500, seed=7)
    assert r1 == r2


def test_bootstrap_zero_allocation_is_zero(params, risk_inputs):
    from agriopt.optim.risk import bootstrap_profit

    crops = risk_inputs.crops
    x = np.zeros(len(crops))
    R = (params.loc[crops, "yield_qtl_ha"] * params.loc[crops, "price"]).to_numpy()
    cost = params.loc[crops, "cost_ha"].to_numpy()
    r = bootstrap_profit(x, risk_inputs, R, cost, n=100, seed=1)
    assert r["mean"] == 0.0
    assert r["P_loss"] == 0.0


# --- NSGA-III (Model B) -------------------------------------------------------


def test_nsga3_solutions_feasible(params, risk_inputs, scenario):
    scen, _ = scenario
    X, F, _ = solve_nsga3(scen, params, risk_inputs.Sigma, gens=80)
    assert len(X) > 0

    crops = list(params.index)
    kharif_mask = np.array(["kharif" in params.loc[c, "seasons_occupied"] for c in crops])
    rabi_mask = np.array(["rabi" in params.loc[c, "seasons_occupied"] for c in crops])
    water_v = params["water_m3_ha"].to_numpy(dtype=float)

    from agriopt.config import FOOD_CROPS

    food_mask = np.array([c in FOOD_CROPS for c in crops])

    for x in X:
        assert x[kharif_mask].sum() <= scen.land_ha + 1e-3
        assert x[rabi_mask].sum() <= scen.land_ha + 1e-3
        assert float(x @ water_v) <= scen.water_budget_m3 + 1e-2 * scen.water_budget_m3
        assert x[food_mask].sum() >= scen.food_share_min * scen.land_ha - 1e-3
        assert (x >= -1e-6).all()


def test_nsga3_front_has_four_objectives(params, risk_inputs, scenario):
    scen, _ = scenario
    _, F, _ = solve_nsga3(scen, params, risk_inputs.Sigma, gens=80)
    assert F.shape[1] == 4


# --- v2 reference front --------------------------------------------------------


def test_exact_front_lp_grid_is_nondominated(params, scenario):
    scen, _ = scenario
    X, F = exact_front_lp_grid(scen, params, n_profit=10, n_fert=6)
    assert len(F) > 0

    M = np.column_stack([-F[:, 0], F[:, 1], F[:, 2]])
    for i in range(len(M)):
        le = np.all(M <= M[i] + 1e-6, axis=1)
        lt = np.any(M < M[i] - 1e-6, axis=1)
        dominators = le & lt
        dominators[i] = False
        assert not dominators.any(), f"point {i} is dominated by another point in the returned front"


# --- ablation (Experiment 4) ---------------------------------------------------


def test_ablation_full_variant_has_zero_loss_vs_itself(params):
    ablation = _load_ablation_module()
    scenario = Scenario(water_budget_m3=ablation.compute_b1_water(params, land_ha=ablation.LAND_HA) * 0.7, land_ha=ablation.LAND_HA)

    full_decisions = ablation.decide(params, scenario)
    for strategy in ["OURS", "B2"]:
        x_full_ref = full_decisions[strategy]
        assert x_full_ref is not None
        r_eval = ablation.evaluate(x_full_ref, params, scenario)
        r_full_ref = ablation.evaluate(x_full_ref, params, scenario)
        loss_pct = (r_full_ref["profit"] - r_eval["profit"]) / abs(r_full_ref["profit"]) * 100
        l1_dist = float(np.abs(x_full_ref - x_full_ref).sum())
        assert loss_pct == pytest.approx(0.0, abs=1e-6)
        assert l1_dist == pytest.approx(0.0, abs=1e-9)
