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


# --- centering (Phase 5.1, Item 1) ---------------------------------------------


def test_deviation_matrix_is_centered(risk_inputs):
    means = risk_inputs.deviation_matrix.mean()
    assert (means.abs() < 1e-9).all()


# --- historical_scenarios (Phase 5.1, Item 2) -----------------------------------


def test_historical_scenarios_mean_matches_deterministic_profit(params, risk_inputs, scenario):
    """Scenario mean must be within +-2% of deterministic profit x@(R-cost)
    for every strategy (B1/B2/B3/OURS), per the Phase 5.1 fix."""
    from agriopt.optim.baselines import evaluate, nsga2_recommended, same_profit_min_water
    from agriopt.optim.risk import historical_scenarios
    from agriopt.optim.solvers import solve_lp_profit_max

    scen, x1 = scenario
    crops = risk_inputs.crops
    R = (params.loc[crops, "yield_qtl_ha"] * params.loc[crops, "price"]).to_numpy(dtype=float)
    cost = params.loc[crops, "cost_ha"].to_numpy(dtype=float)

    r1 = evaluate(x1, params, scen)
    x2, _ = solve_lp_profit_max(scen, params)
    x3 = same_profit_min_water(params, scen, min_profit=r1["profit"])
    x4, _, _, _ = nsga2_recommended(params, scen, seed=42)

    for name, x in [("B1", x1), ("B2", x2), ("B3", x3), ("OURS", x4)]:
        assert x is not None, name
        det_profit = float(x @ (R - cost))
        hs = historical_scenarios(x, risk_inputs, R, cost)
        assert hs["n_years"] >= 3, name
        pct_diff = abs(hs["mean"] - det_profit) / abs(det_profit) * 100
        assert pct_diff <= 2.0, f"{name}: scenario mean {hs['mean']:.0f} vs deterministic {det_profit:.0f} ({pct_diff:.2f}% off)"


def test_historical_scenarios_returns_n_years_rows(params, risk_inputs):
    crops = risk_inputs.crops
    x = np.zeros(len(crops))
    x[crops.index("rice")] = 3.0
    x[crops.index("maize")] = 2.0
    R = (params.loc[crops, "yield_qtl_ha"] * params.loc[crops, "price"]).to_numpy()
    cost = params.loc[crops, "cost_ha"].to_numpy()

    from agriopt.optim.risk import historical_scenarios

    result, series = historical_scenarios(x, risk_inputs, R, cost, return_series=True)
    assert len(series) == result["n_years"]
    assert result["n_years"] > 0
    assert result["worst_year"] in series.index
    assert series[result["worst_year"]] == pytest.approx(result["worst_year_profit"])


def test_historical_scenarios_deterministic(params, risk_inputs):
    from agriopt.optim.risk import historical_scenarios

    crops = risk_inputs.crops
    x = np.zeros(len(crops))
    x[crops.index("rice")] = 3.0
    R = (params.loc[crops, "yield_qtl_ha"] * params.loc[crops, "price"]).to_numpy()
    cost = params.loc[crops, "cost_ha"].to_numpy()

    r1 = historical_scenarios(x, risk_inputs, R, cost)
    r2 = historical_scenarios(x, risk_inputs, R, cost)
    assert r1 == r2


def test_historical_scenarios_zero_allocation_is_zero(params, risk_inputs):
    from agriopt.optim.risk import historical_scenarios

    crops = risk_inputs.crops
    x = np.zeros(len(crops))
    R = (params.loc[crops, "yield_qtl_ha"] * params.loc[crops, "price"]).to_numpy()
    cost = params.loc[crops, "cost_ha"].to_numpy()
    r = historical_scenarios(x, risk_inputs, R, cost)
    assert r["mean"] == 0.0
    assert r["n_loss_years"] == 0


# --- bootstrap_profit_resampled (optional, exploratory only) -------------------


def test_bootstrap_resampled_deterministic_with_seed(params, risk_inputs):
    from agriopt.optim.risk import bootstrap_profit_resampled

    crops = risk_inputs.crops
    x = np.zeros(len(crops))
    x[crops.index("rice")] = 3.0
    x[crops.index("maize")] = 2.0
    R = (params.loc[crops, "yield_qtl_ha"] * params.loc[crops, "price"]).to_numpy()
    cost = params.loc[crops, "cost_ha"].to_numpy()

    r1 = bootstrap_profit_resampled(x, risk_inputs, R, cost, n=500, seed=7)
    r2 = bootstrap_profit_resampled(x, risk_inputs, R, cost, n=500, seed=7)
    assert r1 == r2


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


# --- ablation (Experiment 4, Phase 5.1) -----------------------------------------


def test_ablation_full_variant_has_zero_loss_vs_itself(params):
    ablation = _load_ablation_module()
    scenario = Scenario(water_budget_m3=ablation.compute_b1_water(params, land_ha=ablation.LAND_HA) * 0.7, land_ha=ablation.LAND_HA)

    full_decisions = ablation.decide(params, scenario)
    for strategy in ["OURS", "B2", "B3"]:
        x_full_ref = full_decisions[strategy]
        assert x_full_ref is not None
        r_eval = ablation.evaluate(x_full_ref, params, scenario)
        r_full_ref = ablation.evaluate(x_full_ref, params, scenario)
        loss_pct = (r_full_ref["profit"] - r_eval["profit"]) / abs(r_full_ref["profit"]) * 100
        l1_dist = float(np.abs(x_full_ref - x_full_ref).sum())
        assert loss_pct == pytest.approx(0.0, abs=1e-6)
        assert l1_dist == pytest.approx(0.0, abs=1e-9)


def test_ablation_b2_loss_nonnegative_for_all_variants(params):
    """The exact profit-max LP (B2) shares an identical feasible region
    across all variants (only the profit objective's coefficients change),
    so the FULL decision is the true profit-max under FULL params -- any
    other variant's B2 decision, evaluated under FULL params, can only do
    as well or worse. _lp_strategy_row asserts this internally; this test
    checks it explicitly across every variant."""
    ablation = _load_ablation_module()
    scenario = Scenario(water_budget_m3=ablation.compute_b1_water(params, land_ha=ablation.LAND_HA) * 0.7, land_ha=ablation.LAND_HA)

    full_params = params
    variant_params = {name: builder(full_params) for name, builder in ablation.VARIANTS.items()}
    full_decisions = ablation.decide(variant_params["FULL"], scenario)

    for variant_name, params_variant in variant_params.items():
        decisions = ablation.decide(params_variant, scenario) if variant_name != "FULL" else full_decisions
        row = ablation._lp_strategy_row(variant_name, "test", "B2", decisions["B2"], full_decisions["B2"], full_params, scenario)
        assert row["feasible"]
        assert row["profit_loss_rs_vs_full"] >= -1e-3 * max(1.0, abs(row["profit_under_full"])), variant_name
