"""Phase 5 / Experiment 4: information ablation.

For each crop-params VARIANT (FULL, NO_ML_YIELD, MSP_PRICE, MEAN_PRICE,
NO_COST) and each water scenario (tight, current): decide an allocation
using the VARIANT's params, then EVALUATE that allocation under FULL params
-- i.e. "how much does using worse/partial information cost you, once
judged against the best information we have?"

Two different metrics for two different kinds of solver (Phase 5.1 fix):
  - B2 (profit-max LP) and B3 (same-profit-min-water LP) are EXACT solvers
    over an IDENTICAL feasible region across all variants (only the profit
    objective's coefficients change; water/fert per-ha figures don't depend
    on yield/price/cost) -- so the FULL decision is provably the best
    achievable profit under FULL params, and any other variant's decision,
    evaluated under FULL params, can only do as well or worse. Reported as
    profit loss (Rs and %) vs the FULL decision -- guaranteed >=0 for B2
    (asserted), not guaranteed for B3 (its target profit itself shifts per
    variant, so the comparison isn't apples-to-apples in the same way).
  - OURS (NSGA-II) is a heuristic, not an exact solver, so a raw profit-loss
    number would conflate "worse information" with "NSGA-II didn't fully
    converge." Instead: is the variant's plan, evaluated under FULL params,
    DOMINATED by the FULL plan on (profit, water, fert)? Plus the deltas.

Writes reports/results/ablation_decisions.md/.csv. Does not touch any
Phase 1-3 report files.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from agriopt.config import CROPS, MAIN_SEASON, REPORTS_RESULTS, STATE, YIELD_CLEAN_PARQUET, YIELD_TO_SALEABLE_QTL_PER_HA
from agriopt.data.reference import cost_rs_per_ha, load_reference
from agriopt.models.price_model import build_wide_price_table, load_price_frame
from agriopt.models.yield_model import CANON_TO_YIELD_NAME
from agriopt.optim.baselines import current_mix, evaluate, nsga2_recommended, same_profit_min_water
from agriopt.optim.params import build_crop_params
from agriopt.optim.problem import Scenario
from agriopt.optim.solvers import solve_lp_profit_max

B2_LOSS_TOL = 1e-3  # relative tolerance for the B2 loss>=0 assertion (LP/float noise)
DOMINANCE_TOL = 1e-6

WATER_MULTIPLIERS = {"tight": 0.7, "current": 1.0}
LAND_HA = 10.0
MEAN_PRICE_LOOKBACK_MONTHS = 60  # 5 years
NO_ML_YIELD_LOOKBACK_YEARS = 10


# --- Variant builders (each returns a params_df with the same schema as build_crop_params) ---


def variant_full(full_params: pd.DataFrame, **kwargs) -> pd.DataFrame:
    return full_params.copy()


def variant_no_ml_yield(full_params: pd.DataFrame, crops: list[str] = CROPS, state: str = STATE, **kwargs) -> pd.DataFrame:
    """yield = Maharashtra historical mean saleable yield, last 10 years,
    instead of the ML model's prediction. Cost/profit/profit_std are
    recomputed to stay consistent with the new yield (cost and profit_std
    both scale with yield in the FULL pipeline -- see agriopt.optim.params)."""
    df = pd.read_parquet(YIELD_CLEAN_PARQUET)
    ref = load_reference()
    out = full_params.copy()
    for crop in crops:
        name = CANON_TO_YIELD_NAME[crop]
        season = MAIN_SEASON[crop]
        sub = df[(df["state"] == state) & (df["crop"] == name) & (df["season"] == season)]
        by_year = sub.groupby("year")["yield"].mean().sort_index()
        recent = by_year.tail(NO_ML_YIELD_LOOKBACK_YEARS)
        mean_dataset_yield = float(recent.mean())
        new_yield = YIELD_TO_SALEABLE_QTL_PER_HA[crop](mean_dataset_yield)

        old_yield = float(full_params.loc[crop, "yield_qtl_ha"])
        price_std_per_qtl = float(full_params.loc[crop, "profit_std_ha"]) / old_yield if old_yield else 0.0

        cost_ha = cost_rs_per_ha(crop, new_yield, ref)
        out.loc[crop, "yield_qtl_ha"] = new_yield
        out.loc[crop, "cost_ha"] = cost_ha
        out.loc[crop, "profit_ha"] = new_yield * full_params.loc[crop, "price"] - cost_ha
        out.loc[crop, "profit_std_ha"] = new_yield * price_std_per_qtl
    return out


def variant_msp_price(full_params: pd.DataFrame, crops: list[str] = CROPS, **kwargs) -> pd.DataFrame:
    """price = MSP (or FRP for sugarcane) ALWAYS, not just as a floor."""
    ref = load_reference().set_index("crop")
    out = full_params.copy()
    for crop in crops:
        row = ref.loc[crop]
        price = float(row["msp_rs_per_qtl"]) if pd.notna(row["msp_rs_per_qtl"]) else float(row["admin_price_rs_per_qtl"])
        cost_ha = float(out.loc[crop, "cost_ha"])
        out.loc[crop, "price"] = price
        out.loc[crop, "profit_ha"] = float(out.loc[crop, "yield_qtl_ha"]) * price - cost_ha
    return out


def variant_mean_price(full_params: pd.DataFrame, crops: list[str] = CROPS, **kwargs) -> pd.DataFrame:
    """price = 5-year mean modal price instead of the h=12 forecast.
    Sugarcane has no mandi series -- kept at its FRP (same as FULL), as
    with the rest of this pipeline's sugarcane handling."""
    price_df = load_price_frame()
    wide = build_wide_price_table(price_df)
    out = full_params.copy()
    for crop in crops:
        if crop == "sugarcane":
            continue
        series = wide[crop].dropna().tail(MEAN_PRICE_LOOKBACK_MONTHS)
        price = float(series.mean())
        cost_ha = float(out.loc[crop, "cost_ha"])
        out.loc[crop, "price"] = price
        out.loc[crop, "profit_ha"] = float(out.loc[crop, "yield_qtl_ha"]) * price - cost_ha
    return out


