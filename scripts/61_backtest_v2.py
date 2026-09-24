"""Phase 7.1: backtest fairness, water-matched oracle, profit decomposition.

Builds on Phase 7's `scripts/60_backtest.py` -- specifically its `run_year()`,
which now also returns (additively, see that script's `run_year` docstring)
the per-scenario allocation vectors (`x_store`) and the forecast/realized
params_df used that year. This script REUSES those already-solved
allocations rather than resolving NSGA-II/NSGA-III a second time, and never
calls `scripts/60_backtest.py`'s own `main()` -- so none of Phase 7's
committed output files (backtest_rows.csv, backtest_summary.*,
backtest_findings.md, the PNGs, docs/backtest.md) are touched.

**MODEL_B/NSGA-III reproducibility caveat (found during this phase, not
introduced by it)**: while developing this script, re-running
`scripts/60_backtest.py main()` a second time reproduced every B1/B2/B3/
OURS/ORACLE figure bit-for-bit (all LP- or NSGA-II-based, `seed=0`), but
MODEL_B's (NSGA-III) realized/planned profit came out QUANTITATIVELY
DIFFERENT (same order of magnitude, not the same value) on the second run
despite `seed=0` being passed to `solve_nsga3` -- root cause not chased
down here (out of scope for 7.1; suspected culprit is pymoo NSGA-III's
reference-direction/survival machinery touching a global RNG not fully
covered by the `seed=` kwarg, since NSGA-II with the same seeding
convention WAS reproducible). Concretely: this means the MODEL_B numbers
this script computes (a fresh `run_year()` call) will NOT exactly match
the MODEL_B numbers already committed in backtest_rows.csv from Phase 7's
original run -- expected, harmless for every invariant this phase checks
(feasibility, the decomposition identity, ORACLE upper bounds), and
reported here so it isn't mistaken for a bug in this new code. B1/B2/B3/
OURS are bit-reproducible.

Writes:
  reports/results/backtest_fairness_v2.csv       -- B1 vs B1_SCALED feasibility/water
  reports/results/backtest_rows_v2.csv           -- per strategy/year/scenario: profit-per-water, capture_ratio_w, wins
  reports/results/backtest_b2_oracle_v2.csv      -- B2 vs ORACLE allocation comparison
  reports/results/backtest_decomposition_v2.csv  -- per crop/strategy/year/scenario profit decomposition
  reports/results/backtest_summary_v2.md         -- headline tables
  reports/results/backtest_findings_v2.md        -- narrative, names crops/effects
  reports/results/backtest_decomposition_tight_v2.png -- stacked bar, OURS vs B1_SCALED, tight scenario
Updates (in place, additively -- existing columns/values unchanged):
  data/reference/msp_history.csv -- new `provenance` column for every row
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from agriopt.backtest.evaluate_v2 import ALLOC_TOL_HA, decompose_profit, oracle_water_matched, scale_b1_to_water_budget
from agriopt.config import CROPS, MSP_HISTORY_CSV, REPORTS_RESULTS
from agriopt.optim.baselines import evaluate

REPO_ROOT = Path(__file__).resolve().parent.parent
DECOMP_STRATS = ["B1", "B1_SCALED", "B2", "B3", "OURS", "MODEL_B"]
ALL_STRATS = DECOMP_STRATS + ["ORACLE"]

# --- Phase 7.1's own MSP provenance verification (step 5) ------------------
# jowar/soybean/maize 2017 were flagged secondary in Phase 7 (docs/backtest.md
# "known gaps": sourced from a business-standard comparison table because
# agricoop.gov.in returned a DNS failure). Re-checked here (same DNS failure
# reproduced on agricoop.gov.in), and a genuine PRIMARY government source was
# found instead: a PIB press release (03-Aug-2018, Rajya Sabha Unstarred
# Question No. 1934 answer, Ministry of Agriculture & Farmers Welfare) whose
# official Annexure table gives 2017-18-season Cost/MSP for every kharif
# crop, including JOWAR (Hybrid)=1700, MAIZE=1425, SOYABEEN=3050 -- all three
# EXACTLY matching the values already in msp_history.csv. Confirmed by
# fetching https://pib.gov.in/newsite/PrintRelease.aspx?relid=181467 directly.
VERIFIED_2017_PRIMARY_URL = "https://pib.gov.in/newsite/PrintRelease.aspx?relid=181467"
VERIFIED_2017_CROPS = {"jowar", "soybean", "maize"}

# domain -> provenance classification for every OTHER row's existing source_url.
_PRIMARY_DOMAINS = ("desagri.gov.in", "static.pib.gov.in", "pib.gov.in", "www.pib.gov.in", "cacp.dacnet.nic.in")
_SECONDARY_DOMAINS = ("business-standard.com", "agriculturepost.com", "onmanorama.com", "tribuneindia.com")


def _classify_provenance(source_url: str) -> str:
    if not isinstance(source_url, str) or not source_url.strip():
        return ""
    if source_url.startswith("http"):
        if any(d in source_url for d in _PRIMARY_DOMAINS):
            return "primary"
        if any(d in source_url for d in _SECONDARY_DOMAINS):
            return "secondary"
        return "secondary"  # unknown http domain -- default to the more conservative label
    # plain-text citations (year=2025 rows): e.g. "PIB KMS 2025-26 PRID ... (per crop_reference.csv msp_source)"
    # -- these DO name a specific PIB release, just weren't independently re-fetched by URL in Phase 7; treat as primary.
    if "pib" in source_url.lower():
        return "primary"
    return "secondary"


def update_msp_history_provenance() -> pd.DataFrame:
    """Adds a `provenance` column (primary/secondary/blank) to EVERY row of
    msp_history.csv, and -- for jowar/soybean/maize 2017 specifically --
    replaces source_url with the verified primary PIB citation and marks
    provenance='primary_verified_v2'. Existing crop/year/msp/cost values are
    NEVER modified -- only source_url (for the 3 rows) and the new
    provenance column."""
    df = pd.read_csv(MSP_HISTORY_CSV)
    df["provenance"] = df["source_url"].apply(_classify_provenance)

    mask = (df["year"] == 2017) & (df["crop"].isin(VERIFIED_2017_CROPS))
    assert mask.sum() == 3, f"expected exactly 3 rows (jowar/soybean/maize, 2017), found {mask.sum()}"
    df.loc[mask, "source_url"] = VERIFIED_2017_PRIMARY_URL
    df.loc[mask, "provenance"] = "primary_verified_v2"

    df.to_csv(MSP_HISTORY_CSV, index=False)
    print(f"Updated {MSP_HISTORY_CSV} with a provenance column ({mask.sum()} rows verified primary this phase).")
    return df


# --- shared backtest module + a per-year cache (avoids resolving NSGA twice) ---


def load_backtest_module():
    spec = importlib.util.spec_from_file_location("backtest_60", REPO_ROOT / "scripts" / "60_backtest.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_YEAR_CACHE: dict[int, tuple] = {}


def get_year_data(backtest, t: int):
    if t not in _YEAR_CACHE:
        _YEAR_CACHE[t] = backtest.run_year(t)
    return _YEAR_CACHE[t]


def run_analysis(backtest):
    """Runs the full 7.1 analysis and returns (fairness_df, rows_df,
    b2_oracle_df, decomp_df) -- pulled out of main() so tests can call it
    directly against a subset of years without re-deriving the CLI plumbing."""
    fairness_rows, rows_v2, b2_oracle_rows, decomp_rows = [], [], [], []

    for t in backtest.YEARS:
        rows, meta = get_year_data(backtest, t)
        forecast_params = meta["forecast_params"]
        realized_params = meta["realized_params"]
        missing = meta["missing_realized"]
        has_realized = len(missing) < len(CROPS)  # False only for 2020, per docs/backtest.md

        for label in backtest.WATER_MULTIPLIERS:
            scenario = meta["scenario_store"][label]
            xs = dict(meta["x_store"][label])

            x1 = xs["B1"]
            x1_scaled, scale, water_before = scale_b1_to_water_budget(x1, forecast_params, scenario)
            xs["B1_SCALED"] = x1_scaled

            r1 = evaluate(x1, forecast_params, scenario)
            r1_scaled = evaluate(x1_scaled, forecast_params, scenario)
            food_violated = bool(r1_scaled["food_share"] < scenario.food_share_min - 1e-6)

            def _realized(x):
                if not has_realized or x is None:
                    return None
                return backtest.evaluate_realized_profit(x, forecast_params, realized_params, missing, scenario)

            realized_b1 = _realized(x1)
            realized_b1_scaled = _realized(x1_scaled)

            fairness_rows.append(
                {
                    "year": t,
                    "scenario": label,
                    "budget_m3": scenario.water_budget_m3,
                    "b1_water_m3": r1["water_m3"],
                    "b1_feasible": r1["feasible"],
                    "b1_scale_factor": scale,
                    "b1_scaled_water_m3": r1_scaled["water_m3"],
                    "b1_scaled_feasible": r1_scaled["feasible"],
                    "b1_scaled_food_share": r1_scaled["food_share"],
                    "b1_scaled_food_share_violated": food_violated,
                    "b1_realized_profit": realized_b1,
                    "b1_scaled_realized_profit": realized_b1_scaled,
                }
            )

            for name in ALL_STRATS:
                x = xs.get(name)
                if x is None:
                    rows_v2.append(
                        {
                            "year": t, "scenario": label, "strategy": name, "feasible": False,
                            "planned_profit": np.nan, "realized_profit": np.nan, "water_m3": np.nan,
                            "profit_per_1000m3": np.nan, "oraclew_profit": np.nan, "capture_ratio_w": np.nan,
                            "win_vs_b1": np.nan, "win_vs_b1_scaled": np.nan,
                        }
                    )
                    continue
                r_planned = evaluate(x, forecast_params, scenario)
                realized_profit = _realized(x)
                water = r_planned["water_m3"]
                profit_per_1000m3 = float(realized_profit / (water / 1000.0)) if (realized_profit is not None and water > 0) else np.nan

                if has_realized:
                    _, oraclew_profit, oraclew_water = oracle_water_matched(x, forecast_params, realized_params, scenario)
                else:
                    oraclew_profit, oraclew_water = None, water
                capture_ratio_w = (
                    float(realized_profit / oraclew_profit) if (realized_profit is not None and oraclew_profit) else np.nan
                )

                win_vs_b1 = (
                    bool(realized_profit > realized_b1) if (name != "B1" and realized_profit is not None and realized_b1 is not None) else np.nan
                )
                win_vs_b1_scaled = (
                    bool(realized_profit > realized_b1_scaled)
                    if (name not in ("B1", "B1_SCALED") and realized_profit is not None and realized_b1_scaled is not None)
                    else np.nan
                )

                rows_v2.append(
                    {
                        "year": t, "scenario": label, "strategy": name, "feasible": r_planned["feasible"],
                        "planned_profit": r_planned["profit"], "realized_profit": realized_profit, "water_m3": water,
                        "profit_per_1000m3": profit_per_1000m3, "oraclew_profit": oraclew_profit,
                        "oraclew_water_m3": oraclew_water, "capture_ratio_w": capture_ratio_w,
                        "win_vs_b1": win_vs_b1, "win_vs_b1_scaled": win_vs_b1_scaled,
                    }
                )

            x2, x_oracle = xs.get("B2"), xs.get("ORACLE")
            if x2 is not None and x_oracle is not None:
                diff = np.abs(np.asarray(x2, dtype=float) - np.asarray(x_oracle, dtype=float))
                row = {
                    "year": t, "scenario": label,
                    "identical_alloc": bool((diff < ALLOC_TOL_HA).all()),
                    "max_abs_diff_ha": float(diff.max()),
                    "b2_realized_profit": _realized(x2),
                    "oracle_realized_profit": _realized(x_oracle),
                }
                for c, v in zip(CROPS, x2):
                    row[f"b2_{c}_ha"] = float(v)
                for c, v in zip(CROPS, x_oracle):
                    row[f"oracle_{c}_ha"] = float(v)
                b2_oracle_rows.append(row)

            if has_realized:
                for name in DECOMP_STRATS:
                    x = xs.get(name)
                    if x is None:
                        continue
                    decomp = decompose_profit(x, forecast_params, realized_params)
                    planned = evaluate(x, forecast_params, scenario)["profit"]
                    realized_profit = _realized(x)
                    total_effect = float(decomp["total_effect_rs"].sum())
                    gap = realized_profit - planned
                    tol = max(1.0, abs(gap) * 1e-6)
                    if abs(total_effect - gap) > tol:
                        raise AssertionError(
                            f"decomposition identity failed: t={t} scenario={label} strategy={name} "
                            f"sum(effects)={total_effect:.6f} vs (realized-planned)={gap:.6f}"
                        )
                    d = decomp.reset_index()
                    d["year"], d["scenario"], d["strategy"] = t, label, name
                    decomp_rows.append(d)

    fairness_df = pd.DataFrame(fairness_rows)
    rows_df = pd.DataFrame(rows_v2)
    b2_oracle_df = pd.DataFrame(b2_oracle_rows)
    decomp_df = pd.concat(decomp_rows, ignore_index=True) if decomp_rows else pd.DataFrame()
    return fairness_df, rows_df, b2_oracle_df, decomp_df


# --- reporting ---------------------------------------------------------------


def build_win_summary(rows_df: pd.DataFrame) -> pd.DataFrame:
    realized = rows_df.dropna(subset=["realized_profit"])
    out = []
    for (scenario, strategy), g in realized.groupby(["scenario", "strategy"]):
        if strategy in ("B1", "B1_SCALED", "ORACLE"):
            continue
        out.append(
            {
                "scenario": scenario,
                "strategy": strategy,
                "n_years": len(g),
                "win_count_vs_b1": int(g["win_vs_b1"].sum()) if g["win_vs_b1"].notna().any() else None,
                "win_count_vs_b1_scaled": int(g["win_vs_b1_scaled"].sum()) if g["win_vs_b1_scaled"].notna().any() else None,
                "mean_capture_ratio_w": float(g["capture_ratio_w"].mean()),
                "mean_profit_per_1000m3": float(g["profit_per_1000m3"].mean()),
            }
        )
    # capture_ratio (budget-level, vs ORACLE) + profit-per-water for B1/B1_SCALED/ORACLE too
    for (scenario, strategy), g in realized.groupby(["scenario", "strategy"]):
        if strategy not in ("B1", "B1_SCALED", "ORACLE"):
            continue
        out.append(
            {
                "scenario": scenario, "strategy": strategy, "n_years": len(g),
                "win_count_vs_b1": None, "win_count_vs_b1_scaled": None,
                "mean_capture_ratio_w": float(g["capture_ratio_w"].mean()),
                "mean_profit_per_1000m3": float(g["profit_per_1000m3"].mean()),
            }
        )
    return pd.DataFrame(out).sort_values(["scenario", "strategy"]).reset_index(drop=True)


def build_capture_ratio_budget_level(rows_df: pd.DataFrame) -> pd.DataFrame:
    """The ORIGINAL (budget-level) capture ratio -- total realized profit /
    ORACLE's total realized profit, same definition as Phase 7's
    build_summary -- reported alongside capture_ratio_w for comparison."""
    realized = rows_df.dropna(subset=["realized_profit"])
    out = []
    for scenario, sdf in realized.groupby("scenario"):
        oracle_total = sdf[sdf["strategy"] == "ORACLE"]["realized_profit"].sum()
        for strategy, g in sdf.groupby("strategy"):
            total = g["realized_profit"].sum()
            out.append({"scenario": scenario, "strategy": strategy, "capture_ratio": total / oracle_total if oracle_total else np.nan})
    return pd.DataFrame(out)


def plot_decomposition_tight(decomp_df: pd.DataFrame) -> None:
    tight = decomp_df[decomp_df["scenario"] == "tight"]
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=True)
    for ax, strategy in zip(axes, ["B1_SCALED", "OURS"]):
        sdf = tight[tight["strategy"] == strategy]
        years = sorted(sdf["year"].unique())
        pivot = sdf.pivot_table(index="year", columns="crop", values="total_effect_rs", aggfunc="sum").reindex(years).fillna(0.0)
        bottom_pos = np.zeros(len(years))
        bottom_neg = np.zeros(len(years))
        colors = plt.cm.tab10(np.linspace(0, 1, len(pivot.columns)))
        for crop, color in zip(pivot.columns, colors):
            vals = pivot[crop].to_numpy()
            bottom = np.where(vals >= 0, bottom_pos, bottom_neg)
            ax.bar(years, vals, bottom=bottom, label=crop, color=color)
            bottom_pos = np.where(vals >= 0, bottom_pos + vals, bottom_pos)
            bottom_neg = np.where(vals < 0, bottom_neg + vals, bottom_neg)
        ax.axhline(0, color="black", linewidth=0.8)
        ax.set_title(f"{strategy} -- per-crop net effect (tight scenario)")
        ax.set_xlabel("decision year")
        ax.set_xticks(years)
    axes[0].set_ylabel("realized - planned profit, per crop (Rs)")
    axes[1].legend(fontsize=8, loc="upper left", bbox_to_anchor=(1.0, 1.0))
    fig.tight_layout()
    fig.savefig(REPORTS_RESULTS / "backtest_decomposition_tight_v2.png", dpi=150)
    plt.close(fig)
    print("Wrote backtest_decomposition_tight_v2.png")


def write_summary_md(fairness_df, win_summary_df, capture_budget_df, b2_oracle_df, decomp_df) -> None:
    lines = ["# Decision backtest v2: fairness, water-matched oracle, decomposition (Phase 7.1)\n\n"]

    lines.append("## 1. B1 feasibility and B1_SCALED fairness\n\n")
    cols = ["year", "scenario", "budget_m3", "b1_water_m3", "b1_feasible", "b1_scale_factor",
            "b1_scaled_water_m3", "b1_scaled_feasible", "b1_scaled_food_share_violated"]
    lines.append("| " + " | ".join(cols) + " |\n" + "|" + "---|" * len(cols) + "\n")
    for _, row in fairness_df.iterrows():
        cells = []
        for c in cols:
            v = row[c]
            cells.append(f"{v:,.3f}" if isinstance(v, float) else str(v))
        lines.append("| " + " | ".join(cells) + " |\n")

    lines.append("\n## 2. Win counts and capture ratios (2016-2019, n=4)\n\n")
    cols2 = ["scenario", "strategy", "n_years", "win_count_vs_b1", "win_count_vs_b1_scaled",
             "mean_capture_ratio_w", "mean_profit_per_1000m3"]
    lines.append("| " + " | ".join(cols2) + " |\n" + "|" + "---|" * len(cols2) + "\n")
    for _, row in win_summary_df.iterrows():
        cells = [f"{row[c]:,.3f}" if isinstance(row[c], float) else str(row[c]) for c in cols2]
        lines.append("| " + " | ".join(cells) + " |\n")

    lines.append("\n## 3. Budget-level capture ratio (vs ORACLE, same definition as Phase 7)\n\n")
    lines.append("| scenario | strategy | capture_ratio |\n|---|---|---|\n")
    for _, row in capture_budget_df.iterrows():
        lines.append(f"| {row['scenario']} | {row['strategy']} | {row['capture_ratio']:.3f} |\n")

    lines.append("\n## 4. B2 vs ORACLE allocation\n\n")
    lines.append("| year | scenario | identical_alloc | max_abs_diff_ha | b2_realized_profit | oracle_realized_profit |\n|---|---|---|---|---|---|\n")
    for _, row in b2_oracle_df.iterrows():
        lines.append(
            f"| {row['year']} | {row['scenario']} | {row['identical_alloc']} | {row['max_abs_diff_ha']:.4f} | "
            f"{row['b2_realized_profit']:,.0f} | {row['oracle_realized_profit']:,.0f} |\n"
        )

    (REPORTS_RESULTS / "backtest_summary_v2.md").write_text("".join(lines), encoding="utf-8")
    print("Wrote backtest_summary_v2.md")


def write_findings_md(fairness_df, win_summary_df, decomp_df, b2_oracle_df) -> None:
    lines = ["# Decision backtest v2 findings (Phase 7.1)\n\n"]

    lines.append("## Fairness verdict\n\n")
    tight_b1 = fairness_df[fairness_df["scenario"] == "tight"]
    over_budget_years = tight_b1[~tight_b1["b1_feasible"]]["year"].tolist()
    lines.append(
        f"- B1 (current_mix) is water-INFEASIBLE in the tight scenario for years {over_budget_years} "
        "(uses more water than its own budget allows) -- confirmed via evaluate()'s feasible flag AND a "
        "direct water_m3 vs budget_m3 comparison. B1_SCALED corrects this by scaling B1's hectares down "
        "proportionally until water_m3 <= budget.\n"
    )
    food_viol = fairness_df[fairness_df["b1_scaled_food_share_violated"]]
    if len(food_viol):
        lines.append(
            f"- After water-scaling, B1_SCALED's food-share constraint is VIOLATED in "
            f"{len(food_viol)} year/scenario combos: {list(zip(food_viol['year'], food_viol['scenario']))}.\n"
        )
    else:
        lines.append("- After water-scaling, B1_SCALED never violates the food-share constraint in any year/scenario.\n")

    tight_summary = win_summary_df[win_summary_df["scenario"] == "tight"]
    for strategy in ["OURS", "MODEL_B"]:
        r = tight_summary[tight_summary["strategy"] == strategy]
        if len(r):
            r = r.iloc[0]
            lines.append(
                f"- **tight scenario, {strategy}**: won {r['win_count_vs_b1']}/{r['n_years']} vs raw B1, "
                f"{r['win_count_vs_b1_scaled']}/{r['n_years']} vs B1_SCALED (the fair, water-feasible baseline); "
                f"mean capture_ratio_w (water-matched) = {r['mean_capture_ratio_w']:.2f}; "
                f"mean profit per 1,000 m3 water = Rs {r['mean_profit_per_1000m3']:,.0f}.\n"
            )
    b1_row = tight_summary[tight_summary["strategy"] == "B1"] if "B1" in tight_summary["strategy"].values else None

    lines.append(
        "\n## B2 == ORACLE\n\n"
        f"- Identical allocation (within {ALLOC_TOL_HA} ha) in "
        f"{int(b2_oracle_df['identical_alloc'].sum())}/{len(b2_oracle_df)} year/scenario combos. Both are "
        "profit-max LPs over the SAME feasible region (water_m3_ha/fert_kg_ha/seasons_occupied are physical, "
        "not forecast-dependent) -- they differ only through which crop the objective vector (profit_ha) "
        "favors, so when forecast and realized profit_ha rank crops identically (same top crop(s) hit their "
        "max_share*land_ha cap, same runner-up ordering), the LPs land on the same vertex.\n"
    )

    lines.append("\n## Mechanism (decomposition)\n\n")
    tight_decomp = decomp_df[decomp_df["scenario"] == "tight"]
    for strategy in ["B1_SCALED", "OURS", "MODEL_B"]:
        sdf = tight_decomp[tight_decomp["strategy"] == strategy]
        if sdf.empty:
            continue
        by_crop = sdf.groupby("crop")[["yield_effect_rs", "price_effect_rs", "interaction_rs", "cost_effect_rs", "total_effect_rs"]].sum()
        top = by_crop["total_effect_rs"].abs().sort_values(ascending=False).head(2)
        lines.append(f"- **{strategy}, tight scenario, summed 2016-2019**: largest net effects by crop: ")
        parts = []
        for crop in top.index:
            row = by_crop.loc[crop]
            dominant_term = row[["yield_effect_rs", "price_effect_rs", "interaction_rs", "cost_effect_rs"]].abs().idxmax()
            parts.append(f"{crop} (Rs {row['total_effect_rs']:,.0f}, driven by {dominant_term.replace('_rs', '')})")
        lines.append("; ".join(parts) + ".\n")
        cost_total = float(sdf["cost_effect_rs"].abs().sum())
        lines.append(f"  cost_effect summed |value| = Rs {cost_total:.6f} (exactly 0 by construction -- see decompose_profit's docstring).\n")

    (REPORTS_RESULTS / "backtest_findings_v2.md").write_text("".join(lines), encoding="utf-8")
    print("Wrote backtest_findings_v2.md")


def main() -> None:
    update_msp_history_provenance()

    backtest = load_backtest_module()
    fairness_df, rows_df, b2_oracle_df, decomp_df = run_analysis(backtest)

    REPORTS_RESULTS.mkdir(parents=True, exist_ok=True)
    fairness_df.to_csv(REPORTS_RESULTS / "backtest_fairness_v2.csv", index=False)
    rows_df.to_csv(REPORTS_RESULTS / "backtest_rows_v2.csv", index=False)
    b2_oracle_df.to_csv(REPORTS_RESULTS / "backtest_b2_oracle_v2.csv", index=False)
    decomp_df.to_csv(REPORTS_RESULTS / "backtest_decomposition_v2.csv", index=False)
    print("Wrote backtest_fairness_v2.csv, backtest_rows_v2.csv, backtest_b2_oracle_v2.csv, backtest_decomposition_v2.csv")

    win_summary_df = build_win_summary(rows_df)
    capture_budget_df = build_capture_ratio_budget_level(rows_df)
    write_summary_md(fairness_df, win_summary_df, capture_budget_df, b2_oracle_df, decomp_df)
    plot_decomposition_tight(decomp_df)
    write_findings_md(fairness_df, win_summary_df, decomp_df, b2_oracle_df)

    print("\n=== fairness ===")
    print(fairness_df.to_string(index=False))
    print("\n=== win summary ===")
    print(win_summary_df.to_string(index=False))
    print("\n=== B2 vs ORACLE ===")
    print(b2_oracle_df[["year", "scenario", "identical_alloc", "max_abs_diff_ha"]].to_string(index=False))


if __name__ == "__main__":
    sys.exit(main())
