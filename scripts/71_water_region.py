"""Phase 8.1, step (d): net-irrigation table for EACH of the 4 IMD
subdivisions (8 crops x 4 regions x 2 rainfall scenarios), and the "E3
strategies" table (agriopt.optim rerun, same pattern as
scripts/70_water_basis_net.py) rerun for region="marathwada" and
region="konkan" specifically (drought-prone semi-arid vs high-rainfall
coastal -- the two regions that bracket Maharashtra's rainfall range; see
the Phase 8.1 task brief, which asks for these 2 of the 4 regions, not all
4, and does NOT ask for a full backtest rerun per region).

Reuses (does not duplicate) scripts/30_run_optimizer.py's run_scenario /
write_strategy_table / strategy_table_markdown, exactly as
scripts/70_water_basis_net.py already does for the net-irrigation basis.

Writes ONLY new `*_region` files -- no Phase 1-8 output (including the
`*_net` files from Phase 8) is read-write here, only read-only where needed
for comparison:
  reports/results/net_irrigation_by_region.csv / .md  -- 8 crops x 4 regions x 2 scenarios
  reports/results/optim_strategies_marathwada.csv / .md -- E3 table, region=marathwada
  reports/results/optim_strategies_konkan.csv / .md     -- E3 table, region=konkan
  reports/results/region_comparison.md                  -- narrative comparison doc
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from agriopt.config import CROPS, REPORTS_RESULTS
from agriopt.data.rainfall import REGIONS, rainfall_water_table
from agriopt.optim.baselines import current_mix
from agriopt.optim.params import build_crop_params
from agriopt.optim.problem import Scenario

REPO_ROOT = Path(__file__).resolve().parent.parent
WATER_BASIS = "net_irrigation"
RAINFALL_SCENARIO = "normal"
WATER_MULTIPLIERS = {"tight": 0.7, "current": 1.0}
PRICE_MODES = ["market", "msp_floor"]
LAND_HA = 10.0
RERUN_REGIONS = ["marathwada", "konkan"]  # per Phase 8.1 task brief: these 2 of the 4


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_net_irrigation_by_region() -> pd.DataFrame:
    """8 crops x 4 regions x 2 scenarios (normal/dry) net irrigation table."""
    frames = []
    for region in REGIONS:
        wt = rainfall_water_table(CROPS, region=region)
        wt = wt.reset_index().rename(columns={"index": "crop"})
        wt["region"] = region
        frames.append(wt)
    combined = pd.concat(frames, ignore_index=True)
    combined = combined[
        ["region", "crop", "water_need_mm", "peff_normal_mm", "net_irrigation_normal_mm", "net_irrigation_dry_mm"]
    ]
    combined.to_csv(REPORTS_RESULTS / "net_irrigation_by_region.csv", index=False)

    lines = ["# Net irrigation requirement by region (Phase 8.1)\n\n"]
    lines.append(
        "8 crops x 4 IMD subdivisions (+ the area-weighted state-wide \"maharashtra\" "
        "figure) x 2 rainfall scenarios (normal 30-yr mean, dry 20th-percentile year). "
        "See docs/water.md section 8 for methodology and citations.\n\n"
    )
    for region in REGIONS:
        sub = combined[combined["region"] == region].round(1)
        lines.append(f"## region={region}\n\n")
        lines.append("| crop | water need (mm) | Peff normal (mm) | net irrigation normal (mm) | net irrigation dry (mm) |\n")
        lines.append("|---|---|---|---|---|\n")
        for _, row in sub.iterrows():
            lines.append(
                f"| {row['crop']} | {row['water_need_mm']} | {row['peff_normal_mm']} | "
                f"{row['net_irrigation_normal_mm']} | {row['net_irrigation_dry_mm']} |\n"
            )
        lines.append("\n")
    (REPORTS_RESULTS / "net_irrigation_by_region.md").write_text("".join(lines), encoding="utf-8")
    print("Wrote net_irrigation_by_region.csv / net_irrigation_by_region.md")
    return combined


def compute_b1_water_region(region: str, land_ha: float = LAND_HA) -> tuple[np.ndarray, float, pd.DataFrame]:
    """Same pattern as scripts/70_water_basis_net.py's compute_b1_water_net,
    but for a specific region's own net-irrigation water footprint."""
    params = build_crop_params(
        "market", verbose=False, water_basis=WATER_BASIS, rainfall_scenario=RAINFALL_SCENARIO, region=region
    )
    dummy = Scenario(water_budget_m3=1e15, land_ha=land_ha, water_basis=WATER_BASIS, rainfall_scenario=RAINFALL_SCENARIO, region=region)
    x1 = current_mix(params, dummy)
    water = float(x1 @ params["water_m3_ha"].to_numpy())
    return x1, water, params


