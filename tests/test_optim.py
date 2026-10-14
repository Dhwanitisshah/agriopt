import numpy as np
import pandas as pd
import pytest

# needs_data is applied per test (not module-wide) so the data-free toy
# test below still runs in CI.
needs_data = pytest.mark.needs_data

from agriopt.optim.baselines import (
    closest_feasible_mix,
    current_mix,
    evaluate,
    mix_from_shares,
    nsga2_recommended,
    profit_max,
    same_profit_min_water,
)
from agriopt.optim.params import build_crop_params
from agriopt.optim.problem import Scenario
from agriopt.optim.solvers import _lp_arrays, polish_front, solve_lp_profit_max, solve_nsga2

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


@needs_data
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


@needs_data
def test_b2_profit_dominates_nsga2_front(params, scenario):
    scen, _ = scenario
    _, b2_profit = solve_lp_profit_max(scen, params)
    _, F_front, _ = solve_nsga2(scen, params)

    assert b2_profit is not None
    if len(F_front):
        max_nsga_profit = F_front[:, 0].max()
        assert b2_profit >= max_nsga_profit - 1e-2 * max(1.0, abs(max_nsga_profit))


@needs_data
def test_b3_matches_b1_profit_with_less_or_equal_water(params, scenario):
    scen, x1 = scenario
    r1 = evaluate(x1, params, scen)
    x3 = same_profit_min_water(params, scen, min_profit=r1["profit"])
    assert x3 is not None
    r3 = evaluate(x3, params, scen)

    assert r3["profit"] >= r1["profit"] - 1e-3 * max(1.0, abs(r1["profit"]))
    assert r3["water_m3"] <= r1["water_m3"] + 1e-3 * max(1.0, r1["water_m3"])


@needs_data
def test_nsga2_deterministic_with_fixed_seed(params, scenario):
    scen, _ = scenario
    X1, F1, _ = solve_nsga2(scen, params, seed=7)
    X2, F2, _ = solve_nsga2(scen, params, seed=7)

    np.testing.assert_allclose(X1, X2)
    np.testing.assert_allclose(F1, F2)


@needs_data
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


def _lp_profit_at_caps(params_df, scen, water_cap, fert_cap):
    """Exact max profit over every allocation that uses <= water_cap and <= fert_cap."""
    from scipy.optimize import linprog

    _, profit, _, fert, A, b, bounds = _lp_arrays(params_df, scen)
    b = b.copy()
    b[2] = min(b[2], water_cap)
    r = linprog(-profit, A_ub=np.vstack([A, fert]), b_ub=np.append(b, fert_cap), bounds=bounds, method="highs")
    assert r.success
    return -r.fun


@needs_data
@pytest.mark.parametrize("water_mult", [0.7, 1.0, 1.3])
def test_ours_is_not_dominated_by_an_lp_at_same_water_and_fert(params, scenario, water_mult):
    """The problem has 3 LINEAR objectives, so a raw NSGA-II point is generically
    dominated by the LP optimum at its own water and fertilizer. The recommendation
    must be LP-polished: no allocation using <= OURS water and <= OURS fert earns
    strictly more profit."""
    base, _ = scenario
    scen = Scenario(water_budget_m3=base.water_budget_m3 * water_mult, land_ha=base.land_ha)
    x4, _, _, _ = nsga2_recommended(params, scen)
    r = evaluate(x4, params, scen)
    assert r["feasible"]
    best = _lp_profit_at_caps(params, scen, r["water_m3"] * (1 + 1e-6), r["fert_kg"] * (1 + 1e-6))
    assert best <= r["profit"] * (1 + 1e-6) + 1e-3, f"LP earns {best:,.0f} vs OURS {r['profit']:,.0f} at same water+fert"


def test_polish_front_lifts_dominated_points_to_the_lp_frontier():
    toy_params = pd.DataFrame(
        {
            "profit_ha": [100.0, 60.0, 30.0],
            "water_m3_ha": [10.0, 4.0, 1.0],
            "fert_kg_ha": [5.0, 2.0, 1.0],
            "seasons_occupied": [{"kharif"}, {"kharif"}, {"kharif"}],
        },
        index=["a", "b", "c"],
    )
    scen = Scenario(water_budget_m3=1e6, land_ha=10.0, food_share_min=0.0, max_share=1.0)
    # a deliberately sloppy "NSGA-II" point: 3 ha of a + 3 ha of b, 4 ha idle
    x_raw = np.array([[3.0, 3.0, 0.0]])
    F_raw = np.array([[3 * 100 + 3 * 60, 3 * 10 + 3 * 4, 3 * 5 + 3 * 2]], dtype=float)

    X, F = polish_front(x_raw, F_raw, scen, toy_params)

    assert len(X) == 1
    assert F[0, 1] <= F_raw[0, 1] + 1e-6 and F[0, 2] <= F_raw[0, 2] + 1e-6  # never uses more water or fert
    assert F[0, 0] > F_raw[0, 0] + 1.0  # but earns more
    best = _lp_profit_at_caps(toy_params, scen, F_raw[0, 1] * (1 + 1e-6), F_raw[0, 2] * (1 + 1e-6))
    assert F[0, 0] == pytest.approx(best, rel=1e-6)