def variant_no_cost(full_params: pd.DataFrame, **kwargs) -> pd.DataFrame:
    out = full_params.copy()
    out["cost_ha"] = 0.0
    out["profit_ha"] = out["yield_qtl_ha"] * out["price"]
    return out


VARIANTS = {
    "FULL": variant_full,
    "NO_ML_YIELD": variant_no_ml_yield,
    "MSP_PRICE": variant_msp_price,
    "MEAN_PRICE": variant_mean_price,
    "NO_COST": variant_no_cost,
}


def compute_b1_water(full_params: pd.DataFrame, land_ha: float = LAND_HA) -> float:
    dummy = Scenario(water_budget_m3=1e15, land_ha=land_ha)
    x1 = current_mix(full_params, dummy)
    return float(x1 @ full_params["water_m3_ha"].to_numpy())


def decide(params_df: pd.DataFrame, scenario: Scenario) -> dict:
    x_ours, _, _, _ = nsga2_recommended(params_df, scenario, seed=0)
    x_b2, _ = solve_lp_profit_max(scenario, params_df)

    x1 = current_mix(params_df, scenario)
    r1 = evaluate(x1, params_df, scenario)
    x_b3 = same_profit_min_water(params_df, scenario, min_profit=r1["profit"])

    return {"OURS": x_ours, "B2": x_b2, "B3": x_b3}