def write_optim_strategies_region(m30, region: str, x1: np.ndarray, params_by_mode: dict, water_budgets: dict) -> pd.DataFrame:
    all_runs = {}
    for water_label, wb in water_budgets.items():
        for price_mode in PRICE_MODES:
            all_runs[(water_label, price_mode)] = m30.run_scenario(water_label, price_mode, x1, params_by_mode[price_mode], wb)

    strategy_df = m30.write_strategy_table(all_runs)
    strategy_df.to_csv(REPORTS_RESULTS / f"optim_strategies_{region}.csv", index=False)
    md = (
        f"# Optimizer strategies (E3.1), NET IRRIGATION water basis, region={region} (Phase 8.1)\n\n"
        f"Water budget derived from B1's own NET-irrigation water footprint under region={region}'s "
        "own rainfall (same \"derive budget from B1's footprint\" pattern as Phase 3/7/8). See "
        "docs/water.md section 8 and reports/results/region_comparison.md.\n"
        + m30.strategy_table_markdown(strategy_df)
    )
    (REPORTS_RESULTS / f"optim_strategies_{region}.md").write_text(md, encoding="utf-8")
    print(f"Wrote optim_strategies_{region}.csv / optim_strategies_{region}.md")
    return strategy_df


def write_region_comparison(strategy_by_region: dict[str, pd.DataFrame], net_table: pd.DataFrame) -> None:
    orig_net_path = REPORTS_RESULTS / "optim_strategies_net.csv"
    orig_net_df = pd.read_csv(orig_net_path) if orig_net_path.exists() else None

    lines = ["# Region comparison: net-irrigation water basis by IMD subdivision (Phase 8.1)\n\n"]
    lines.append(
        "Compares the recommended allocation (OURS, NSGA-II + pseudo-weights) at the `current` "
        "water/`market` price scenario, across region=`maharashtra` (state-wide, area-weighted -- "
        "reports/results/optim_strategies_net.md, Phase 8), region=`marathwada` (drought-prone, "
        "semi-arid) and region=`konkan` (high-rainfall coastal) -- see docs/water.md section 8 for "
        "the net irrigation numbers behind these allocations.\n\n"
    )

    lines.append("## Net irrigation requirement, region contrast (normal scenario, mm)\n\n")
    pivot = net_table[net_table["region"].isin(["maharashtra", "marathwada", "konkan"])].pivot(
        index="crop", columns="region", values="net_irrigation_normal_mm"
    ).round(1)
    cols = [c for c in ["maharashtra", "marathwada", "konkan"] if c in pivot.columns]
    lines.append("| crop | " + " | ".join(cols) + " |\n")
    lines.append("|---|" + "---|" * len(cols) + "\n")
    for crop, row in pivot.iterrows():
        lines.append(f"| {crop} | " + " | ".join(f"{row[c]:.1f}" for c in cols) + " |\n")

    lines.append("\n## OURS allocation summary, current water x market price\n\n")
    header_regions = ["marathwada", "konkan"]

    # write_strategy_table doesn't carry per-crop hectare allocations, only
    # the evaluated summary (profit/water/fert/n_crops/food_share) -- report
    # that summary per region here.
    lines_alloc = []
    for region in header_regions:
        df = strategy_by_region[region]
        row = df[(df.water_scenario == "current") & (df.price_mode == "market") & (df.strategy == "OURS")]
        if not row.empty:
            r = row.iloc[0]
            lines_alloc.append(
                f"- **{region}**: OURS profit={r['profit']:.0f} Rs, water={r['water_m3']:.0f} m3, "
                f"fert={r['fert_kg']:.0f} kg, n_crops={r['n_crops']}, food_share={r['food_share']:.2f}\n"
            )
    lines.append("".join(lines_alloc))

    lines.append("\n## E3 strategies: profit & water, current x market -- maharashtra (Phase 8 net) vs marathwada vs konkan\n\n")
    lines.append("| region | strategy | profit (Rs) | water_m3 |\n")
    lines.append("|---|---|---|---|\n")
    for strategy in ["B1", "B2", "B3", "OURS"]:
        if orig_net_df is not None:
            o = orig_net_df[(orig_net_df.water_scenario == "current") & (orig_net_df.price_mode == "market") & (orig_net_df.strategy == strategy)]
            if not o.empty:
                r = o.iloc[0]
                lines.append(f"| maharashtra (state-wide) | {strategy} | {r['profit']:.0f} | {r['water_m3']:.0f} |\n")
        for region in header_regions:
            df = strategy_by_region[region]
            r = df[(df.water_scenario == "current") & (df.price_mode == "market") & (df.strategy == strategy)]
            if not r.empty:
                r = r.iloc[0]
                lines.append(f"| {region} | {strategy} | {r['profit']:.0f} | {r['water_m3']:.0f} |\n")

    lines.append("\n## Findings\n\n")
    mw_rice = pivot.loc["rice", "marathwada"] if "rice" in pivot.index and "marathwada" in pivot.columns else None
    kk_rice = pivot.loc["rice", "konkan"] if "rice" in pivot.index and "konkan" in pivot.columns else None
    mh_rice = pivot.loc["rice", "maharashtra"] if "rice" in pivot.index and "maharashtra" in pivot.columns else None
    if mw_rice is not None and mh_rice is not None:
        lines.append(
            f"- Marathwada's own (drier) normal-year effective rainfall pushes rice's net irrigation to "
            f"{mw_rice:.0f}mm vs {mh_rice:.0f}mm state-wide ({(mw_rice / mh_rice - 1) * 100:+.0f}%) -- Marathwada's "
            "season-window rainfall covers noticeably less of rice's FAO TM3 need than the state-wide "
            "average, making rice relatively more water-expensive there.\n"
        )
    if kk_rice is not None and mh_rice is not None:
        lines.append(
            f"- Konkan's high monsoon rainfall keeps rice's net irrigation at {kk_rice:.0f}mm (essentially "
            "just RICE_EXTRA_MM's puddling-water floor -- see docs/water.md 8.2), the lowest of the 3 regions "
            "shown, since Konkan's own Kharif-season Peff comfortably exceeds rice's total water need.\n"
        )
    b1_water_deltas = []
    for region in header_regions:
        df = strategy_by_region[region]
        b1 = df[(df.water_scenario == "current") & (df.price_mode == "market") & (df.strategy == "B1")]
        if not b1.empty and orig_net_df is not None:
            o_b1 = orig_net_df[(orig_net_df.water_scenario == "current") & (orig_net_df.price_mode == "market") & (orig_net_df.strategy == "B1")]
            if not o_b1.empty:
                delta = (b1.iloc[0]["water_m3"] - o_b1.iloc[0]["water_m3"]) / o_b1.iloc[0]["water_m3"] * 100
                b1_water_deltas.append((region, delta))
    for region, delta in b1_water_deltas:
        lines.append(
            f"- B1 (current mix)'s own net-irrigation water footprint under region={region} is "
            f"{delta:+.1f}% vs the state-wide maharashtra figure -- since B1's crop mix is fixed, this "
            "change is driven entirely by how much of the SAME crop mix's water need that region's own "
            "rainfall covers.\n"
        )
    lines.append(
        "- All `*_region` outputs (net_irrigation_by_region.{csv,md}, optim_strategies_marathwada.{csv,md}, "
        "optim_strategies_konkan.{csv,md}, region_comparison.md) are NEW files -- no Phase 1-8 output "
        "(including the `*_net` files) was modified.\n"
    )

    (REPORTS_RESULTS / "region_comparison.md").write_text("".join(lines), encoding="utf-8")
    print("Wrote region_comparison.md")


