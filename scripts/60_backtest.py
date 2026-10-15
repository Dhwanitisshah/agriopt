"""Phase 7: decision backtest 2016-2020 -- "would AgriOpt have helped?"

For each decision year t in 2016..2020: build every strategy's plan using
ONLY information available before sowing (agriopt.backtest.info), then score
that SAME plan twice -- once under the forecast/planning params (planned
profit) and once under year t's REALIZED yield/price (realized profit).
ORACLE plans directly against realized params -- a perfect-foresight upper
bound no other strategy's realized profit should ever beat. ORACLE_PRICE and
ORACLE_YIELD give partial foresight (realized prices with forecast yields, and
the reverse) so the gap between B2 and ORACLE can be split into "prices we
could not foresee" and "yields we could not foresee" (scripts/62_backtest_skill.py).

Information set: every crop is planned on 1 May of year t (info.PLAN_MONTH);
rabi prices are the naive carry-forward of the last price at or before May.
An earlier version read rabi prices in October while planning in May.

Two water scenarios per year ("default" = 1.0x B1's own water footprint that
year, "tight" = 0.7x), matching the WATER_MULTIPLIERS convention used in
scripts/31_run_risk.py / scripts/50_ablation.py.

Maharashtra's yield_clean.parquet tops out at year 2019 -- so t=2020 has NO
realized outcome for ANY crop (not a bug: verified against the raw data,
see docs/backtest.md). Planning still happens for 2020 (it only needs data
<= 2019), but realized profit/forecast-error/capture-ratio/stats all fall
back to the 4 years that actually have an outcome (2016-2019), which is
called out explicitly everywhere below rather than silently averaging over
whatever happens to be non-NaN.

Writes reports/results/backtest_rows.csv, backtest_summary.csv,
backtest_summary.md, backtest_realized_profit.png,
backtest_capture_ratio.png, backtest_planned_vs_realized.png, and
reports/results/backtest_findings.md.
"""
from __future__ import annotations

import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from agriopt.backtest.info import (
    build_forecast_params_df,
    build_realized_params_df,
    build_risk_inputs_leakfree,
    commit_planned_costs,
    current_mix_leakfree,
    hybrid_params_df,
)
from agriopt.config import CROPS, REPORTS_RESULTS
from agriopt.optim.baselines import evaluate, nsga2_recommended
from agriopt.optim.problem import Scenario
from agriopt.optim.solvers import nsga3_recommended, solve_lp_eps, solve_lp_profit_max

YEARS = [2016, 2017, 2018, 2019, 2020]
WATER_MULTIPLIERS = {"default": 1.0, "tight": 0.7}
LAND_HA = 10.0
FOOD_SHARE_MIN = 0.3
MAX_SHARE = 0.5
OURS_WEIGHTS = (0.5, 0.3, 0.2)  # matches baselines.nsga2_recommended's own default
MODEL_B_WEIGHTS = (0.4, 0.2, 0.1, 0.3)  # matches scripts/31_run_risk.py's MODEL_B_WEIGHTS
SEED = 0
STRATEGY_ORDER = ["B1", "B2", "B3", "OURS", "MODEL_B", "ORACLE_PRICE", "ORACLE_YIELD", "ORACLE"]


def evaluate_realized_profit(x, forecast_params: pd.DataFrame, realized_params: pd.DataFrame, missing_crops: list[str], scenario: Scenario) -> float | None:
    """Realized profit for allocation x (built under forecast_params' crop
    order/constraints), scored against year t's REALIZED profit_ha where
    available. Crops with no realized data (missing_crops) contribute 0 to
    the realized-profit sum -- excluded, not imputed -- and are always
    reported alongside (missing_realized_crops column) so a nonzero
    allocation into a missing crop is visible, never silently dropped.
    Water/fert are physical properties of the plan (crop_reference-driven,
    not yield/price-driven), so they're identical whether scored under
    forecast or realized params -- reused from forecast_params directly."""
    crops = list(forecast_params.index)
    if len(missing_crops) == len(crops):
        return None
    realized_full = realized_params.reindex(crops).copy()
    realized_full["profit_ha"] = realized_full["profit_ha"].fillna(0.0)
    realized_full["water_m3_ha"] = forecast_params["water_m3_ha"]
    realized_full["fert_kg_ha"] = forecast_params["fert_kg_ha"]
    realized_full["seasons_occupied"] = forecast_params["seasons_occupied"]
    return float(evaluate(x, realized_full, scenario)["profit"])


