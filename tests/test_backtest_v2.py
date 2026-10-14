"""Phase 7.1 tests: B1_SCALED water-feasibility, the profit-decomposition
identity, the water-matched ORACLE_W upper bound, and the B2<=ORACLE sanity
check. Mirrors tests/test_backtest.py's style (module-loaded via
importlib, since scripts/ isn't a package) and reuses its
`_load_backtest_module` pattern for scripts/61_backtest_v2.py too.

`run_analysis` is computed ONCE per test session (module-scoped fixture) --
it calls scripts/60_backtest.py's run_year() for every year/scenario, which
solves NSGA-II/NSGA-III internally, so recomputing it per-test would be
wasteful; every test below just asserts on the shared result.
"""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

pytestmark = pytest.mark.needs_data  # Phase 10: needs gitignored data/raw or models/*.joblib -- see pyproject.toml's marker registration

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_module(name: str, relpath: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / relpath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def backtest_v2():
    return _load_module("backtest_61_v2", "scripts/61_backtest_v2.py")


@pytest.fixture(scope="module")
def backtest_60(backtest_v2):
    return backtest_v2.load_backtest_module()


@pytest.fixture(scope="module")
def analysis(backtest_v2, backtest_60):
    fairness_df, rows_df, b2_oracle_df, decomp_df = backtest_v2.run_analysis(backtest_60)
    return {"fairness": fairness_df, "rows": rows_df, "b2_oracle": b2_oracle_df, "decomp": decomp_df}


# --- B1_SCALED feasibility ---------------------------------------------------


def test_b1_scaled_is_feasible_on_water_every_year_scenario(analysis):
    fairness_df = analysis["fairness"]
    tol = 1e-6
    over = fairness_df[fairness_df["b1_scaled_water_m3"] > fairness_df["budget_m3"] + tol]
    assert over.empty, f"B1_SCALED exceeds its own water budget in:\n{over[['year', 'scenario', 'b1_scaled_water_m3', 'budget_m3']]}"


def test_b1_scaled_water_never_exceeds_raw_b1_water(analysis):
    """B1_SCALED is only ever asked to meet a budget at or below B1's own water
    (default budget == B1's water, tight == 0.7x), so the LP-nearest feasible
    mix can't end up using more water than B1."""
    fairness_df = analysis["fairness"]
    assert (fairness_df["b1_scaled_water_m3"] <= fairness_df["b1_water_m3"] + 1e-6).all()


def test_b1_scaled_is_fully_feasible_every_year_scenario(analysis):
    """The old B1_SCALED (uniform shrink) stayed food-share-infeasible in 10/10
    cells. The LP-nearest mix must satisfy every constraint, food share included."""
    fairness_df = analysis["fairness"]
    assert fairness_df["b1_scaled_feasible"].all()
    assert not fairness_df["b1_scaled_food_share_violated"].any()


# --- decomposition identity ---------------------------------------------------


def test_decomposition_identity_holds_for_every_row(analysis):
    """Sum of yield/price/interaction/cost effects over crops must equal
    (realized_profit - planned_profit) for that strategy/year/scenario --
    this is `run_analysis`'s own internal assertion (it raises if this ever
    fails), but re-checked explicitly here at the per-(strategy,year,
    scenario) group level as a standalone, discoverable test."""
    decomp_df = analysis["decomp"]
    rows_df = analysis["rows"]
    assert len(decomp_df) > 0

    for (year, scenario, strategy), g in decomp_df.groupby(["year", "scenario", "strategy"]):
        total_effect = float(g["total_effect_rs"].sum())
        row = rows_df[(rows_df["year"] == year) & (rows_df["scenario"] == scenario) & (rows_df["strategy"] == strategy)]
        assert len(row) == 1
        planned = row.iloc[0]["planned_profit"]
        realized = row.iloc[0]["realized_profit"]
        gap = realized - planned
        tol = max(1.0, abs(gap) * 1e-6)
        assert abs(total_effect - gap) < tol, f"{year} {scenario} {strategy}: sum(effects)={total_effect} vs gap={gap}"


def test_decomposition_cost_effect_is_exactly_zero(analysis):
    """cost_for_year(crop, t) is called identically for forecast_params and
    realized_params in the same decision year -- cost effect must be
    exactly (up to float noise) zero for every row, never just 'small'."""
    decomp_df = analysis["decomp"]
    assert decomp_df["cost_effect_rs"].abs().max() < 1e-6


# --- water-matched ORACLE (ORACLE_W) upper bound ------------------------------


def test_oraclew_realized_profit_is_upper_bound(analysis):
    """ORACLE_W directly maximizes realized profit under a water budget ==
    the strategy's own realized water use, so no strategy can beat its own
    ORACLE_W in the same year/scenario."""
    rows_df = analysis["rows"]
    realized = rows_df.dropna(subset=["realized_profit", "oraclew_profit"])
    assert len(realized) > 0
    tol = realized["oraclew_profit"].abs().clip(lower=1.0) * 1e-3
    violations = realized[realized["realized_profit"] > realized["oraclew_profit"] + tol]
    assert violations.empty, f"strategy beat its own water-matched ORACLE_W:\n{violations[['year', 'scenario', 'strategy', 'realized_profit', 'oraclew_profit']]}"


def test_capture_ratio_w_at_most_one(analysis):
    rows_df = analysis["rows"]
    ratios = rows_df["capture_ratio_w"].dropna()
    assert len(ratios) > 0
    assert (ratios <= 1.0 + 1e-6).all()


# --- B2 never beats ORACLE -----------------------------------------------------


def test_b2_realized_profit_never_exceeds_oracle(analysis):
    b2_oracle_df = analysis["b2_oracle"]
    realized = b2_oracle_df.dropna(subset=["b2_realized_profit", "oracle_realized_profit"])
    assert len(realized) > 0
    tol = realized["oracle_realized_profit"].abs().clip(lower=1.0) * 1e-3
    violations = realized[realized["b2_realized_profit"] > realized["oracle_realized_profit"] + tol]
    assert violations.empty, f"B2 beat ORACLE:\n{violations[['year', 'scenario', 'b2_realized_profit', 'oracle_realized_profit']]}"


def test_b2_and_oracle_allocations_differ_in_most_cells(analysis):
    """B2 (plans on forecast profit_ha) and ORACLE (plans on realized profit_ha)
    are profit-max LPs over the same feasible region. Before the cost-unit fix
    the backtest 'profit' was ~revenue, so forecast and realized profit ranked
    crops identically and B2 == ORACLE in all 8 cells -- an artefact, not a
    finding. With real margins the two disagree in most cells, so the backtest
    can actually measure forecast skill."""
    b2_oracle_df = analysis["b2_oracle"]
    assert len(b2_oracle_df) > 0
    differing = (b2_oracle_df["max_abs_diff_ha"] > 1e-3).mean()
    assert differing > 0.5, f"B2 == ORACLE again in {1 - differing:.0%} of cells -- cost units regressed?"


# --- MSP provenance ------------------------------------------------------------


def test_msp_history_has_provenance_column_for_every_populated_row():
    import pandas as pd

    from agriopt.config import MSP_HISTORY_CSV

    df = pd.read_csv(MSP_HISTORY_CSV)
    assert "provenance" in df.columns
    populated = df[df["msp_rs_per_qtl"].notna() | df["cost_a2fl_rs_per_qtl"].notna()]
    assert (populated["provenance"] != "").all()
    assert populated["provenance"].isin(["primary", "secondary", "primary_verified_v2"]).all()


def test_msp_history_2017_kharif_trio_verified_primary():
    import pandas as pd

    from agriopt.config import MSP_HISTORY_CSV

    df = pd.read_csv(MSP_HISTORY_CSV)
    mask = (df["year"] == 2017) & (df["crop"].isin(["jowar", "soybean", "maize"]))
    rows = df[mask]
    assert len(rows) == 3
    assert (rows["provenance"] == "primary_verified_v2").all()
    assert rows["source_url"].str.contains("pib.gov.in").all()
    # values unchanged from Phase 7
    expected = {"jowar": 1700.0, "soybean": 3050.0, "maize": 1425.0}
    for _, row in rows.iterrows():
        assert float(row["msp_rs_per_qtl"]) == expected[row["crop"]]
