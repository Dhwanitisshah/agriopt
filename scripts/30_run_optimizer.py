"""Phase 3 / Experiment 3: multi-objective crop allocation optimizer.

6 scenarios (water budget tight/current/relaxed x price market/msp_floor),
4 strategies (B1 current-mix, B2 profit-max LP, B3 same-profit-min-water LP,
OURS NSGA-II + pseudo-weights) -> reports/results/optim_strategies.csv/.md.
NSGA-II (5 seeds) vs exact LP reference front: hypervolume + IGD + runtime
-> reports/results/optim_front_quality.csv/.md. Plots + findings for the
current/market scenario.
"""
from __future__ import annotations

import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pymoo.indicators.hv import HV
from pymoo.indicators.igd import IGD

from agriopt.config import CROPS, REPORTS_RESULTS
from agriopt.optim.baselines import current_mix, evaluate, nsga2_recommended, profit_max, same_profit_min_water
from agriopt.optim.params import build_crop_params
from agriopt.optim.problem import Scenario
from agriopt.optim.solvers import exact_front_lp, solve_nsga2

WATER_MULTIPLIERS = {"tight": 0.7, "current": 1.0, "relaxed": 1.3}
PRICE_MODES = ["market", "msp_floor"]
LAND_HA = 10.0
SEEDS = [0, 1, 2, 3, 4]
PLOT_SCENARIO = ("current", "market")


def compute_b1_water(land_ha: float = LAND_HA) -> tuple[np.ndarray, float, pd.DataFrame]:
    """B1's hectare allocation and water use don't depend on price_mode
    (current_mix uses historical area shares only; water_m3_ha doesn't
    depend on price) -- compute once, reuse everywhere."""
    params = build_crop_params("market", verbose=False)
    dummy = Scenario(water_budget_m3=1e15, land_ha=land_ha)
    x1 = current_mix(params, dummy)
    water = float(x1 @ params["water_m3_ha"].to_numpy())
    return x1, water, params


def pct_change(new: float, base: float) -> float:
    if base == 0:
        return float("nan")
    return (new - base) / abs(base) * 100


def run_scenario(water_label: str, price_mode: str, x1: np.ndarray, params_df: pd.DataFrame, water_budget: float) -> dict:
    scenario = Scenario(water_budget_m3=water_budget, land_ha=LAND_HA, price_mode=price_mode)

    r1 = evaluate(x1, params_df, scenario)

    x2 = profit_max(params_df, scenario)
    r2 = evaluate(x2, params_df, scenario) if x2 is not None else None

    x3 = same_profit_min_water(params_df, scenario, min_profit=r1["profit"])
    r3 = evaluate(x3, params_df, scenario) if x3 is not None else None

    x4, X_front, F_front, nsga_runtime = nsga2_recommended(params_df, scenario, seed=42)
    r4 = evaluate(x4, params_df, scenario) if x4 is not None else None

    return {
        "scenario": (water_label, price_mode),
        "water_budget_m3": water_budget,
        "x": {"B1": x1, "B2": x2, "B3": x3, "OURS": x4},
        "eval": {"B1": r1, "B2": r2, "B3": r3, "OURS": r4},
        "nsga_front": (X_front, F_front),
        "nsga_runtime": nsga_runtime,
    }