def run_year(
    t: int,
    water_basis: str = "total_need",
    rainfall_scenario: str = "normal",
    info_set: str = "may",
    crops: list[str] = CROPS,
) -> tuple[list[dict], dict]:
    """water_basis/rainfall_scenario (Phase 8): defaults reproduce every
    pre-Phase-8 result unchanged; water_basis="net_irrigation" threads
    through to build_forecast_params_df/build_realized_params_df so the
    whole backtest (B1/B2/B3/OURS/MODEL_B/ORACLE) can be rerun under net
    irrigation water without any other code path changing -- see
    scripts/70_water_basis_net.py and reports/results/water_basis_comparison.md.

    info_set ("may" default; "season" = legacy look-ahead, see info.PLAN_MONTH)
    and crops (default all 8; pass a subset, e.g. without sugarcane, for the
    forecast-skill variants in scripts/62_backtest_skill.py)."""
    forecast_params, finfo = build_forecast_params_df(
        t, crops=crops, water_basis=water_basis, rainfall_scenario=rainfall_scenario, info_set=info_set
    )
    realized_params, missing_realized = build_realized_params_df(t, crops=crops, water_basis=water_basis, rainfall_scenario=rainfall_scenario)
    realized_params = commit_planned_costs(realized_params, forecast_params)
    R = (forecast_params["yield_qtl_ha"] * forecast_params["price"]).to_numpy(dtype=float)
    risk_inputs = build_risk_inputs_leakfree(t - 1, crops=crops, R=R)

    dummy_scenario = Scenario(water_budget_m3=1e15, land_ha=LAND_HA, food_share_min=FOOD_SHARE_MIN, max_share=MAX_SHARE)
    x1_probe = current_mix_leakfree(forecast_params, dummy_scenario, t)
    b1_water_probe = float(x1_probe @ forecast_params["water_m3_ha"].to_numpy())

    rows = []
    oracle_feasible = len(missing_realized) < len(crops)
    # Phase 7.1 (scripts/61_backtest_v2.py) reuses these already-solved
    # allocations for fairness/water-matched-oracle/decomposition analysis
    # rather than resolving NSGA-II/NSGA-III a second time -- purely
    # additive, does not change any row/summary/plot this script itself
    # writes below.
    x_store: dict[str, dict[str, np.ndarray | None]] = {}
    scenario_store: dict[str, Scenario] = {}

    for label, mult in WATER_MULTIPLIERS.items():
        scenario = Scenario(water_budget_m3=b1_water_probe * mult, land_ha=LAND_HA, food_share_min=FOOD_SHARE_MIN, max_share=MAX_SHARE)
        scenario_store[label] = scenario

        x1 = current_mix_leakfree(forecast_params, scenario, t)
        r1 = evaluate(x1, forecast_params, scenario)

        x2, _ = solve_lp_profit_max(scenario, forecast_params)
        x3, _ = solve_lp_eps(scenario, r1["profit"], forecast_params) if x2 is not None else (None, None)
        x_ours, _, _, _ = nsga2_recommended(forecast_params, scenario, weights=OURS_WEIGHTS, seed=SEED)
        x_modelb, _, _, _ = nsga3_recommended(forecast_params, scenario, risk_inputs.Sigma, weights=MODEL_B_WEIGHTS, seed=SEED)

        strategies = {"B1": x1, "B2": x2, "B3": x3, "OURS": x_ours, "MODEL_B": x_modelb}
        x_store[label] = dict(strategies)
        for name, x in strategies.items():
            if x is None:
                rows.append({"year": t, "scenario": label, "strategy": name, "feasible": False, "planned_profit": np.nan,
                             "realized_profit": np.nan, "water_m3": np.nan, "fert_kg": np.nan, "forecast_error": np.nan,
                             "missing_realized_crops": ";".join(missing_realized)})
                continue
            r_planned = evaluate(x, forecast_params, scenario)
            realized_profit = evaluate_realized_profit(x, forecast_params, realized_params, missing_realized, scenario)
            rows.append({
                "year": t, "scenario": label, "strategy": name,
                "planned_profit": r_planned["profit"], "realized_profit": realized_profit,
                "water_m3": r_planned["water_m3"], "fert_kg": r_planned["fert_kg"],
                "feasible": r_planned["feasible"],
                "forecast_error": (realized_profit - r_planned["profit"]) if realized_profit is not None else np.nan,
                "missing_realized_crops": ";".join(missing_realized),
            })

        if oracle_feasible:
            x_oracle, _ = solve_lp_profit_max(scenario, realized_params)
            r_oracle = evaluate(x_oracle, realized_params, scenario)
            x_store[label]["ORACLE"] = x_oracle
            rows.append({
                "year": t, "scenario": label, "strategy": "ORACLE",
                "planned_profit": r_oracle["profit"], "realized_profit": r_oracle["profit"],
                "water_m3": r_oracle["water_m3"], "fert_kg": r_oracle["fert_kg"],
                "feasible": r_oracle["feasible"], "forecast_error": 0.0, "missing_realized_crops": "",
            })
            # partial foresight: know only the realized PRICE, or only the realized YIELD
            for name, know_price, know_yield in (("ORACLE_PRICE", True, False), ("ORACLE_YIELD", False, True)):
                hybrid = hybrid_params_df(forecast_params, realized_params, know_price, know_yield)
                x_h, _ = solve_lp_profit_max(scenario, hybrid)
                x_store[label][name] = x_h
                if x_h is None:
                    continue
                r_h = evaluate(x_h, hybrid, scenario)
                realized_h = evaluate_realized_profit(x_h, forecast_params, realized_params, missing_realized, scenario)
                rows.append({
                    "year": t, "scenario": label, "strategy": name,
                    "planned_profit": r_h["profit"], "realized_profit": realized_h,
                    "water_m3": r_h["water_m3"], "fert_kg": r_h["fert_kg"], "feasible": r_h["feasible"],
                    "forecast_error": (realized_h - r_h["profit"]) if realized_h is not None else np.nan,
                    "missing_realized_crops": ";".join(missing_realized),
                })
        else:
            x_store[label]["ORACLE"] = None
            x_store[label]["ORACLE_PRICE"] = None
            x_store[label]["ORACLE_YIELD"] = None
            rows.append({"year": t, "scenario": label, "strategy": "ORACLE", "feasible": False, "planned_profit": np.nan,
                         "realized_profit": np.nan, "water_m3": np.nan, "fert_kg": np.nan, "forecast_error": np.nan,
                         "missing_realized_crops": ";".join(missing_realized)})

    return rows, {
        "missing_realized": missing_realized,
        "b1_water_probe": b1_water_probe,
        "forecast_info": finfo,
        "forecast_params": forecast_params,
        "realized_params": realized_params,
        "x_store": x_store,
        "scenario_store": scenario_store,
    }


