"""Unit and magnitude invariants for the per-hectare economics.

These need no gitignored data or models: they run on agriopt's pure
functions and on the committed data/processed/crop_params_cache.json, so
they always run in CI. They exist because the backtest once subtracted a
Rs/quintal cost as if it were Rs/ha and nothing caught it."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from agriopt.backtest.info import _base_params_row, commit_planned_costs
from agriopt.data.reference import load_reference
from agriopt.optim.baselines import evaluate
from agriopt.optim.params import SUGARCANE_REVENUE_CV, economic_row
from agriopt.optim.problem import Scenario, food_share
from agriopt.optim.solvers import solve_lp_profit_max
from app import data as appdata
from app.pipeline import apply_price_shocks, gross_frp

REF = load_reference()


def _ref(crop, col):
    return float(REF.loc[REF["crop"] == crop, col].iloc[0])


def _all_param_records():
    raw = appdata.load_cache_raw()

    def walk(node):
        if isinstance(node, list):
            yield from node
        else:
            for v in node.values():
                yield from walk(v)

    yield from walk(raw["price_modes"])
    yield from walk(raw["params"])


# --- economic_row ------------------------------------------------------------


def test_economic_row_cost_is_per_quintal_times_yield():
    row = economic_row("rice", 20.0, 2500.0, 1500.0, 5000.0, 100.0, REF)
    assert row["cost_ha"] == pytest.approx(1500.0 * 20.0)
    assert row["profit_ha"] == pytest.approx(20.0 * 2500.0 - 30000.0)


def test_economic_row_annualizes_sugarcane_and_nets_deduction():
    cycle = _ref("sugarcane", "cycle_months")
    ded = _ref("sugarcane", "price_deduction_rs_per_qtl")
    assert cycle > 12 and ded > 0
    row = economic_row("sugarcane", 700.0, 355.0, 173.0, 20000.0, 200.0, REF)
    k = 12.0 / cycle
    assert row["yield_qtl_ha"] == pytest.approx(700.0 * k)
    assert row["water_m3_ha"] == pytest.approx(20000.0 * k)
    assert row["fert_kg_ha"] == pytest.approx(200.0 * k)
    assert row["price"] == pytest.approx(355.0 - ded)
    assert row["profit_ha"] == pytest.approx(row["yield_qtl_ha"] * row["price"] - row["cost_ha"])


# --- backtest cost-unit regression (the original bug) -------------------------


def test_backtest_row_cost_is_per_ha_not_per_quintal():
    for crop in ["rice", "tur", "sugarcane"]:
        cost_qtl = _ref(crop, "cost_rs_per_qtl")
        row = _base_params_row(crop, 25.0, 3000.0, cost_qtl, REF)
        assert row["cost_ha"] / row["yield_qtl_ha"] == pytest.approx(cost_qtl)
        assert row["cost_ha"] > 10 * cost_qtl  # Rs/ha is far larger than Rs/qtl


def test_realized_outcome_uses_planned_per_ha_cost():
    plan = pd.DataFrame({"yield_qtl_ha": [20.0], "price": [2000.0], "cost_ha": [30000.0]}, index=["rice"])
    real = pd.DataFrame({"yield_qtl_ha": [10.0], "price": [2200.0], "cost_ha": [15000.0]}, index=["rice"])
    out = commit_planned_costs(real, plan)
    assert out.loc["rice", "cost_ha"] == 30000.0
    assert out.loc["rice", "profit_ha"] == pytest.approx(10.0 * 2200.0 - 30000.0)


# --- committed cache magnitudes ----------------------------------------------


def test_cache_records_satisfy_profit_identity_and_units():
    n = 0
    for r in _all_param_records():
        n += 1
        crop = r["crop"]
        assert r["profit_ha"] == pytest.approx(r["yield_qtl_ha"] * r["price"] - r["cost_ha"], rel=1e-9, abs=1e-6)
        assert r["cost_ha"] / r["yield_qtl_ha"] == pytest.approx(_ref(crop, "cost_rs_per_qtl"), rel=1e-6)
        assert r["profit_ha"] < r["yield_qtl_ha"] * r["price"]
        assert r["profit_std_ha"] > 0, f"{crop} has zero profit risk"
    assert n > 100


def test_cache_sugarcane_is_annualized_and_net_of_ht():
    ded = _ref("sugarcane", "price_deduction_rs_per_qtl")
    for r in _all_param_records():
        if r["crop"] == "sugarcane":
            assert r["cycle_months"] == _ref("sugarcane", "cycle_months")
            assert r["price"] + ded == pytest.approx(_ref("sugarcane", "admin_price_rs_per_qtl"))
            assert r["profit_std_ha"] == pytest.approx(r["yield_qtl_ha"] * r["price"] * SUGARCANE_REVENUE_CV)


def test_cached_recommendations_are_not_sugarcane_dominated():
    """Before the economics fix sugarcane supplied 59-81% of every preset
    recommendation's profit. Guard against regressing to that."""
    raw = appdata.load_cache_raw()
    import importlib.util
    from pathlib import Path

    from app.presets import PRESETS

    spec = importlib.util.spec_from_file_location("bc", Path(__file__).resolve().parents[1] / "scripts" / "40_build_cache.py")
    bc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bc)
    for name, preset in PRESETS.items():
        res = raw["preset_results"][name]["normal"]
        assert res["feasible"], name
        df = bc._params_df_for_preset(raw["params"], preset, "market")
        x = np.array(res["x"]["OURS"])
        contrib = x * df["profit_ha"].to_numpy()
        share = contrib[list(df.index).index("sugarcane")] / contrib.sum()
        assert share < 0.5, f"{name}: sugarcane is {share:.0%} of recommended profit"
        assert 0.0 <= res["evals"]["OURS"]["food_share"] <= 1.0


