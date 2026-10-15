"""Committed results must not silently go stale.

The LP rows of the optimizer tables (B1, B2, B3) are cheap and exact, and every input they
need is committed: the per-crop economics (data/processed/crop_params_cache.json) and the
historical area shares. This re-solves them from the cache and diffs them against the
committed CSVs, so a change to the economics, the solvers, the B1 construction or the water
model that is not followed by re-running scripts/30_run_optimizer.py / 70_water_basis_net.py
fails CI instead of leaving yesterday's numbers in the README. Needs no gitignored data.

(OURS is NSGA-II, which is slower and seed-dependent; its guarantees are tested in test_optim.)
"""
import numpy as np
import pandas as pd
import pytest

import app.data as appdata
from agriopt.config import REPORTS_RESULTS
from agriopt.optim.baselines import current_mix, evaluate, same_profit_min_water
from agriopt.optim.problem import Scenario
from agriopt.optim.solvers import solve_lp_profit_max

LAND_HA = 10.0
MULTIPLIERS = {"tight": 0.7, "current": 1.0, "relaxed": 1.3}
RTOL = 1e-6


@pytest.fixture(scope="module")
def raw():
    return appdata.load_cache_raw()


def _scenario_rows(raw, params_by_mode, basis_kwargs):
    """Yield (water_label, price_mode, strategy, expected) re-solved from the cache."""
    share = raw["current_mix_shares"]
    base_mode = "market"
    dummy = Scenario(water_budget_m3=1e15, land_ha=LAND_HA)
    x1 = current_mix(params_by_mode[base_mode], dummy, precomputed_share=share)
    b1_water = float(x1 @ params_by_mode[base_mode]["water_m3_ha"].to_numpy())
    for label, mult in MULTIPLIERS.items():
        for mode, params in params_by_mode.items():
            scen = Scenario(water_budget_m3=mult * b1_water, land_ha=LAND_HA, price_mode=mode, **basis_kwargs)
            r1 = evaluate(x1, params, scen)
            x2, _ = solve_lp_profit_max(scen, params)
            x3 = same_profit_min_water(params, scen, min_profit=r1["profit"])
            for name, x in (("B1", x1), ("B2", x2), ("B3", x3)):
                yield label, mode, name, (evaluate(x, params, scen) if x is not None else None)


def _compare(committed: pd.DataFrame, rows, what: str):
    n = 0
    for label, mode, name, ev in rows:
        row = committed[(committed.water_scenario == label) & (committed.price_mode == mode) & (committed.strategy == name)]
        if label not in committed.water_scenario.unique():
            continue  # the _net table only has tight/current
        assert len(row) == 1, f"{what}: no committed row for {label}/{mode}/{name}"
        row = row.iloc[0]
        assert ev is not None, f"{what}: {label}/{mode}/{name} is infeasible when re-solved but committed as feasible"
        for col, got in (("profit", ev["profit"]), ("water_m3", ev["water_m3"]), ("fert_kg", ev["fert_kg"])):
            np.testing.assert_allclose(
                got, float(row[col]), rtol=RTOL,
                err_msg=f"{what} {label}/{mode}/{name}.{col}: committed {row[col]:,.2f} but re-solving the cache gives {got:,.2f} -- "
                "the committed results are stale; re-run the scripts listed in the README's Reproduce section",
            )
        n += 1
    assert n >= 12, f"{what}: only {n} rows compared"


def test_optim_strategies_csv_matches_the_cache(raw):
    params = {m: appdata.params_df_from_records(raw["price_modes"][m]) for m in ("market", "msp_floor")}
    committed = pd.read_csv(REPORTS_RESULTS / "optim_strategies.csv")
    _compare(committed, _scenario_rows(raw, params, {}), "optim_strategies.csv (total_need)")


def test_optim_strategies_net_csv_matches_the_cache(raw):
    params = {
        m: appdata.params_df_for(raw, "maharashtra", "net_irrigation", "normal", m) for m in ("market", "msp_floor")
    }
    committed = pd.read_csv(REPORTS_RESULTS / "optim_strategies_net.csv")
    basis = {"water_basis": "net_irrigation", "rainfall_scenario": "normal"}
    _compare(committed, _scenario_rows(raw, params, basis), "optim_strategies_net.csv (net irrigation)")