def main() -> None:
    REPORTS_RESULTS.mkdir(parents=True, exist_ok=True)

    print("-- net_irrigation_by_region (8 crops x 4 regions x 2 scenarios) --")
    net_table = write_net_irrigation_by_region()

    m30 = _load_module("optim_30_region", "30_run_optimizer.py")

    strategy_by_region = {}
    for region in RERUN_REGIONS:
        print(f"\n-- E3 strategies, region={region} --")
        x1, b1_water, _ = compute_b1_water_region(region)
        print(f"B1 net-irrigation water usage ({region}): {b1_water:.1f} m3")
        water_budgets = {label: mult * b1_water for label, mult in WATER_MULTIPLIERS.items()}
        for label, wb in water_budgets.items():
            print(f"  {label:10s} = {WATER_MULTIPLIERS[label]}x B1({region}) = {wb:.1f} m3")

        params_by_mode = {
            mode: build_crop_params(mode, verbose=False, water_basis=WATER_BASIS, rainfall_scenario=RAINFALL_SCENARIO, region=region)
            for mode in PRICE_MODES
        }
        strategy_by_region[region] = write_optim_strategies_region(m30, region, x1, params_by_mode, water_budgets)

    print("\n-- region_comparison.md --")
    write_region_comparison(strategy_by_region, net_table)


if __name__ == "__main__":
    sys.exit(main())