def build_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for scenario_label, sdf in df.groupby("scenario"):
        realized = sdf.dropna(subset=["realized_profit"])
        years_used = sorted(realized["year"].unique())
        oracle_total = realized[realized["strategy"] == "ORACLE"]["realized_profit"].sum()
        b1_by_year = realized[realized["strategy"] == "B1"].set_index("year")["realized_profit"]

        for strategy in STRATEGY_ORDER:
            srows = realized[realized["strategy"] == strategy]
            if srows.empty:
                continue
            total = srows["realized_profit"].sum()
            mean = srows["realized_profit"].mean()
            worst = srows["realized_profit"].min()
            capture = total / oracle_total if oracle_total else float("nan")
            if strategy == "B1":
                win_count = None
            else:
                joined = srows.set_index("year")["realized_profit"].reindex(b1_by_year.index)
                win_count = int((joined > b1_by_year).sum())
            water_all = df[(df["scenario"] == scenario_label) & (df["strategy"] == strategy)]["water_m3"]
            b1_water_all = df[(df["scenario"] == scenario_label) & (df["strategy"] == "B1")]["water_m3"]
            water_saved_vs_b1 = float((b1_water_all.to_numpy() - water_all.to_numpy()).mean()) if strategy != "B1" else 0.0
            gap = srows["forecast_error"].mean()  # signed: realized - planned, mean over years with a realized outcome

            rows.append({
                "scenario": scenario_label, "strategy": strategy, "n_years_realized": len(srows),
                "years_realized": ",".join(str(y) for y in years_used),
                "total_realized_profit": total, "mean_realized_profit": mean, "worst_year_realized_profit": worst,
                "capture_ratio_vs_oracle": capture, "win_count_vs_b1": win_count,
                "mean_water_saved_vs_b1_m3": water_saved_vs_b1, "mean_signed_forecast_gap_rs": gap,
            })
    return pd.DataFrame(rows)


