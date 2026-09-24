"""Phase 7 tests: no-leakage guarantees for the decision backtest, ORACLE
upper-bound property, feasibility, and msp_history.csv citation coverage."""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from agriopt.backtest.info import (
    build_forecast_params_df,
    build_realized_params_df,
    build_risk_inputs_leakfree,
    current_mix_leakfree,
    load_msp_history,
)
from agriopt.config import CROPS, MSP_HISTORY_CSV
from agriopt.optim.baselines import evaluate
from agriopt.optim.problem import Scenario
from agriopt.optim.solvers import solve_lp_profit_max

REPO_ROOT = Path(__file__).resolve().parent.parent
TEST_YEAR = 2018  # a representative decision year (cheaper than looping all 5 for most checks)


def _load_backtest_module():
    spec = importlib.util.spec_from_file_location("backtest_60", REPO_ROOT / "scripts" / "60_backtest.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --- msp_history.csv citation coverage --------------------------------------


def test_msp_history_populated_values_have_source_url():
    df = pd.read_csv(MSP_HISTORY_CSV)
    populated = df[df["msp_rs_per_qtl"].notna() | df["cost_a2fl_rs_per_qtl"].notna()]
    missing_source = populated[populated["source_url"].isna() | (populated["source_url"] == "")]
    assert missing_source.empty, f"rows with a populated value but no source_url:\n{missing_source}"


def test_msp_history_covers_backtest_crops_and_years():
    df = pd.read_csv(MSP_HISTORY_CSV)
    for crop in CROPS:
        for year in range(2016, 2021):
            row = df[(df["crop"] == crop) & (df["year"] == year)]
            assert len(row) == 1, f"missing msp_history.csv row for ({crop}, {year})"


# --- no-leakage: yield model training window --------------------------------


@pytest.mark.parametrize("t", [2016, 2017, 2018, 2019, 2020])
def test_yield_model_trained_only_on_year_leq_t_minus_1(t):
    _, info = build_forecast_params_df(t, crops=["rice", "wheat"])
    assert info["train_max_year"] == t - 1


# --- no-leakage: price origin month is strictly before the realized harvest window ---


@pytest.mark.parametrize("t", [2016, 2018, 2020])
def test_price_origin_month_precedes_realized_harvest_window(t):
    from agriopt.optim.risk import HARVEST_WINDOW_MONTHS
    from agriopt.config import MAIN_SEASON

    _, info = build_forecast_params_df(t, crops=["rice", "wheat"])
    for crop, origin_str in info["price_origin_months"].items():
        if origin_str is None:  # sugarcane: FRP, not a mandi-price origin month
            continue
        origin = pd.Timestamp(origin_str)
        season = MAIN_SEASON[crop]
        windows = HARVEST_WINDOW_MONTHS[season]
        harvest_months = [pd.Timestamp(year=t + offset, month=month, day=1) for offset, month in windows]
        assert all(origin < h for h in harvest_months), f"{crop}: origin {origin} not strictly before harvest window {harvest_months}"


# --- no-leakage: risk Sigma's deviation matrix ------------------------------


@pytest.mark.parametrize("t", [2016, 2018, 2020])
def test_risk_sigma_deviation_matrix_only_uses_years_leq_t_minus_1(t):
    params, _ = build_forecast_params_df(t, crops=CROPS)
    R = (params["yield_qtl_ha"] * params["price"]).to_numpy(dtype=float)
    risk_inputs = build_risk_inputs_leakfree(t - 1, crops=CROPS, R=R)
    assert risk_inputs.deviation_matrix.index.max() <= t - 1


# --- ORACLE upper bound ------------------------------------------------------


def test_oracle_realized_profit_is_upper_bound():
    """Over the years/scenarios that actually have a realized outcome
    (2016-2019 -- 2020 has none, see docs/backtest.md), ORACLE's realized
    profit must be >= every other strategy's, since ORACLE optimizes profit
    directly under the realized params over an IDENTICAL feasible region
    (water/fert/land/food constraints never depend on yield/price)."""
    backtest = _load_backtest_module()
    for t in [2016, 2017, 2018, 2019]:
        rows, meta = backtest.run_year(t)
        df = pd.DataFrame(rows)
        for scenario_label, sdf in df.groupby("scenario"):
            oracle = sdf[sdf["strategy"] == "ORACLE"]["realized_profit"]
            assert len(oracle) == 1 and pd.notna(oracle.iloc[0]), f"t={t} scenario={scenario_label}: ORACLE missing"
            oracle_profit = float(oracle.iloc[0])
            for _, row in sdf.iterrows():
                if row["strategy"] == "ORACLE" or pd.isna(row["realized_profit"]):
                    continue
                tol = 1e-3 * max(1.0, abs(oracle_profit))
                assert row["realized_profit"] <= oracle_profit + tol, (
                    f"t={t} scenario={scenario_label} strategy={row['strategy']}: realized profit "
                    f"{row['realized_profit']:.2f} exceeds ORACLE's {oracle_profit:.2f}"
                )


# --- feasibility of planned allocations --------------------------------------


def test_planned_allocations_are_feasible():
    """B1 (current_mix) is EXCLUDED here on purpose: per its own docstring
    (agriopt.optim.baselines.current_mix / current_mix_leakfree), it is
    scaled to fit the LAND constraints only and is never force-fixed against
    water/food -- evaluate() reports its feasibility as-is, and it is known
    to go infeasible under a tight water budget (verified: B1/tight/2018).
    Every solver-driven strategy (B2/B3/OURS/MODEL_B/ORACLE) DOES solve
    subject to the full constraint set, so those must come back feasible."""
    backtest = _load_backtest_module()
    rows, _ = backtest.run_year(TEST_YEAR)
    for row in rows:
        if row["strategy"] == "B1":
            continue
        if row.get("feasible") is False and pd.isna(row.get("planned_profit", np.nan)):
            continue  # solver returned no solution -- not a feasibility violation, just infeasible/no-solve
        assert row["feasible"], f"strategy {row['strategy']} scenario {row['scenario']} year {row['year']} is infeasible"


def test_current_mix_leakfree_matches_land_constraints():
    params, _ = build_forecast_params_df(TEST_YEAR, crops=CROPS)
    scenario = Scenario(water_budget_m3=1e15, land_ha=10.0)
    x1 = current_mix_leakfree(params, scenario, TEST_YEAR)
    r = evaluate(x1, params, scenario)
    assert r["kharif_land"] <= scenario.land_ha + 1e-6
    assert r["rabi_land"] <= scenario.land_ha + 1e-6


# --- realized data availability sanity check ---------------------------------


def test_realized_data_missing_for_2020_confirmed():
    """Documents (and pins) the real data gap this phase's methodology
    section relies on: Maharashtra's yield_clean.parquet has zero rows for
    2020, so realized outcomes cannot be computed for that decision year."""
    _, missing_2020 = build_realized_params_df(2020, crops=CROPS)
    assert set(missing_2020) == set(CROPS)

    _, missing_2019 = build_realized_params_df(2019, crops=CROPS)
    assert missing_2019 == []