def _lp_strategy_row(variant_name: str, water_label: str, strategy: str, x_variant, x_full_ref, full_params: pd.DataFrame, scenario: Scenario) -> dict:
    if x_variant is None or x_full_ref is None:
        return {"variant": variant_name, "water_scenario": water_label, "strategy": strategy, "feasible": False}

    r_eval = evaluate(x_variant, full_params, scenario)
    r_full_ref = evaluate(x_full_ref, full_params, scenario)
    loss_rs = r_full_ref["profit"] - r_eval["profit"]
    loss_pct = loss_rs / abs(r_full_ref["profit"]) * 100 if r_full_ref["profit"] else float("nan")
    l1_dist = float(np.abs(x_variant - x_full_ref).sum())

    if strategy == "B2":
        tol = B2_LOSS_TOL * max(1.0, abs(r_full_ref["profit"]))
        assert loss_rs >= -tol, (
            f"B2 ablation loss should be >=0 (FULL's LP decision is optimal under FULL params over an identical "
            f"feasible region) but got {loss_rs:.2f} for variant={variant_name}, water={water_label}"
        )

    return {
        "variant": variant_name,
        "water_scenario": water_label,
        "strategy": strategy,
        "profit_under_full": r_eval["profit"],
        "profit_loss_rs_vs_full": loss_rs,
        "profit_loss_pct_vs_full": loss_pct,
        "water_m3": r_eval["water_m3"],
        "fert_kg": r_eval["fert_kg"],
        "allocation_l1_dist_ha": l1_dist,
        "feasible": r_eval["feasible"],
    }


def _ours_row(variant_name: str, water_label: str, x_variant, x_full_ref, full_params: pd.DataFrame, scenario: Scenario) -> dict:
    if x_variant is None or x_full_ref is None:
        return {"variant": variant_name, "water_scenario": water_label, "strategy": "OURS", "feasible": False}

    r_eval = evaluate(x_variant, full_params, scenario)
    r_full_ref = evaluate(x_full_ref, full_params, scenario)

    def pct(new, base):
        return (new - base) / abs(base) * 100 if base else float("nan")

    profit_delta_pct = pct(r_eval["profit"], r_full_ref["profit"])
    water_delta_pct = pct(r_eval["water_m3"], r_full_ref["water_m3"])
    fert_delta_pct = pct(r_eval["fert_kg"], r_full_ref["fert_kg"])

    profit_ge = r_full_ref["profit"] >= r_eval["profit"] - DOMINANCE_TOL * max(1.0, abs(r_eval["profit"]))
    water_le = r_full_ref["water_m3"] <= r_eval["water_m3"] + DOMINANCE_TOL * max(1.0, r_eval["water_m3"])
    fert_le = r_full_ref["fert_kg"] <= r_eval["fert_kg"] + DOMINANCE_TOL * max(1.0, r_eval["fert_kg"])
    strictly_better = (
        r_full_ref["profit"] > r_eval["profit"] + DOMINANCE_TOL * max(1.0, abs(r_eval["profit"]))
        or r_full_ref["water_m3"] < r_eval["water_m3"] - DOMINANCE_TOL * max(1.0, r_eval["water_m3"])
        or r_full_ref["fert_kg"] < r_eval["fert_kg"] - DOMINANCE_TOL * max(1.0, r_eval["fert_kg"])
    )
    dominated_by_full = bool(profit_ge and water_le and fert_le and strictly_better)

    l1_dist = float(np.abs(x_variant - x_full_ref).sum())

    return {
        "variant": variant_name,
        "water_scenario": water_label,
        "strategy": "OURS",
        "profit_under_full": r_eval["profit"],
        "dominated_by_full": dominated_by_full,
        "profit_pct_vs_full": profit_delta_pct,
        "water_pct_vs_full": water_delta_pct,
        "fert_pct_vs_full": fert_delta_pct,
        "allocation_l1_dist_ha": l1_dist,
        "feasible": r_eval["feasible"],
    }