# --- food-security constraint -------------------------------------------------


def _toy_params():
    return pd.DataFrame(
        {
            "profit_ha": [1.0, 1.0, 100.0],
            "water_m3_ha": [1.0, 1.0, 1.0],
            "fert_kg_ha": [1.0, 1.0, 1.0],
            "profit_std_ha": [1.0, 1.0, 1.0],
            "seasons_occupied": [{"kharif"}, {"rabi"}, {"kharif", "rabi"}],
        },
        index=["maize", "wheat", "cotton"],
    )


def test_food_share_counts_season_hectares_and_stays_in_unit_interval():
    p = _toy_params()
    sc = Scenario(water_budget_m3=1e9, land_ha=10.0, food_share_min=0.3, max_share=1.0)
    # 1.5 ha maize (kharif) + 1.5 ha wheat (rabi) + 8.5 ha cotton: 85% of each season is non-food
    x = np.array([1.5, 1.5, 8.5])
    assert food_share(x, p, 10.0) == pytest.approx(0.15)
    assert not evaluate(x, p, sc)["feasible"]
    assert food_share(np.array([10.0, 10.0, 0.0]), p, 10.0) == pytest.approx(1.0)


def test_lp_respects_season_weighted_food_minimum():
    p = _toy_params()
    sc = Scenario(water_budget_m3=1e9, land_ha=10.0, food_share_min=0.3, max_share=1.0)
    x, _ = solve_lp_profit_max(sc, p)
    assert x is not None
    assert food_share(x, p, 10.0) >= 0.3 - 1e-6
    assert evaluate(x, p, sc)["feasible"]


# --- app FRP override ---------------------------------------------------------


def test_frp_override_is_gross_and_round_trips():
    raw = appdata.load_cache_raw()
    df = pd.DataFrame(raw["price_modes"]["market"]).set_index("crop")
    df["seasons_occupied"] = df["seasons_occupied"].apply(set)
    frp = gross_frp(df)
    assert frp == pytest.approx(_ref("sugarcane", "admin_price_rs_per_qtl"))
    same = apply_price_shocks(df, {}, frp)
    pd.testing.assert_frame_equal(same, df)
    up = apply_price_shocks(df, {}, frp + 10.0)
    assert up.loc["sugarcane", "price"] == pytest.approx(df.loc["sugarcane", "price"] + 10.0)
    assert up.loc["sugarcane", "profit_ha"] == pytest.approx(df.loc["sugarcane", "profit_ha"] + 10.0 * df.loc["sugarcane", "yield_qtl_ha"])
