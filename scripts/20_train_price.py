"""Phase 2 (c): price forecasting.

Naive / Seasonal-Naive / pooled XGBoost, rolling-origin backtest at horizons
h in {3, 6, 12} months -> reports/results/price_results.csv/.md,
price_findings.md, plots. MSP floor experiment (E2.2). Selects the best
model for h=12 by backtest MAE, refits it on all data through the last
observed month, and saves models/price_best_h12.* for expected_price().
"""
from __future__ import annotations

import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from agriopt.config import REPORTS_RESULTS
from agriopt.data.reference import load_reference
from agriopt.models.price_model import (
    HORIZONS,
    PRICE_CROPS,
    build_base_features,
    build_horizon_table,
    build_wide_price_table,
    compute_price_metrics,
    fit_xgb,
    load_price_frame,
    predict_xgb,
    rolling_origin_backtest,
    save_price_model,
)

MODEL_COLS = {"Naive": "pred_naive", "Seasonal-Naive": "pred_seasonal_naive", "XGBoost": "pred_xgb"}
PLOT_CROPS_H12 = ["rice", "wheat", "cotton"]


def metrics_table(bt: pd.DataFrame) -> pd.DataFrame:
    """rows = model, columns = overall_{MAE,RMSE,MAPE} + <crop>_{MAE,MAPE}."""
    rows = []
    for model_name, col in MODEL_COLS.items():
        row = {"model": model_name}
        overall = compute_price_metrics(bt["actual"], bt[col])
        row.update({f"overall_{k}": v for k, v in overall.items() if k != "n"})
        row["overall_n"] = overall["n"]
        for crop in PRICE_CROPS:
            sub = bt[bt["crop"] == crop]
            m = compute_price_metrics(sub["actual"], sub[col])
            row[f"{crop}_MAE"] = m["MAE"]
            row[f"{crop}_MAPE"] = m["MAPE"]
        rows.append(row)
    return pd.DataFrame(rows).set_index("model")


def markdown_bold_best(df: pd.DataFrame) -> str:
    lower_better = [c for c in df.columns if c.endswith(("_MAE", "_RMSE", "_MAPE"))]
    lines = ["| model | " + " | ".join(df.columns) + " |\n", "|---|" + "---|" * len(df.columns) + "\n"]
    best = {c: df[c].dropna().idxmin() for c in lower_better if df[c].notna().any()}
    for model_name, row in df.iterrows():
        cells = [model_name]
        for col in df.columns:
            val = row[col]
            if pd.isna(val):
                cells.append("-")
                continue
            text = f"{val:.1f}" if isinstance(val, float) else str(val)
            if best.get(col) == model_name:
                text = f"**{text}**"
            cells.append(text)
        lines.append("| " + " | ".join(cells) + " |\n")
    return "".join(lines)


