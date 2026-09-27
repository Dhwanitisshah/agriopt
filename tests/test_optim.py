import numpy as np
import pandas as pd
import pytest

pytestmark = pytest.mark.needs_data  # Phase 10: needs gitignored data/raw or models/*.joblib -- see pyproject.toml's marker registration

from agriopt.optim.baselines import current_mix, evaluate, nsga2_recommended, profit_max, same_profit_min_water
from agriopt.optim.params import build_crop_params
from agriopt.optim.problem import Scenario
from agriopt.optim.solvers import solve_lp_profit_max, solve_nsga2

TOL = 1e-6

RABI_CROPS = ["wheat", "sugarcane", "cotton", "tur"]


@pytest.fixture(scope="module")
def params():
    return build_crop_params("market", verbose=False)


@pytest.fixture(scope="module")
def scenario(params):
    dummy = Scenario(water_budget_m3=1e15, land_ha=10.0)
    x1 = current_mix(params, dummy)
    b1_water = float(x1 @ params["water_m3_ha"].to_numpy())
    return Scenario(water_budget_m3=b1_water, land_ha=10.0), x1


def _constraint_margins(x, params_df, scen):
    crops = list(params_df.index)
    kharif_mask = np.array(["kharif" in params_df.loc[c, "seasons_occupied"] for c in crops])
    rabi_mask = np.array(["rabi" in params_df.loc[c, "seasons_occupied"] for c in crops])
    water_v = params_df["water_m3_ha"].to_numpy(dtype=float)

    from agriopt.config import FOOD_CROPS

    food_mask = np.array([c in FOOD_CROPS for c in crops])

    kharif = x[kharif_mask].sum() - scen.land_ha
    rabi = x[rabi_mask].sum() - scen.land_ha
    water = float(x @ water_v) - scen.water_budget_m3
    food = scen.food_share_min * scen.land_ha - x[food_mask].sum()
    return kharif, rabi, water, food


def test_all_returned_solutions_satisfy_constraints(params, scenario):
    scen, x1 = scenario

    x2, _ = solve_lp_profit_max(scen, params)
    x3 = same_profit_min_water(params, scen, min_profit=evaluate(x1, params, scen)["profit"])
    x4, X_front, F_front, _ = nsga2_recommended(params, scen)

    for label, x in [("B2", x2), ("B3", x3), ("OURS", x4)]:
        assert x is not None, f"{label} infeasible"
        for g in _constraint_margins(x, params, scen):
            assert g <= TOL, f"{label} violates a constraint: margins={_constraint_margins(x, params, scen)}"

    for i, x in enumerate(X_front):
        for g in _constraint_margins(x, params, scen):
            assert g <= 1e-4, f"NSGA-II front point {i} violates a constraint"


def test_b2_profit_dominates_nsga2_front(params, scenario):
    scen, _ = scenario
    _, b2_profit = solve_lp_profit_max(scen, params)
    _, F_front, _ = solve_nsga2(scen, params)

    assert b2_profit is not None
    if len(F_front):
        max_nsga_profit = F_front[:, 0].max()
        assert b2_profit >= max_nsga_profit - 1e-2 * max(1.0, abs(max_nsga_profit))


def test_b3_matches_b1_profit_with_less_or_equal_water(params, scenario):
    scen, x1 = scenario
    r1 = evaluate(x1, params, scen)
    x3 = same_profit_min_water(params, scen, min_profit=r1["profit"])
    assert x3 is not None
    r3 = evaluate(x3, params, scen)

    assert r3["profit"] >= r1["profit"] - 1e-3 * max(1.0, abs(r1["profit"]))
    assert r3["water_m3"] <= r1["water_m3"] + 1e-3 * max(1.0, r1["water_m3"])


def test_nsga2_deterministic_with_fixed_seed(params, scenario):
    scen, _ = scenario
    X1, F1, _ = solve_nsga2(scen, params, seed=7)
    X2, F2, _ = solve_nsga2(scen, params, seed=7)

    np.testing.assert_allclose(X1, X2)
    np.testing.assert_allclose(F1, F2)


def test_rabi_constraint_wheat_sugarcane_cotton_tur(params, scenario):
    scen, x1 = scenario
    crops = list(params.index)
    rabi_idx = [crops.index(c) for c in RABI_CROPS]

    x2, _ = solve_lp_profit_max(scen, params)
    x3 = same_profit_min_water(params, scen, min_profit=evaluate(x1, params, scen)["profit"])
    x4, X_front, _, _ = nsga2_recommended(params, scen)

    for label, x in [("B1", x1), ("B2", x2), ("B3", x3), ("OURS", x4)]:
        assert x is not None, label
        assert x[rabi_idx].sum() <= scen.land_ha + 1e-4, f"{label} violates rabi land constraint"

    for x in X_front:
        assert x[rabi_idx].sum() <= scen.land_ha + 1e-3


def test_toy_2crop_analytical_optimum():
    """toyA: 100 profit/ha, toyB: 50 profit/ha, both need 'kharif' land,
    water/food unconstrained (huge budget / zero minimum) -> the unique
    optimum under a single land<=10 constraint is all-in on toyA:
    x=(10, 0), profit=1000."""
    toy_params = pd.DataFrame(
        {
            "profit_ha": [100.0, 50.0],
            "water_m3_ha": [10.0, 5.0],
            "fert_kg_ha": [1.0, 1.0],
            "seasons_occupied": [{"kharif"}, {"kharif"}],
        },
        index=["toyA", "toyB"],
    )
    toy_scenario = Scenario(water_budget_m3=1e6, land_ha=10.0, food_share_min=0.0, max_share=1.0)

    x_lp, profit_lp = solve_lp_profit_max(toy_scenario, toy_params)
    assert x_lp is not None
    np.testing.assert_allclose(x_lp, [10.0, 0.0], atol=1e-6)
    assert profit_lp == pytest.approx(1000.0, abs=1e-6)

    X_front, F_front, _ = solve_nsga2(toy_scenario, toy_params, pop=50, gens=100, seed=0)
    best_idx = F_front[:, 0].argmax()
    x_nsga = X_front[best_idx]
    assert x_nsga[0] == pytest.approx(10.0, rel=0.02)
    assert x_nsga[1] == pytest.approx(0.0, abs=0.2)
    assert F_front[best_idx, 0] == pytest.approx(1000.0, rel=0.02)