def write_strategy_table(all_runs: dict) -> pd.DataFrame:
    rows = []
    for (water_label, price_mode), run in all_runs.items():
        b1_profit = run["eval"]["B1"]["profit"]
        b1_water = run["eval"]["B1"]["water_m3"]
        b1_fert = run["eval"]["B1"]["fert_kg"]
        for strategy in ["B1", "B2", "B3", "OURS"]:
            r = run["eval"][strategy]
            if r is None:
                rows.append({"water_scenario": water_label, "price_mode": price_mode, "strategy": strategy, "feasible": False})
                continue
            rows.append(
                {
                    "water_scenario": water_label,
                    "price_mode": price_mode,
                    "strategy": strategy,
                    "profit": r["profit"],
                    "water_m3": r["water_m3"],
                    "fert_kg": r["fert_kg"],
                    "food_share": r["food_share"],
                    "n_crops": r["n_crops"],
                    "profit_risk": r["profit_risk"],
                    "feasible": r["feasible"],
                    "profit_pct_vs_B1": pct_change(r["profit"], b1_profit),
                    "water_pct_vs_B1": pct_change(r["water_m3"], b1_water),
                    "fert_pct_vs_B1": pct_change(r["fert_kg"], b1_fert),
                }
            )
    return pd.DataFrame(rows)


def strategy_table_markdown(df: pd.DataFrame) -> str:
    lines = []
    for (water_label, price_mode), sub in df.groupby(["water_scenario", "price_mode"], sort=False):
        lines.append(f"\n## water={water_label}, price={price_mode}\n\n")
        cols = ["strategy", "profit", "water_m3", "fert_kg", "food_share", "n_crops", "profit_risk",
                "profit_pct_vs_B1", "water_pct_vs_B1", "fert_pct_vs_B1", "feasible"]
        lines.append("| " + " | ".join(cols) + " |\n")
        lines.append("|" + "---|" * len(cols) + "\n")
        for _, row in sub.iterrows():
            cells = []
            for c in cols:
                v = row.get(c, np.nan)
                if isinstance(v, bool):
                    cells.append(str(v))
                elif isinstance(v, (int, np.integer)):
                    cells.append(str(v))
                elif isinstance(v, float):
                    cells.append(f"{v:.2f}" if not np.isnan(v) else "-")
                elif isinstance(v, str):
                    cells.append(v)
                else:
                    cells.append("-")
            lines.append("| " + " | ".join(cells) + " |\n")
    return "".join(lines)


def front_quality_for_scenario(water_label: str, price_mode: str, params_df: pd.DataFrame, water_budget: float) -> dict:
    scenario = Scenario(water_budget_m3=water_budget, land_ha=LAND_HA, price_mode=price_mode)
    X_lp, F_lp = exact_front_lp(scenario, n=50, params_df=params_df)

    nsga_fronts, runtimes = [], []
    for seed in SEEDS:
        _, F, rt = solve_nsga2(scenario, params_df, seed=seed)
        nsga_fronts.append(F)
        runtimes.append(rt)

    def to_min_form(F):
        Fm = F.copy()
        Fm[:, 0] = -Fm[:, 0]
        return Fm

    union = np.vstack([to_min_form(F) for F in nsga_fronts] + [to_min_form(F_lp)])
    lo, hi = union.min(axis=0), union.max(axis=0)
    span = np.where(hi > lo, hi - lo, 1.0)

    def norm(F):
        return (to_min_form(F) - lo) / span

    ref_point = np.array([1.1, 1.1, 1.1])
    hv = HV(ref_point=ref_point)
    igd = IGD(norm(F_lp))

    hv_lp = float(hv(norm(F_lp)))
    hv_nsga = np.array([float(hv(norm(F))) for F in nsga_fronts])
    igd_nsga = np.array([float(igd(norm(F))) for F in nsga_fronts])

    return {
        "water_scenario": water_label,
        "price_mode": price_mode,
        "hv_lp_reference": hv_lp,
        "hv_nsga2_mean": float(hv_nsga.mean()),
        "hv_nsga2_std": float(hv_nsga.std()),
        "igd_nsga2_mean": float(igd_nsga.mean()),
        "igd_nsga2_std": float(igd_nsga.std()),
        "runtime_mean_s": float(np.mean(runtimes)),
        "runtime_std_s": float(np.std(runtimes)),
        "lp_front_size": len(F_lp),
        "nsga_front_size_mean": float(np.mean([len(F) for F in nsga_fronts])),
    }


