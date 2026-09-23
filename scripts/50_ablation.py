"""Phase 5 / Experiment 4: information ablation.

For each crop-params VARIANT (FULL, NO_ML_YIELD, MSP_PRICE, MEAN_PRICE,
NO_COST) and each water scenario (tight, current): decide an allocation
(OURS via NSGA-II recommend, B2 via profit-max LP) using the VARIANT's
params, then EVALUATE that allocation under FULL params -- i.e. "how much
does using worse/partial information cost you, once judged against the
best information we have?"

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
from agriopt.optim.baselines import current_mix, evaluate
from agriopt.optim.baselines import nsga2_recommended
from agriopt.optim.params import build_crop_params
from agriopt.optim.problem import Scenario
from agriopt.optim.risk import build_risk_inputs, portfolio_risk
from agriopt.optim.solvers import solve_lp_profit_max

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
    return {"OURS": x_ours, "B2": x_b2}


def main() -> None:
    REPORTS_RESULTS.mkdir(parents=True, exist_ok=True)

    full_params = build_crop_params("market", verbose=False)
    risk_inputs = build_risk_inputs(full_params)
    b1_water = compute_b1_water(full_params)
    water_budgets = {label: mult * b1_water for label, mult in WATER_MULTIPLIERS.items()}
    print(f"B1 water usage: {b1_water:.1f} m3; budgets: {water_budgets}")

    variant_params = {name: builder(full_params) for name, builder in VARIANTS.items()}

    rows = []
    for water_label, wb in water_budgets.items():
        scenario = Scenario(water_budget_m3=wb, land_ha=LAND_HA, price_mode="market")
        print(f"\n-- water={water_label} --")

        full_decisions = decide(variant_params["FULL"], scenario)

        for variant_name, params_variant in variant_params.items():
            print(f"  variant={variant_name} ...")
            decisions = decide(params_variant, scenario) if variant_name != "FULL" else full_decisions

            for strategy in ["OURS", "B2"]:
                x_variant = decisions[strategy]
                x_full_ref = full_decisions[strategy]

                if x_variant is None or x_full_ref is None:
                    rows.append(
                        {"variant": variant_name, "water_scenario": water_label, "strategy": strategy, "feasible": False}
                    )
                    continue

                r_eval = evaluate(x_variant, full_params, scenario)
                r_full_ref = evaluate(x_full_ref, full_params, scenario)
                profit_loss_pct = (
                    (r_full_ref["profit"] - r_eval["profit"]) / abs(r_full_ref["profit"]) * 100
                    if r_full_ref["profit"]
                    else float("nan")
                )
                l1_dist = float(np.abs(x_variant - x_full_ref).sum())
                risk_val = portfolio_risk(x_variant, risk_inputs.Sigma)

                rows.append(
                    {
                        "variant": variant_name,
                        "water_scenario": water_label,
                        "strategy": strategy,
                        "profit_under_full": r_eval["profit"],
                        "profit_pct_loss_vs_full_decision": profit_loss_pct,
                        "water_m3": r_eval["water_m3"],
                        "fert_kg": r_eval["fert_kg"],
                        "allocation_l1_dist_ha": l1_dist,
                        "portfolio_risk_rs": risk_val,
                        "feasible": r_eval["feasible"],
                    }
                )

    df = pd.DataFrame(rows)
    df.to_csv(REPORTS_RESULTS / "ablation_decisions.csv", index=False)

    lines = ["# Information ablation (Phase 5, Experiment 4)\n\n"]
    lines.append(
        "Each variant DECIDES an allocation (OURS = NSGA-II recommend, seed=0, default weights; B2 = profit-max "
        "LP) using its own (degraded) view of crop params, then that allocation is EVALUATED under FULL params "
        "-- this measures the real cost of deciding with worse information, not just how the params themselves "
        "differ.\n\n"
    )
    cols = ["variant", "water_scenario", "strategy", "profit_under_full", "profit_pct_loss_vs_full_decision", "water_m3", "fert_kg", "allocation_l1_dist_ha", "portfolio_risk_rs", "feasible"]
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

    lines.append("\n## Findings\n\n")
    ours_df = df[(df["strategy"] == "OURS") & (df["variant"] != "FULL") & df["feasible"]]
    if not ours_df.empty:
        by_variant = ours_df.groupby("variant").agg(
            mean_loss_pct=("profit_pct_loss_vs_full_decision", "mean"), mean_l1=("allocation_l1_dist_ha", "mean")
        )
        worst_loss = by_variant["mean_loss_pct"].idxmax()
        worst_l1 = by_variant["mean_l1"].idxmax()
        lines.append(
            f"- By profit loss (OURS, averaged over water scenarios): **{worst_loss}** costs the most "
            f"({by_variant.loc[worst_loss, 'mean_loss_pct']:+.1f}% vs the FULL-information decision). "
            f"By decision shift: **{worst_l1}** moves hectares the most "
            f"({by_variant.loc[worst_l1, 'mean_l1']:.2f} ha mean L1 distance from the FULL decision).\n"
        )
        for variant in by_variant.index:
            row = by_variant.loc[variant]
            lines.append(f"- {variant}: mean profit loss {row['mean_loss_pct']:+.1f}%, mean allocation shift {row['mean_l1']:.2f} ha.\n")
    lines.append(
        "\nPlain language: this table shows which single piece of information -- the ML yield model, the "
        "price forecast, or the cost-of-cultivation figures -- the recommendation depends on most. A variant "
        "with near-zero loss/shift means that information barely matters for the DECISION even if the numbers "
        "themselves change; a variant with a large loss/shift means the pipeline is leaning heavily on that "
        "particular model or data source.\n"
    )

    (REPORTS_RESULTS / "ablation_decisions.md").write_text("".join(lines), encoding="utf-8")
    print("\nWrote ablation_decisions.csv / ablation_decisions.md")
    print(df.to_string(index=False))


if __name__ == "__main__":
    sys.exit(main())