def paired_deltas(df: pd.DataFrame) -> pd.DataFrame:
    """Per-year realized-profit difference (challenger - B1), per scenario, for
    OURS and MODEL_B -- one row per (scenario, challenger, year).

    Deliberately NO p-values. With n=4 paired years the smallest attainable
    two-sided p-value of a sign or Wilcoxon signed-rank test is 0.125, so a
    test can never reject at 5% and a p-value would only invite over-reading;
    the four deltas themselves are the honest result."""
    rows = []
    for scenario_label, sdf in df.groupby("scenario"):
        realized = sdf.dropna(subset=["realized_profit"])
        b1 = realized[realized["strategy"] == "B1"].set_index("year")["realized_profit"]
        for challenger in ["OURS", "MODEL_B"]:
            chal = realized[realized["strategy"] == challenger].set_index("year")["realized_profit"]
            for year in sorted(set(b1.index) & set(chal.index)):
                rows.append({
                    "scenario": scenario_label, "challenger": challenger, "year": int(year),
                    "challenger_profit": float(chal[year]), "b1_profit": float(b1[year]),
                    "delta_rs": float(chal[year] - b1[year]),
                    "delta_pct": float((chal[year] - b1[year]) / abs(b1[year]) * 100) if b1[year] else float("nan"),
                })
    return pd.DataFrame(rows)


def write_summary_md(summary_df: pd.DataFrame, deltas_df: pd.DataFrame, missing_by_year: dict) -> None:
    lines = ["# Decision backtest 2016-2020: summary (Phase 7)\n\n"]
    lines.append(
        "Maharashtra's yield_clean.parquet has no rows at all for year 2020 (any crop) -- verified against the "
        "raw data, not a code bug. Every 'realized' figure below (total/mean/worst realized profit, capture "
        "ratio, win count, forecast gap, per-year deltas) is therefore computed over **2016-2019 (n=4)**, "
        "not the full 5 decision years. Planned allocations and water/fert usage ARE reported for 2020 (planning "
        "only needs data <= 2019), just not scored against an outcome that doesn't exist. See "
        "`missing_realized_crops` in backtest_rows.csv and the per-year note below.\n\n"
    )
    for t, missing in missing_by_year.items():
        if missing:
            lines.append(f"- year {t}: realized data missing for crops {missing} ({'ALL crops' if len(missing) == len(CROPS) else 'partial'}).\n")
    lines.append("\n## Per-strategy summary, by water scenario\n\n")
    cols = ["scenario", "strategy", "n_years_realized", "total_realized_profit", "mean_realized_profit",
            "worst_year_realized_profit", "capture_ratio_vs_oracle", "win_count_vs_b1",
            "mean_water_saved_vs_b1_m3", "mean_signed_forecast_gap_rs"]
    lines.append("| " + " | ".join(cols) + " |\n")
    lines.append("|" + "---|" * len(cols) + "\n")
    for _, row in summary_df.iterrows():
        cells = []
        for c in cols:
            v = row[c]
            if v is None or (isinstance(v, float) and np.isnan(v)):
                cells.append("-")
            elif isinstance(v, float):
                cells.append(f"{v:,.3f}" if abs(v) < 10 else f"{v:,.0f}")
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |\n")

    lines.append(
        "\n`mean_signed_forecast_gap_rs` = mean(realized - planned) profit -- positive means plans came in "
        "MORE profitable than forecast (underpromised), negative means they were overoptimistic. Signed, not "
        "absolute, because 'how optimistic was the plan' is the question being asked (absolute error would only "
        "say how big the miss was, not which direction).\n"
    )

    lines.append("\n## Per-year realized-profit delta vs B1 (Rs), per scenario\n\n")
    lines.append(
        "**Four paired years (2016-2019) cannot support a significance test** -- the smallest attainable "
        "two-sided sign / Wilcoxon p-value at n=4 is 0.125 -- so none is reported. The per-year deltas below "
        "are the result; read the sign and size of each, not an aggregate.\n\n"
    )
    years = sorted(deltas_df["year"].unique())
    lines.append("| scenario | challenger | " + " | ".join(str(y) for y in years) + " | mean | years won |\n")
    lines.append("|" + "---|" * (len(years) + 4) + "\n")
    for (scenario_label, challenger), g in deltas_df.groupby(["scenario", "challenger"], sort=False):
        by_year = g.set_index("year")["delta_rs"]
        cells = [f"{by_year[y]:+,.0f}" if y in by_year.index else "-" for y in years]
        lines.append(
            f"| {scenario_label} | {challenger} | " + " | ".join(cells) + f" | {by_year.mean():+,.0f} | {int((by_year > 0).sum())}/{len(by_year)} |\n"
        )

    (REPORTS_RESULTS / "backtest_summary.md").write_text("".join(lines), encoding="utf-8")
    print("Wrote backtest_summary.md")