def main() -> None:
    REPORTS_RESULTS.mkdir(parents=True, exist_ok=True)

    print("Loading prices_monthly.parquet ...")
    df = load_price_frame()
    print(f"  {len(df)} rows, crops: {sorted(df['crop'].unique())}, "
          f"last month: {df['month'].max().date()}")

    backtests = {}
    for h in HORIZONS:
        print(f"\nRolling-origin backtest h={h} ...")
        bt = rolling_origin_backtest(df, h)
        backtests[h] = bt
        print(f"  {len(bt)} (crop, origin) predictions across "
              f"{bt['origin_month'].nunique()} origins.")

    # --- E2.1: results table, per horizon -----------------------------------
    csv_frames = []
    md_lines = ["# Price model results (E2.1)\n"]
    for h in HORIZONS:
        table = metrics_table(backtests[h])
        table_for_csv = table.reset_index()
        table_for_csv.insert(0, "horizon", h)
        csv_frames.append(table_for_csv)
        md_lines.append(f"\n## Horizon h={h} months\n\n")
        md_lines.append(markdown_bold_best(table))
    pd.concat(csv_frames, ignore_index=True).to_csv(REPORTS_RESULTS / "price_results.csv", index=False)
    (REPORTS_RESULTS / "price_results.md").write_text("".join(md_lines), encoding="utf-8")
    print("\nWrote price_results.csv / price_results.md")

    overall_mae = {h: {m: compute_price_metrics(backtests[h]["actual"], backtests[h][col])["MAE"] for m, col in MODEL_COLS.items()} for h in HORIZONS}
    winner_by_h = {h: min(overall_mae[h], key=overall_mae[h].get) for h in HORIZONS}
    print("Winner by overall backtest MAE per horizon:", winner_by_h)

    # --- Plots: actual vs forecast for 3 crops at h=12 --------------------------
    bt12 = backtests[12]
    fig, axes = plt.subplots(len(PLOT_CROPS_H12), 1, figsize=(9, 10), sharex=False)
    for ax, crop in zip(axes, PLOT_CROPS_H12):
        sub = bt12[bt12["crop"] == crop].sort_values("target_month")
        ax.plot(sub["target_month"], sub["actual"], label="actual", color="black")
        ax.plot(sub["target_month"], sub["pred_naive"], label="naive", linestyle="--")
        ax.plot(sub["target_month"], sub["pred_xgb"], label="xgboost", linestyle=":")
        ax.set_title(f"{crop}: h=12 actual vs forecast")
        ax.set_ylabel("Rs/qtl")
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(REPORTS_RESULTS / "price_actual_vs_forecast_h12.png", dpi=150)
    plt.close(fig)
    print("Wrote price_actual_vs_forecast_h12.png")

    # --- E2.2: MSP floor experiment (h=12 XGB) -----------------------------------
    ref = load_reference()
    msp_by_crop = ref.set_index("crop")["msp_rs_per_qtl"].to_dict()
    bt12 = bt12.copy()
    bt12["msp"] = bt12["crop"].map(msp_by_crop)
    bt12["pred_xgb_floored"] = bt12[["pred_xgb", "msp"]].max(axis=1)

    msp_lines = ["# MSP floor experiment (E2.2, h=12 XGBoost)\n\n"]
    msp_rows = []
    for crop in PRICE_CROPS:
        sub = bt12[bt12["crop"] == crop]
        if sub["msp"].isna().all():
            continue
        raw = compute_price_metrics(sub["actual"], sub["pred_xgb"])
        floored = compute_price_metrics(sub["actual"], sub["pred_xgb_floored"])
        msp_rows.append({"crop": crop, "raw_MAE": raw["MAE"], "floored_MAE": floored["MAE"],
                          "raw_MAPE": raw["MAPE"], "floored_MAPE": floored["MAPE"],
                          "floor_helps": floored["MAE"] < raw["MAE"]})
    msp_df = pd.DataFrame(msp_rows).set_index("crop")
    msp_df.to_csv(REPORTS_RESULTS / "price_msp_floor.csv")
    msp_lines.append("| crop | " + " | ".join(msp_df.columns) + " |\n")
    msp_lines.append("|---|" + "---|" * len(msp_df.columns) + "\n")
    for crop, row in msp_df.iterrows():
        cells = [f"{v:.1f}" if isinstance(v, float) else str(v) for v in row]
        msp_lines.append(f"| {crop} | " + " | ".join(cells) + " |\n")
    n_helped = int(msp_df["floor_helps"].sum())
    msp_lines.append(
        f"\n\nMSP floor {'helped' if n_helped > len(msp_df) / 2 else 'did not help'} "
        f"overall: helped {n_helped}/{len(msp_df)} crops (lower MAE with the floor applied).\n"
    )
    (REPORTS_RESULTS / "price_msp_floor.md").write_text("".join(msp_lines), encoding="utf-8")
    print(f"Wrote price_msp_floor.csv / price_msp_floor.md ({n_helped}/{len(msp_df)} crops helped)")

    # --- Findings -------------------------------------------------------------
    write_findings(backtests, overall_mae, winner_by_h, msp_df)

    # --- Select + refit best h=12 model for inference -----------------------------
    best_h12 = winner_by_h[12]
    print(f"\nBest model for h=12 (backtest MAE, used as validation): {best_h12}")

    wide = build_wide_price_table(df)
    base = build_base_features(wide)
    horizon_table_12 = build_horizon_table(base, wide, 12)
    last_month = wide.index.max()

    if best_h12 == "XGBoost":
        all_train = horizon_table_12[horizon_table_12["target_price"].notna()]
        final_model = fit_xgb(all_train)
    else:
        final_model = None  # Naive/Seasonal-Naive need no fitted model; expected_price() looks up the wide table directly

    metadata = {
        "method": best_h12,
        "origin_month": str(last_month.date()),
        "horizon": 12,
        "backtest_overall_mae_h12": overall_mae[12],
        "backtest_window": "2021-11 to 2024-10 (36 origins); used as validation, no further held-out test set",
        "price_crops": PRICE_CROPS,
    }
    save_price_model(final_model, metadata)
    print(f"Saved models/price_best_h12.joblib / .json (method={best_h12}, origin={last_month.date()})")

    # --- Print inference table: crop, expected price h=12, MSP/FRP, last observed --
    from agriopt.models.price_model import expected_price

    print(f"\n{'crop':10s} {'expected_h12':14s} {'MSP/FRP':10s} {'last_observed':14s}")
    for crop in PRICE_CROPS:
        r = expected_price(crop, horizon=12)
        msp = msp_by_crop.get(crop)
        last_obs = float(wide[crop].dropna().iloc[-1])
        print(f"{crop:10s} {r['value_rs_per_qtl']:<14.1f} {msp if msp==msp else '-':<10} {last_obs:<14.1f}")
    frp_row = load_reference()
    frp = frp_row[frp_row["crop"] == "sugarcane"].iloc[0]["admin_price_rs_per_qtl"]
    print(f"{'sugarcane':10s} {frp:<14.1f} {'(FRP)':<10} {'n/a (no mandi series)':<14s}")


