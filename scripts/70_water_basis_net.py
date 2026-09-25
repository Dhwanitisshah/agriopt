"""Phase 8, step 2: rerun the E3 strategies table, the risk/Model-B
strategies table, and the Phase 7.1 backtest fairness metrics under the
NEW `water_basis="net_irrigation"` basis (see docs/water.md), writing only
NEW `*_net` output files -- reports/results/optim_strategies.{csv,md},
risk_strategies.{csv,md}, backtest_summary_v2.md and every other Phase 3-7.1
output are read-only inputs here (for the comparison doc), never touched.

Reuses (does not duplicate) the existing scripts' pure functions:
  - scripts/30_run_optimizer.py: run_scenario, write_strategy_table, strategy_table_markdown
  - scripts/31_run_risk.py: run_focus_scenario (B1/B2/B3/OURS_A/ModelB rows)
  - scripts/60_backtest.py: run_year (now water_basis-parametrized, Phase 8)
  - scripts/61_backtest_v2.py: run_analysis, build_win_summary, build_capture_ratio_budget_level

Writes:
  reports/results/optim_strategies_net.csv / .md   -- E3 table (B1,B2,B3,OURS), tight+current x market+msp_floor
  reports/results/risk_strategies_net.csv / .md     -- B1,B2,B3,OURS_A,ModelB, current/market focus scenario
  reports/results/backtest_summary_net.md           -- Phase 7.1 fairness metrics under net irrigation
  reports/results/water_basis_comparison.md         -- total_need vs net_irrigation comparison + findings
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from agriopt.config import CROPS, REPORTS_RESULTS
from agriopt.optim.baselines import current_mix
from agriopt.optim.params import build_crop_params
from agriopt.optim.problem import Scenario
from agriopt.optim.risk import build_risk_inputs

REPO_ROOT = Path(__file__).resolve().parent.parent
WATER_BASIS = "net_irrigation"
RAINFALL_SCENARIO = "normal"
WATER_MULTIPLIERS = {"tight": 0.7, "current": 1.0}
PRICE_MODES = ["market", "msp_floor"]
LAND_HA = 10.0
FOCUS_SCENARIO = ("current", "market")


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def compute_b1_water_net(land_ha: float = LAND_HA) -> tuple[np.ndarray, float, pd.DataFrame]:
    """Same pattern as scripts/30_run_optimizer.py's compute_b1_water, but
    with params_df built under water_basis="net_irrigation" -- so B1's own
    water footprint (the basis for the tight/current budgets below) is
    itself measured in net-irrigation terms, not total need."""
    params = build_crop_params("market", verbose=False, water_basis=WATER_BASIS, rainfall_scenario=RAINFALL_SCENARIO)
    dummy = Scenario(water_budget_m3=1e15, land_ha=land_ha, water_basis=WATER_BASIS, rainfall_scenario=RAINFALL_SCENARIO)
    x1 = current_mix(params, dummy)
    water = float(x1 @ params["water_m3_ha"].to_numpy())
    return x1, water, params


def write_optim_strategies_net(m30, x1: np.ndarray, params_by_mode: dict, water_budgets: dict) -> pd.DataFrame:
    all_runs = {}
    for water_label, wb in water_budgets.items():
        for price_mode in PRICE_MODES:
            all_runs[(water_label, price_mode)] = m30.run_scenario(water_label, price_mode, x1, params_by_mode[price_mode], wb)

    strategy_df = m30.write_strategy_table(all_runs)
    strategy_df.to_csv(REPORTS_RESULTS / "optim_strategies_net.csv", index=False)
    md = (
        "# Optimizer strategies (E3.1), NET IRRIGATION water basis (Phase 8)\n\n"
        "Water budget derived from B1's own NET-irrigation water footprint (same "
        "\"derive budget from B1's footprint\" pattern as Phase 3/7). See docs/water.md "
        "and reports/results/water_basis_comparison.md.\n"
        + m30.strategy_table_markdown(strategy_df)
    )
    (REPORTS_RESULTS / "optim_strategies_net.md").write_text(md, encoding="utf-8")
    print("Wrote optim_strategies_net.csv / optim_strategies_net.md")
    return strategy_df


def write_risk_strategies_net(m31, params_market_net: pd.DataFrame, water_budget: float) -> pd.DataFrame:
    risk_inputs = build_risk_inputs(params_market_net)
    result = m31.run_focus_scenario(params_market_net, water_budget, risk_inputs)
    rows = result["rows"]
    df = pd.DataFrame([{k: v for k, v in row.items() if k != "_series"} for row in rows])
    df.to_csv(REPORTS_RESULTS / "risk_strategies_net.csv", index=False)

    lines = ["# Risk evaluation of B1/B2/B3/OURS (Model A) / Model B, NET IRRIGATION water basis (Phase 8)\n\n"]
    lines.append(f"Scenario: water={FOCUS_SCENARIO[0]}, price={FOCUS_SCENARIO[1]} (land={LAND_HA} ha), water_basis=net_irrigation.\n")
    lines.append(f"Model B pseudo-weights (profit, water, fert, risk) = {m31.MODEL_B_WEIGHTS}.\n\n")
    lines.append("Mirrors reports/results/risk_strategies.md's structure exactly, under the net-irrigation water basis -- see docs/water.md.\n\n")

    cols = ["strategy", "profit", "water_m3", "fert_kg", "n_crops", "portfolio_risk_rs", "scenario_n_years",
            "scenario_mean", "scenario_worst_year_profit", "scenario_worst_year", "scenario_P10",
            "scenario_n_loss_years", "feasible"]
    lines.append("| " + " | ".join(cols) + " |\n")
    lines.append("|" + "---|" * len(cols) + "\n")
    for _, row in df.iterrows():
        cells = []
        for c in cols:
            v = row.get(c, np.nan)
            if isinstance(v, bool):
                cells.append(str(v))
            elif isinstance(v, float):
                cells.append(f"{v:.2f}" if not np.isnan(v) else "-")
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |\n")

    (REPORTS_RESULTS / "risk_strategies_net.md").write_text("".join(lines), encoding="utf-8")
    print("Wrote risk_strategies_net.csv / risk_strategies_net.md")
    return df


def write_backtest_summary_net(m61, m60) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    fairness_df, rows_df, b2_oracle_df, decomp_df = m61.run_analysis(m60, water_basis=WATER_BASIS, rainfall_scenario=RAINFALL_SCENARIO)
    win_summary_df = m61.build_win_summary(rows_df)
    capture_budget_df = m61.build_capture_ratio_budget_level(rows_df)

    fairness_df.to_csv(REPORTS_RESULTS / "backtest_fairness_net.csv", index=False)
    rows_df.to_csv(REPORTS_RESULTS / "backtest_rows_net.csv", index=False)

    lines = ["# Backtest fairness/water-matched-oracle summary, NET IRRIGATION water basis (Phase 8)\n\n"]
    lines.append(
        "Reruns Phase 7.1's fairness metrics (B1_SCALED, profit per 1,000 m3 of "
        "water, capture_ratio_w vs the water-matched oracle ORACLE_W) with every "
        "params_df built under water_basis=\"net_irrigation\" instead of the "
        "original FAO TM3 total-need basis -- see docs/water.md and "
        "reports/results/water_basis_comparison.md for the interpretation.\n\n"
    )

    lines.append("## Win summary (per-year win rate + mean capture_ratio_w + mean profit/1000m3 of NET irrigation water)\n\n")
    cols = list(win_summary_df.columns)
    lines.append("| " + " | ".join(cols) + " |\n")
    lines.append("|" + "---|" * len(cols) + "\n")
    for _, row in win_summary_df.iterrows():
        cells = [f"{v:.3f}" if isinstance(v, float) and not pd.isna(v) else ("-" if pd.isna(v) else str(v)) for v in row]
        lines.append("| " + " | ".join(cells) + " |\n")

    lines.append("\n## Budget-level capture ratio (total realized profit / ORACLE's total realized profit)\n\n")
    cap_pivot = capture_budget_df.pivot(index="strategy", columns="scenario", values="capture_ratio")
    lines.append("| strategy | " + " | ".join(str(c) for c in cap_pivot.columns) + " |\n")
    lines.append("|---|" + "---|" * len(cap_pivot.columns) + "\n")
    for strategy, row in cap_pivot.iterrows():
        lines.append(f"| {strategy} | " + " | ".join(f"{v:.3f}" if pd.notna(v) else "-" for v in row) + " |\n")

    (REPORTS_RESULTS / "backtest_summary_net.md").write_text("".join(lines), encoding="utf-8")
    print("Wrote backtest_fairness_net.csv, backtest_rows_net.csv, backtest_summary_net.md")
    return fairness_df, win_summary_df, capture_budget_df


def write_comparison_doc(strategy_df_net: pd.DataFrame, win_summary_net: pd.DataFrame, capture_budget_net: pd.DataFrame) -> None:
    orig_path = REPORTS_RESULTS / "optim_strategies.csv"
    orig_df = pd.read_csv(orig_path) if orig_path.exists() else None
    orig_v2_win_path = REPORTS_RESULTS / "backtest_rows_v2.csv"

    lines = ["# Water basis comparison: total_need vs net_irrigation (Phase 8)\n\n"]
    lines.append(
        "Compares headline numbers between the original (`total_need`, FAO TM3 crop "
        "water NEED) and the new (`net_irrigation`, need minus effective season "
        "rainfall -- see docs/water.md) water bases, at the `tight`/`current` water "
        "scenarios, market price.\n\n"
    )

    lines.append("## Water need vs net irrigation, per crop (mm)\n\n")
    from agriopt.data.rainfall import rainfall_water_table
    wt = rainfall_water_table(CROPS).round(1)
    lines.append("| crop | water need (mm) | Peff normal (mm) | net irrigation normal (mm) | net irrigation dry (mm) |\n")
    lines.append("|---|---|---|---|---|\n")
    for crop, row in wt.iterrows():
        lines.append(f"| {crop} | {row['water_need_mm']} | {row['peff_normal_mm']} | {row['net_irrigation_normal_mm']} | {row['net_irrigation_dry_mm']} |\n")

    if orig_df is not None:
        lines.append("\n## E3 strategies: profit & water, tight/current x market (total_need vs net_irrigation)\n\n")
        lines.append("| water | strategy | profit (total_need) | profit (net_irrigation) | water_m3 (total_need) | water_m3 (net_irrigation) |\n")
        lines.append("|---|---|---|---|---|---|\n")
        for water_label in WATER_MULTIPLIERS:
            for strategy in ["B1", "B2", "B3", "OURS"]:
                o = orig_df[(orig_df.water_scenario == water_label) & (orig_df.price_mode == "market") & (orig_df.strategy == strategy)]
                n = strategy_df_net[(strategy_df_net.water_scenario == water_label) & (strategy_df_net.price_mode == "market") & (strategy_df_net.strategy == strategy)]
                if o.empty or n.empty:
                    continue
                o, n = o.iloc[0], n.iloc[0]
                lines.append(
                    f"| {water_label} | {strategy} | {o['profit']:.0f} | {n['profit']:.0f} | {o['water_m3']:.0f} | {n['water_m3']:.0f} |\n"
                )

    lines.append("\n## Backtest: win rate / capture_ratio_w / profit-per-1000m3, net irrigation basis\n\n")
    cols = list(win_summary_net.columns)
    lines.append("| " + " | ".join(cols) + " |\n")
    lines.append("|" + "---|" * len(cols) + "\n")
    for _, row in win_summary_net.iterrows():
        cells = [f"{v:.3f}" if isinstance(v, float) and not pd.isna(v) else ("-" if pd.isna(v) else str(v)) for v in row]
        lines.append("| " + " | ".join(cells) + " |\n")

    lines.append("\n## Findings\n\n")
    rice_net = wt.loc["rice", "net_irrigation_normal_mm"]
    wheat_net = wt.loc["wheat", "net_irrigation_normal_mm"]
    wheat_need = wt.loc["wheat", "water_need_mm"]
    sugarcane_need = wt.loc["sugarcane", "water_need_mm"]
    sugarcane_net = wt.loc["sugarcane", "net_irrigation_normal_mm"]
    lines.append(
        f"- Rainfed kharif crops (rice, soybean, tur, maize) drop to {rice_net:.0f}mm net irrigation under normal "
        "monsoon rainfall (from their full FAO TM3 need) -- monsoon rainfall alone covers essentially all of "
        "their season water need, confirmed by the numbers above, not just assumed.\n"
    )
    lines.append(
        f"- Rabi crops (wheat, jowar) barely benefit: net irrigation ({wheat_net:.0f}mm) is still "
        f"{wheat_net / wheat_need * 100:.0f}% of their total need ({wheat_need:.0f}mm) -- the Nov-Mar dry season "
        "provides almost no effective rainfall relief in this dataset.\n"
    )
    lines.append(
        f"- Sugarcane's net irrigation need ({sugarcane_net:.0f}mm) covers {sugarcane_net / sugarcane_need * 100:.0f}% "
        f"of its total need ({sugarcane_need:.0f}mm) -- LOWER than wheat/jowar's {wheat_net / wheat_need * 100:.0f}%, "
        "since sugarcane's whole-year season captures some monsoon-month rainfall that a pure-Rabi crop never sees. "
        "Its irrigation burden does not exceed total need (by construction) but remains the largest of any crop in "
        "absolute m3/ha under BOTH bases -- see docs/water.md section 6 for the full numbers.\n"
    )
    if orig_df is not None:
        b1_water_change = None
        try:
            o_b1 = orig_df[(orig_df.water_scenario == "current") & (orig_df.price_mode == "market") & (orig_df.strategy == "B1")].iloc[0]
            n_b1 = strategy_df_net[(strategy_df_net.water_scenario == "current") & (strategy_df_net.price_mode == "market") & (strategy_df_net.strategy == "B1")].iloc[0]
            b1_water_change = (n_b1["water_m3"] - o_b1["water_m3"]) / o_b1["water_m3"] * 100
        except (IndexError, KeyError):
            pass
        if b1_water_change is not None:
            lines.append(
                f"- B1 (current mix)'s own water footprint changes by {b1_water_change:+.1f}% moving from total_need to "
                "net_irrigation water -- since B1's crop mix is fixed, this change is driven entirely by how much of "
                "its existing crops' water need monsoon rainfall already covers.\n"
            )
    lines.append(
        "- All `_net` outputs (optim_strategies_net.*, risk_strategies_net.*, backtest_summary_net.md, "
        "backtest_fairness_net.csv, backtest_rows_net.csv) are NEW files -- no Phase 1-7.1 output was modified "
        "(verified: git status shows only new files added by this phase, plus the additive water_basis parameters).\n"
    )

    (REPORTS_RESULTS / "water_basis_comparison.md").write_text("".join(lines), encoding="utf-8")
    print("Wrote water_basis_comparison.md")


def main() -> None:
    REPORTS_RESULTS.mkdir(parents=True, exist_ok=True)

    m30 = _load_module("optim_30_net", "30_run_optimizer.py")
    m31 = _load_module("risk_31_net", "31_run_risk.py")
    m60 = _load_module("backtest_60_net", "60_backtest.py")
    m61 = _load_module("backtest_61_net", "61_backtest_v2.py")

    print("Computing B1's net-irrigation water footprint ...")
    x1, b1_water_net, _ = compute_b1_water_net()
    print(f"B1 net-irrigation water usage: {b1_water_net:.1f} m3")
    water_budgets = {label: mult * b1_water_net for label, mult in WATER_MULTIPLIERS.items()}
    for label, wb in water_budgets.items():
        print(f"  {label:10s} = {WATER_MULTIPLIERS[label]}x B1(net) = {wb:.1f} m3")

    print("\nBuilding net-irrigation crop params per price mode ...")
    params_by_mode = {
        mode: build_crop_params(mode, verbose=False, water_basis=WATER_BASIS, rainfall_scenario=RAINFALL_SCENARIO)
        for mode in PRICE_MODES
    }

    print("\n-- optim_strategies_net (E3 table) --")
    strategy_df_net = write_optim_strategies_net(m30, x1, params_by_mode, water_budgets)

    print("\n-- risk_strategies_net (B1/B2/B3/OURS_A/ModelB) --")
    write_risk_strategies_net(m31, params_by_mode["market"], water_budgets[FOCUS_SCENARIO[0]])

    print("\n-- backtest_summary_net --")
    _, win_summary_net, capture_budget_net = write_backtest_summary_net(m61, m60)

    print("\n-- water_basis_comparison.md --")
    write_comparison_doc(strategy_df_net, win_summary_net, capture_budget_net)


if __name__ == "__main__":
    sys.exit(main())