def _markdown_table(df: pd.DataFrame, cols: list[str]) -> str:
    lines = ["| " + " | ".join(cols) + " |\n", "|" + "---|" * len(cols) + "\n"]
    for _, row in df.iterrows():
        cells = []
        for c in cols:
            v = row.get(c, np.nan)
            if isinstance(v, bool):
                cells.append(str(v))
            elif isinstance(v, float):
                cells.append(f"{v:.2f}" if not np.isnan(v) else "-")
            else:
                cells.append(str(v) if pd.notna(v) else "-")
        lines.append("| " + " | ".join(cells) + " |\n")
    return "".join(lines)


def main() -> None:
    REPORTS_RESULTS.mkdir(parents=True, exist_ok=True)

    full_params = build_crop_params("market", verbose=False)
    b1_water = compute_b1_water(full_params)
    water_budgets = {label: mult * b1_water for label, mult in WATER_MULTIPLIERS.items()}
    print(f"B1 water usage: {b1_water:.1f} m3; budgets: {water_budgets}")

    variant_params = {name: builder(full_params) for name, builder in VARIANTS.items()}

    lp_rows, ours_rows = [], []
    for water_label, wb in water_budgets.items():
        scenario = Scenario(water_budget_m3=wb, land_ha=LAND_HA, price_mode="market")
        print(f"\n-- water={water_label} --")

        full_decisions = decide(variant_params["FULL"], scenario)

        for variant_name, params_variant in variant_params.items():
            print(f"  variant={variant_name} ...")
            decisions = decide(params_variant, scenario) if variant_name != "FULL" else full_decisions

            for strategy in ["B2", "B3"]:
                lp_rows.append(_lp_strategy_row(variant_name, water_label, strategy, decisions[strategy], full_decisions[strategy], full_params, scenario))

            ours_rows.append(_ours_row(variant_name, water_label, decisions["OURS"], full_decisions["OURS"], full_params, scenario))

    lp_df = pd.DataFrame(lp_rows)
    ours_df = pd.DataFrame(ours_rows)
    lp_df.to_csv(REPORTS_RESULTS / "ablation_decisions_lp.csv", index=False)
    ours_df.to_csv(REPORTS_RESULTS / "ablation_decisions_ours.csv", index=False)
    pd.concat([lp_df, ours_df], ignore_index=True).to_csv(REPORTS_RESULTS / "ablation_decisions.csv", index=False)

    lines = ["# Information ablation (Phase 5.1, Experiment 4)\n\n"]
    lines.append(
        "Each variant DECIDES an allocation using its own (degraded) view of crop params, then that allocation "
        "is EVALUATED under FULL params -- this measures the real cost of deciding with worse information, not "
        "just how the params themselves differ. B2/B3 (exact LP solvers, identical feasible region across "
        "variants) are compared by profit loss vs the FULL decision; OURS (NSGA-II, a heuristic) is compared by "
        "Pareto dominance on (profit, water, fert), since a raw profit-loss number would conflate 'worse "
        "information' with 'NSGA-II didn't fully converge.'\n\n"
    )

    lines.append("## B2 (profit-max LP) and B3 (same-profit-min-water LP)\n\n")
    lp_cols = ["variant", "water_scenario", "strategy", "profit_under_full", "profit_loss_rs_vs_full", "profit_loss_pct_vs_full", "water_m3", "fert_kg", "allocation_l1_dist_ha", "feasible"]
    lines.append(_markdown_table(lp_df, lp_cols))

    lines.append("\n## OURS (NSGA-II): dominance vs the FULL decision\n\n")
    ours_cols = ["variant", "water_scenario", "strategy", "profit_under_full", "dominated_by_full", "profit_pct_vs_full", "water_pct_vs_full", "fert_pct_vs_full", "allocation_l1_dist_ha", "feasible"]
    lines.append(_markdown_table(ours_df, ours_cols))

    lines.append("\n## Findings\n\n")

    b2_df = lp_df[(lp_df["strategy"] == "B2") & (lp_df["variant"] != "FULL") & lp_df["feasible"]]
    b3_df = lp_df[(lp_df["strategy"] == "B3") & (lp_df["variant"] != "FULL") & lp_df["feasible"]]
    b2_by_variant = None
    if not b2_df.empty:
        b2_by_variant = b2_df.groupby("variant").agg(mean_loss_pct=("profit_loss_pct_vs_full", "mean"), mean_l1=("allocation_l1_dist_ha", "mean"))
        worst_b2 = b2_by_variant["mean_loss_pct"].idxmax()
        lines.append(
            f"- **B2 (exact profit-max LP), by profit loss**: **{worst_b2}** costs the most "
            f"({b2_by_variant.loc[worst_b2, 'mean_loss_pct']:+.1f}% vs the FULL-information decision, mean over "
            "water scenarios). All B2 losses are >=0 by construction (asserted in code) -- the FULL decision is "
            "the true profit-max over an identical feasible region, so any other variant's B2 decision can only "
            "do as well or worse once judged under FULL params.\n"
        )
        for variant in b2_by_variant.index:
            row = b2_by_variant.loc[variant]
            lines.append(f"  - {variant}: mean profit loss {row['mean_loss_pct']:+.1f}%, mean allocation shift {row['mean_l1']:.2f} ha.\n")

    if not b3_df.empty:
        b3_by_variant = b3_df.groupby("variant").agg(mean_loss_pct=("profit_loss_pct_vs_full", "mean"), mean_l1=("allocation_l1_dist_ha", "mean"))
        lines.append("\n- **B3 (same-profit-min-water LP)**, mean profit loss / allocation shift per variant (not guaranteed >=0 -- each variant targets its OWN B1 profit level, not FULL's):\n")
        for variant in b3_by_variant.index:
            row = b3_by_variant.loc[variant]
            lines.append(f"  - {variant}: mean profit loss {row['mean_loss_pct']:+.1f}%, mean allocation shift {row['mean_l1']:.2f} ha.\n")

    n_dominated = int(ours_df[(ours_df["variant"] != "FULL") & ours_df["feasible"]]["dominated_by_full"].sum())
    n_ours_total = int((ours_df["variant"] != "FULL").sum())
    lines.append(
        f"\n- **OURS (NSGA-II)**: the FULL decision Pareto-dominates the variant's decision (on profit/water/fert, "
        f"under FULL params) in {n_dominated}/{n_ours_total} variant x water-scenario combinations. Where it "
        "isn't dominated, the variant's NSGA-II plan traded one objective against another rather than simply "
        "losing on all three -- see the deltas above.\n"
    )

    if b2_by_variant is not None and b2_by_variant["mean_loss_pct"].idxmax() == "NO_COST":
        lines.append(
            "\nPlain language: **cost-of-cultivation data matters most to the DECISION** -- B2 (the exact "
            f"solver, so this reading is not a heuristic artifact) loses the most profit ({b2_by_variant.loc['NO_COST', 'mean_loss_pct']:+.1f}%) "
            "when cost is dropped to zero, more than when yield comes from a historical mean instead of the ML "
            "model, or when price is set to MSP/mean-price instead of the forecast. The ML yield model and the "
            "price forecast matter less to the final allocation than the reference cost table does.\n"
        )
    else:
        lines.append(
            "\nPlain language: this table shows which single piece of information -- the ML yield model, the "
            "price forecast, or the cost-of-cultivation figures -- the exact-solver (B2) decision depends on "
            "most; see the per-variant mean profit loss above for which one dominates in this run.\n"
        )

    (REPORTS_RESULTS / "ablation_decisions.md").write_text("".join(lines), encoding="utf-8")
    print("\nWrote ablation_decisions.csv (+ _lp/_ours) / ablation_decisions.md")
    print("\n=== B2/B3 (LP) ===")
    print(lp_df.to_string(index=False))
    print("\n=== OURS (dominance) ===")
    print(ours_df.to_string(index=False))


if __name__ == "__main__":
    sys.exit(main())