def plot_realized_profit(df: pd.DataFrame) -> None:
    for scenario_label, sdf in df.groupby("scenario"):
        fig, ax = plt.subplots(figsize=(8, 5))
        for strategy in STRATEGY_ORDER:
            s = sdf[sdf["strategy"] == strategy].sort_values("year")
            ax.plot(s["year"], s["realized_profit"], marker="o", label=strategy)
        ax.set_xlabel("decision year")
        ax.set_ylabel("realized profit (Rs)")
        ax.set_title(f"Realized profit by strategy/year ({scenario_label} water scenario)")
        ax.set_xticks(YEARS)
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(REPORTS_RESULTS / f"backtest_realized_profit_{scenario_label}.png", dpi=150)
        plt.close(fig)
    print("Wrote backtest_realized_profit_default.png / _tight.png")


def plot_capture_ratio(summary_df: pd.DataFrame) -> None:
    strategies = [s for s in STRATEGY_ORDER if s != "ORACLE"]
    scenarios = sorted(summary_df["scenario"].unique())
    x = np.arange(len(strategies))
    width = 0.35
    fig, ax = plt.subplots(figsize=(8, 5))
    for i, scenario_label in enumerate(scenarios):
        vals = []
        for s in strategies:
            row = summary_df[(summary_df["scenario"] == scenario_label) & (summary_df["strategy"] == s)]
            vals.append(float(row["capture_ratio_vs_oracle"].iloc[0]) if len(row) else np.nan)
        ax.bar(x + (i - 0.5) * width, vals, width, label=scenario_label)
    ax.axhline(1.0, color="gray", linestyle="--", linewidth=1)
    ax.set_xticks(x)
    ax.set_xticklabels(strategies)
    ax.set_ylabel("capture ratio (total realized profit / ORACLE's)")
    ax.set_title("Capture ratio vs perfect foresight (ORACLE=1.0), by scenario")
    ax.legend()
    fig.tight_layout()
    fig.savefig(REPORTS_RESULTS / "backtest_capture_ratio.png", dpi=150)
    plt.close(fig)
    print("Wrote backtest_capture_ratio.png")