def _season_toy():
    """kharif-only A, rabi-only B, both-season C."""
    params = pd.DataFrame(
        {
            "profit_ha": [100.0, 80.0, 60.0],
            "water_m3_ha": [10.0, 4.0, 8.0],
            "fert_kg_ha": [1.0, 1.0, 1.0],
            "seasons_occupied": [{"kharif"}, {"rabi"}, {"kharif", "rabi"}],
        },
        index=["A", "B", "C"],
    )
    return params


def test_mix_from_shares_fills_each_season_from_its_own_crops():
    """A(kharif) .3, B(rabi) .2, C(both) .5 -> kharif area .8, rabi .7. The
    both-season crop is fixed at its share of the LARGER season (.5/.8 of the
    land); each single-season crop fills the rest of ITS season. The old
    all-crops normalisation gave x = (3, 2, 5): kharif 8 ha, rabi 7 ha."""
    params = _season_toy()
    scen = Scenario(water_budget_m3=1e9, land_ha=10.0, food_share_min=0.0, max_share=1.0)
    x = mix_from_shares({"A": 0.3, "B": 0.2, "C": 0.5}, params, scen)
    np.testing.assert_allclose(x, [3.75, 3.75, 6.25])
    assert x[0] + x[2] == pytest.approx(10.0)  # kharif land fully used
    assert x[1] + x[2] == pytest.approx(10.0)  # rabi land fully used


def test_closest_feasible_mix_moves_the_fewest_hectares():
    params = _season_toy()
    x_cur = np.array([3.75, 3.75, 6.25])
    # current water use = 37.5 + 15 + 50 = 102.5; ask for 80 -> must shed >= 22.5 m3
    scen = Scenario(water_budget_m3=80.0, land_ha=10.0, food_share_min=0.0, max_share=1.0)
    x, moved = closest_feasible_mix(x_cur, params, scen)
    assert x is not None
    assert float(x @ params["water_m3_ha"].to_numpy()) <= 80.0 + 1e-6
    assert moved == pytest.approx(float(np.abs(x - x_cur).sum()))
    # the cheapest way to shed 22.5 m3 is swapping A (10 m3/ha) out of kharif for C... C also
    # costs water, so the only lever is idling A: 22.5 / 10 = 2.25 ha of A moved.
    assert moved == pytest.approx(2.25, abs=1e-6)
    # a feasible current mix is returned untouched
    easy = Scenario(water_budget_m3=1e9, land_ha=10.0, food_share_min=0.0, max_share=1.0)
    x_same, moved_same = closest_feasible_mix(x_cur, params, easy)
    np.testing.assert_allclose(x_same, x_cur, atol=1e-9)
    assert moved_same == pytest.approx(0.0, abs=1e-9)
    # an impossible scenario reports it instead of returning something infeasible
    assert closest_feasible_mix(x_cur, params, Scenario(water_budget_m3=-1.0, land_ha=10.0, food_share_min=0.0, max_share=1.0)) == (None, None)


@needs_data
def test_current_mix_uses_all_land_and_closest_feasible_meets_every_constraint(params):
    dummy = Scenario(water_budget_m3=1e15, land_ha=10.0)
    x1 = current_mix(params, dummy)
    r1 = evaluate(x1, params, dummy)
    assert r1["kharif_land"] == pytest.approx(10.0, rel=1e-6)
    assert r1["rabi_land"] == pytest.approx(10.0, rel=1e-6)

    tight = Scenario(water_budget_m3=0.7 * r1["water_m3"], land_ha=10.0)
    xf, moved = closest_feasible_mix(x1, params, tight)
    assert xf is not None and evaluate(xf, params, tight)["feasible"]
    # and it moves fewer hectares than uniformly shrinking B1 to the water budget would
    uniform = x1 * (tight.water_budget_m3 / r1["water_m3"])
    assert moved <= float(np.abs(uniform - x1).sum()) + 1e-6


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