def write_findings(backtests, overall_mae, winner_by_h, msp_df) -> None:
    lines = ["# Price model findings (Phase 2)\n\n"]
    for h in HORIZONS:
        sorted_models = sorted(overall_mae[h].items(), key=lambda kv: kv[1])
        winner, winner_mae = sorted_models[0]
        lines.append(
            f"- h={h}: **{winner}** wins on overall backtest MAE ({winner_mae:.1f} Rs/qtl); "
            + ", ".join(f"{m}={v:.1f}" for m, v in sorted_models[1:])
            + (". Naive and Seasonal-Naive are mathematically IDENTICAL at h=12 (12 months before a "
               "target 12 months out is just the origin month's own price), so any tie there is expected, "
               "not a bug." if h == 12 else "")
            + "\n"
        )
    naive_wins_somewhere = any(winner_by_h[h] in ("Naive", "Seasonal-Naive") for h in HORIZONS)
    lines.append(
        f"- {'A naive baseline wins at one or more horizons' if naive_wins_somewhere else 'XGBoost wins at every horizon'} "
        "-- commodity mandi prices are highly persistent month-to-month, so simple persistence is a strong, "
        "hard-to-beat baseline, especially with only ~20 years of monthly data pooled across 7 crops for XGBoost to learn from.\n"
    )
    n_helped = int(msp_df["floor_helps"].sum())
    lines.append(
        f"- MSP floor (E2.2, h=12 XGBoost): helped {n_helped}/{len(msp_df)} crops (lower MAE with "
        f"max(forecast, MSP) than the raw forecast) -- {'MSP floors are a net positive adjustment given how often mandi prices trade below MSP' if n_helped > len(msp_df) / 2 else 'MSP floors are NOT a reliable blanket adjustment; forecasts already tend to sit above MSP for most crops in this backtest, so flooring adds bias without reducing error'}.\n"
    )
    lines.append(
        "- This uses rolling-origin backtest MAE as a VALIDATION signal to select the deployed h=12 model "
        "(no further held-out test set exists beyond the backtest itself) -- the reported backtest numbers "
        "for the winning model are the same numbers used to pick it, unlike the yield model's separate "
        "validation/test split.\n"
    )
    lines.append(
        "- Sugarcane has no mandi price series at all -- expected_price('sugarcane') always returns the "
        "government FRP (crop_reference.csv), never a forecast.\n"
    )
    (REPORTS_RESULTS / "price_findings.md").write_text("".join(lines), encoding="utf-8")
    print("Wrote price_findings.md")


if __name__ == "__main__":
    sys.exit(main())