def plot_planned_vs_realized(df: pd.DataFrame) -> None:
    realized = df.dropna(subset=["realized_profit"])
    fig, ax = plt.subplots(figsize=(7, 7))
    colors = plt.cm.tab10(np.linspace(0, 1, len(STRATEGY_ORDER)))
    for strategy, color in zip(STRATEGY_ORDER, colors):
        s = realized[realized["strategy"] == strategy]
        ax.scatter(s["planned_profit"], s["realized_profit"], label=strategy, color=color, alpha=0.8, s=40)
    lo = float(min(realized["planned_profit"].min(), realized["realized_profit"].min()))
    hi = float(max(realized["planned_profit"].max(), realized["realized_profit"].max()))
    ax.plot([lo, hi], [lo, hi], "k--", linewidth=1, label="perfect forecast")
    ax.set_xlabel("planned (forecast) profit, Rs")
    ax.set_ylabel("realized profit, Rs")
    ax.set_title("Planned vs realized profit (one point per strategy x year x scenario)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(REPORTS_RESULTS / "backtest_planned_vs_realized.png", dpi=150)
    plt.close(fig)
    print("Wrote backtest_planned_vs_realized.png")


def write_findings(df: pd.DataFrame, summary_df: pd.DataFrame, deltas_df: pd.DataFrame, missing_by_year: dict) -> None:
    lines = ["# Decision backtest findings (Phase 7)\n\n"]
    lines.append(
        "- **2020 has no realized outcome at all**: Maharashtra's yield_clean.parquet stops at 2019 for every "
        "crop, so all realized-profit comparisons below cover 2016-2019 (n=4 years), not the full 5 decision "
        "years -- planning for 2020 still ran (it only needs data through 2019), it's just unscored.\n"
    )

    realized = df.dropna(subset=["realized_profit"])
    for scenario_label in sorted(realized["scenario"].unique()):
        sdf = realized[realized["scenario"] == scenario_label]
        for strategy in ["OURS", "MODEL_B"]:
            b1 = sdf[sdf["strategy"] == "B1"].set_index("year")["realized_profit"]
            chal = sdf[sdf["strategy"] == strategy].set_index("year")["realized_profit"]
            for year in sorted(set(b1.index) & set(chal.index)):
                if chal[year] <= b1[year]:
                    lines.append(
                        f"- **{strategy} did NOT beat B1 in {year} ({scenario_label} scenario)**: realized profit "
                        f"Rs {chal[year]:,.0f} vs B1's Rs {b1[year]:,.0f}. See the allocation/price data for that "
                        "year in backtest_rows.csv and prices_monthly.parquet to trace which crop's forecast "
                        "missed -- reported here rather than glossed over.\n"
                    )

    for scenario_label in sorted(summary_df["scenario"].unique()):
        srow_ours = summary_df[(summary_df["scenario"] == scenario_label) & (summary_df["strategy"] == "OURS")]
        srow_b = summary_df[(summary_df["scenario"] == scenario_label) & (summary_df["strategy"] == "MODEL_B")]
        if len(srow_ours):
            r = srow_ours.iloc[0]
            lines.append(
                f"- **{scenario_label} scenario, OURS**: capture ratio {r['capture_ratio_vs_oracle']:.2f} vs "
                f"ORACLE, won {r['win_count_vs_b1']}/4 years vs B1, mean signed forecast gap "
                f"Rs {r['mean_signed_forecast_gap_rs']:,.0f} (realized - planned).\n"
            )
        if len(srow_b):
            r = srow_b.iloc[0]
            lines.append(
                f"- **{scenario_label} scenario, MODEL_B**: capture ratio {r['capture_ratio_vs_oracle']:.2f} vs "
                f"ORACLE, won {r['win_count_vs_b1']}/4 years vs B1, mean water saved vs B1 "
                f"{r['mean_water_saved_vs_b1_m3']:,.0f} m3.\n"
            )

    lines.append(
        "\n**Statistical caveat (stated plainly, not buried)**: only four years (2016-2019) have a realized "
        "outcome. With n=4 no sign or Wilcoxon test can reach p<0.125, so none is reported; "
        "backtest_summary.md lists the per-year deltas instead. Treat the results as four case studies, not as "
        "evidence that AgriOpt beats (or fails to beat) B1 in any statistically meaningful sense.\n"
    )

    (REPORTS_RESULTS / "backtest_findings.md").write_text("".join(lines), encoding="utf-8")
    print("Wrote backtest_findings.md")


def main() -> None:
    REPORTS_RESULTS.mkdir(parents=True, exist_ok=True)
    all_rows = []
    missing_by_year = {}
    for t in YEARS:
        print(f"-- decision year {t} --")
        rows, meta = run_year(t)
        all_rows.extend(rows)
        missing_by_year[t] = meta["missing_realized"]
        print(f"  b1_water_probe={meta['b1_water_probe']:.1f} m3, missing_realized={meta['missing_realized']}")

    df = pd.DataFrame(all_rows)
    df.to_csv(REPORTS_RESULTS / "backtest_rows.csv", index=False)
    print("Wrote backtest_rows.csv")

    summary_df = build_summary(df)
    summary_df.to_csv(REPORTS_RESULTS / "backtest_summary.csv", index=False)
    print("Wrote backtest_summary.csv")

    deltas_df = paired_deltas(df)
    deltas_df.to_csv(REPORTS_RESULTS / "backtest_deltas.csv", index=False)

    write_summary_md(summary_df, deltas_df, missing_by_year)
    plot_realized_profit(df)
    plot_capture_ratio(summary_df)
    plot_planned_vs_realized(df)
    write_findings(df, summary_df, deltas_df, missing_by_year)

    print("\n=== summary ===")
    print(summary_df.to_string(index=False))
    print("\n=== per-year deltas vs B1 ===")
    print(deltas_df.to_string(index=False))


if __name__ == "__main__":
    sys.exit(main())