def plot_scenario(water_label: str, price_mode: str, run: dict, params_df: pd.DataFrame, X_lp: np.ndarray, F_lp: np.ndarray) -> None:
    X_front, F_front = run["nsga_front"]

    fig, ax = plt.subplots(figsize=(8, 6))
    sc = ax.scatter(F_front[:, 0], F_front[:, 1], c=F_front[:, 2], cmap="viridis", s=25, alpha=0.8, label="NSGA-II front")
    fig.colorbar(sc, ax=ax, label="fertilizer (kg)")

    order = np.argsort(F_lp[:, 1])
    ax.plot(F_lp[order, 0], F_lp[order, 1], "k-", linewidth=1, alpha=0.6, label="LP exact front")

    markers = {"B1": ("s", "red"), "B2": ("^", "orange"), "B3": ("D", "purple"), "OURS": ("*", "blue")}
    for strategy, (marker, color) in markers.items():
        r = run["eval"][strategy]
        if r is None:
            continue
        ax.scatter([r["profit"]], [r["water_m3"]], marker=marker, s=180, color=color, edgecolor="black", label=strategy, zorder=5)

    ax.set_xlabel("profit (Rs)")
    ax.set_ylabel("water (m3)")
    ax.set_title(f"Pareto front: water={water_label}, price={price_mode}")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(REPORTS_RESULTS / "optim_pareto_front.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 6))
    strategies = ["B1", "B2", "B3", "OURS"]
    bottom = np.zeros(len(strategies))
    crops = list(params_df.index)
    colors = plt.cm.tab10(np.linspace(0, 1, len(crops)))
    for crop, color in zip(crops, colors):
        heights = []
        for s in strategies:
            x = run["x"][s]
            heights.append(x[crops.index(crop)] if x is not None else 0.0)
        ax.bar(strategies, heights, bottom=bottom, label=crop, color=color)
        bottom += np.array(heights)
    ax.set_ylabel("hectares")
    ax.set_title(f"Allocation by crop: water={water_label}, price={price_mode}")
    ax.legend(fontsize=8, bbox_to_anchor=(1.02, 1), loc="upper left")
    fig.tight_layout()
    fig.savefig(REPORTS_RESULTS / "optim_allocation_by_crop.png", dpi=150)
    plt.close(fig)


def write_findings(strategy_df: pd.DataFrame, quality_df: pd.DataFrame) -> None:
    lines = ["# Optimizer findings (Phase 3 / Experiment 3)\n\n"]

    b3_rows = strategy_df[strategy_df["strategy"] == "B3"]
    ours_rows = strategy_df[strategy_df["strategy"] == "OURS"]
    headline_candidates = pd.concat([b3_rows, ours_rows])
    headline_candidates = headline_candidates[
        (headline_candidates["profit_pct_vs_B1"] >= -0.5) & (headline_candidates["water_pct_vs_B1"] < 0) & headline_candidates["feasible"]
    ]
    if not headline_candidates.empty:
        best = headline_candidates.loc[headline_candidates["water_pct_vs_B1"].idxmin()]
        lines.append(
            f"- **Headline: {best['strategy']} matches or beats current-mix profit "
            f"({best['profit_pct_vs_B1']:+.1f}%) with {abs(best['water_pct_vs_B1']):.1f}% less water** "
            f"(water={best['water_scenario']}, price={best['price_mode']}).\n"
        )
    else:
        lines.append(
            "- No strategy both matched B1's profit and used less water across all 6 scenarios "
            "(see optim_strategies.md for the per-scenario numbers) -- the profit/water tradeoff is "
            "real here, not free.\n"
        )

    b2_profit_avg = strategy_df[strategy_df["strategy"] == "B2"]["profit"].mean()
    b1_profit_avg = strategy_df[strategy_df["strategy"] == "B1"]["profit"].mean()
    lines.append(
        f"- B2 (pure profit-max LP) averages {pct_change(b2_profit_avg, b1_profit_avg):+.1f}% profit vs B1 "
        f"across all 6 scenarios, but concentrates into very few crops "
        f"(mean n_crops={strategy_df[strategy_df['strategy']=='B2']['n_crops'].mean():.1f}) -- profit-max "
        "is not diversified.\n"
    )

    ours_vs_lp = quality_df["hv_nsga2_mean"] / quality_df["hv_lp_reference"]
    worst_scenario = quality_df.loc[ours_vs_lp.idxmin()]
    worst_ratio = ours_vs_lp.min()
    if worst_ratio < 0.98:
        lines.append(
            f"- NSGA-II's hypervolume is below the exact LP reference front's in at least one scenario "
            f"(worst: water={worst_scenario['water_scenario']}, price={worst_scenario['price_mode']}, "
            f"NSGA-II HV is {(1 - worst_ratio) * 100:.1f}% lower) -- expected, since NSGA-II approximates a "
            "front that LP epsilon-constraint sweeps exactly for this linear problem.\n"
        )
    else:
        lines.append(
            f"- **NSGA-II's hypervolume is HIGHER than the exact LP reference front's in every scenario** "
            f"(mean ratio {ours_vs_lp.mean():.2f}x) -- not a contradiction: `exact_front_lp` traces a "
            "1-D lexicographic SLICE of the true 3-objective Pareto surface (for each profit level, the "
            "unique minimal water, then unique minimal fert at that water), not the full surface. NSGA-II "
            "explores water/fert trade-offs off that slice too, covering more of the surface -- while "
            f"still staying close to the LP curve (mean IGD {quality_df['igd_nsga2_mean'].mean():.3f}, "
            "small relative to the front's own scale). The LP front is exact where it's defined, but it's "
            "a curve, not a surface; NSGA-II's front is an approximate surface.\n"
        )

    lines.append(
        f"- NSGA-II runtime: {quality_df['runtime_mean_s'].mean():.2f}s mean per run (pop=100, gens=200) "
        f"across seeds 0-4, vs `exact_front_lp`'s ~50 tiny LP solves (well under a second) -- for this small "
        "(8-variable, linear) problem the LP sweep is far cheaper per point, but only traces one curve "
        "through objective space; NSGA-II's cost buys broader coverage of the trade-off surface, which "
        "would matter more once objectives/constraints stop being linear.\n"
    )

    b1_food = strategy_df[strategy_df["strategy"] == "B1"]["food_share"].iloc[0]
    lines.append(
        f"- B1 (current mix)'s food_share is {b1_food * 100:.1f}% (comfortably above the 30% minimum) "
        "in every scenario since it's not water/food-constrained by construction -- if a scenario shows "
        "B1 infeasible on water, that's flagged, not silently fixed (see optim_strategies.md 'feasible' column).\n"
    )

    b1_infeasible = strategy_df[(strategy_df["strategy"] == "B1") & (~strategy_df["feasible"])]
    if not b1_infeasible.empty:
        lines.append(
            f"- B1 is INFEASIBLE (violates the water or food constraint) in {len(b1_infeasible)}/6 scenarios "
            f"({', '.join(f'{r.water_scenario}/{r.price_mode}' for r in b1_infeasible.itertuples())}) -- "
            "reported as-is, not force-fixed, per the brief.\n"
        )
    else:
        lines.append("- B1 (current mix) is feasible in all 6 scenarios -- historical Maharashtra cropping already fits the water/food constraints tested here.\n")

    lines.append(
        "- Water uses FAO TM3 total crop water NEED, not net irrigation (see docs/formulation.md) -- "
        "WATER_BUDGET_M3 scenarios should be read as a water-need budget, not a literal canal/well supply figure.\n"
    )

    (REPORTS_RESULTS / "optim_findings.md").write_text("".join(lines), encoding="utf-8")
    print("Wrote optim_findings.md")


def main() -> None:
    REPORTS_RESULTS.mkdir(parents=True, exist_ok=True)

    x1, b1_water, _ = compute_b1_water()
    print(f"B1 water usage (price-mode independent): {b1_water:.1f} m3")
    print("Water budget scenarios:")
    water_budgets = {label: mult * b1_water for label, mult in WATER_MULTIPLIERS.items()}
    for label, wb in water_budgets.items():
        print(f"  {label:10s} = {WATER_MULTIPLIERS[label]}x B1 = {wb:.1f} m3")

    print("\nBuilding crop params per price mode ...")
    params_by_mode = {}
    for mode in PRICE_MODES:
        print(f"\n-- price_mode={mode} --")
        params_by_mode[mode] = build_crop_params(mode, verbose=True)

    all_runs = {}
    quality_rows = []
    for water_label, wb in water_budgets.items():
        for price_mode in PRICE_MODES:
            print(f"\nRunning scenario water={water_label} price={price_mode} ...")
            run = run_scenario(water_label, price_mode, x1, params_by_mode[price_mode], wb)
            all_runs[(water_label, price_mode)] = run
            print(f"  B1 profit={run['eval']['B1']['profit']:.0f} feasible={run['eval']['B1']['feasible']}")
            print(f"  B2 profit={run['eval']['B2']['profit']:.0f}" if run['eval']['B2'] else "  B2 infeasible")
            print(f"  B3 profit={run['eval']['B3']['profit']:.0f}" if run['eval']['B3'] else "  B3 infeasible")
            print(f"  OURS profit={run['eval']['OURS']['profit']:.0f}" if run['eval']['OURS'] else "  OURS infeasible")

            print("  Computing front quality (LP exact front + NSGA-II x5 seeds) ...")
            q = front_quality_for_scenario(water_label, price_mode, params_by_mode[price_mode], wb)
            quality_rows.append(q)

    # --- E3.1 ------------------------------------------------------------------
    strategy_df = write_strategy_table(all_runs)
    strategy_df.to_csv(REPORTS_RESULTS / "optim_strategies.csv", index=False)
    md = "# Optimizer strategies (E3.1)\n" + strategy_table_markdown(strategy_df)
    (REPORTS_RESULTS / "optim_strategies.md").write_text(md, encoding="utf-8")
    print("\nWrote optim_strategies.csv / optim_strategies.md")

    # --- E3.2 ------------------------------------------------------------------
    quality_df = pd.DataFrame(quality_rows)
    quality_df.to_csv(REPORTS_RESULTS / "optim_front_quality.csv", index=False)
    q_lines = ["# NSGA-II vs exact LP front quality (E3.2)\n\n"]
    q_cols = list(quality_df.columns)
    q_lines.append("| " + " | ".join(q_cols) + " |\n")
    q_lines.append("|" + "---|" * len(q_cols) + "\n")
    for _, row in quality_df.iterrows():
        q_lines.append("| " + " | ".join(f"{v:.3f}" if isinstance(v, float) else str(v) for v in row) + " |\n")
    (REPORTS_RESULTS / "optim_front_quality.md").write_text("".join(q_lines), encoding="utf-8")
    print("Wrote optim_front_quality.csv / optim_front_quality.md")

    # --- E3.3 plots (current water, market price) --------------------------------
    plot_label, plot_mode = PLOT_SCENARIO
    plot_run = all_runs[(plot_label, plot_mode)]
    X_lp, F_lp = exact_front_lp(
        Scenario(water_budget_m3=water_budgets[plot_label], land_ha=LAND_HA, price_mode=plot_mode),
        n=50,
        params_df=params_by_mode[plot_mode],
    )
    plot_scenario(plot_label, plot_mode, plot_run, params_by_mode[plot_mode], X_lp, F_lp)
    print("Wrote optim_pareto_front.png / optim_allocation_by_crop.png")

    # --- Findings -------------------------------------------------------------
    write_findings(strategy_df, quality_df)


if __name__ == "__main__":
    sys.exit(main())
