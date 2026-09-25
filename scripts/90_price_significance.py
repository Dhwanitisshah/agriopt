"""Phase 9 / E2.3: Diebold-Mariano significance tests for the price model.

For each horizon h in {3, 6, 12}: Naive vs XGBoost, and Naive vs
Seasonal-Naive, absolute-error loss, HLN-corrected DM test -- POOLED across
all PRICE_CROPS and PER-CROP. Rows are paired by (crop, origin_month)
within a comparison (both forecasts predict the SAME target from the SAME
rolling-origin backtest output -- see agriopt.models.price_model.
rolling_origin_backtest), and only rows with all three predictions +
a realized actual are used (drops the tail-end origins with no realized
target yet).

Writes reports/results/price_significance.csv / .md.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from agriopt.config import REPORTS_RESULTS
from agriopt.models.price_model import HORIZONS, PRICE_CROPS, load_price_frame, rolling_origin_backtest
from agriopt.stats.dm_test import diebold_mariano, dm_verdict

COMPARISONS = [
    ("pred_naive", "pred_xgb", "Naive", "XGBoost"),
    ("pred_naive", "pred_seasonal_naive", "Naive", "Seasonal-Naive"),
]


def _errors(df: pd.DataFrame, pred_col: str) -> np.ndarray:
    return (df["actual"] - df[pred_col]).to_numpy(dtype=float)


def run_comparisons(bt: pd.DataFrame, h: int) -> list[dict]:
    rows = []
    valid = bt.dropna(subset=["actual", "pred_naive", "pred_xgb", "pred_seasonal_naive"])

    for col1, col2, label1, label2 in COMPARISONS:
        # POOLED across crops -- valid because DM's HAC variance estimator
        # only assumes stationarity/autocorrelation structure WITHIN a
        # single paired series; pooling crops just concatenates independent
        # (crop, time) series in temporal order per crop, which understates
        # cross-crop correlation slightly but is the standard "pooled
        # backtest" convention already used elsewhere in this repo
        # (compute_price_metrics is called pooled too) -- documented here as
        # an ASSUMPTION, not hidden.
        pooled = valid.sort_values(["crop", "origin_month"])
        e1, e2 = _errors(pooled, col1), _errors(pooled, col2)
        if len(e1) >= 2:
            stat, p = diebold_mariano(e1, e2, h)
            rows.append(
                {
                    "horizon": h,
                    "scope": "pooled",
                    "crop": "ALL",
                    "comparison": f"{label1} vs {label2}",
                    "n": len(e1),
                    "dm_stat": stat,
                    "p_value": p,
                    "verdict": dm_verdict(stat, p, label1, label2, h),
                }
            )

        for crop in PRICE_CROPS:
            sub = valid[valid["crop"] == crop].sort_values("origin_month")
            if len(sub) < 2:
                continue
            e1, e2 = _errors(sub, col1), _errors(sub, col2)
            stat, p = diebold_mariano(e1, e2, h)
            rows.append(
                {
                    "horizon": h,
                    "scope": "per_crop",
                    "crop": crop,
                    "comparison": f"{label1} vs {label2}",
                    "n": len(e1),
                    "dm_stat": stat,
                    "p_value": p,
                    "verdict": dm_verdict(stat, p, label1, label2, h),
                }
            )
    return rows


def main() -> None:
    REPORTS_RESULTS.mkdir(parents=True, exist_ok=True)
    df = load_price_frame()

    all_rows = []
    for h in HORIZONS:
        print(f"Running rolling-origin backtest h={h} ...")
        bt = rolling_origin_backtest(df, h)
        all_rows.extend(run_comparisons(bt, h))

    out = pd.DataFrame(all_rows)
    out.to_csv(REPORTS_RESULTS / "price_significance.csv", index=False)

    lines = ["# Price model significance: Diebold-Mariano tests (Phase 9 / E2.3)\n\n"]
    lines.append(
        "HLN-corrected Diebold-Mariano test, absolute-error loss "
        "(d_t = |e_naive| - |e_other|; positive dm_stat means the OTHER "
        "model has smaller average absolute error than Naive), HAC variance "
        "with h-1 lags. p < 0.05 is treated as significant. See "
        "`agriopt.stats.dm_test` for the implementation.\n\n"
    )

    lines.append("## Pooled (across all 7 PRICE_CROPS)\n\n")
    pooled = out[out["scope"] == "pooled"]
    lines.append("| horizon | comparison | n | dm_stat | p_value | verdict |\n|---|---|---|---|---|---|\n")
    for _, r in pooled.iterrows():
        lines.append(f"| {r['horizon']} | {r['comparison']} | {r['n']} | {r['dm_stat']:.3f} | {r['p_value']:.4f} | {r['verdict']} |\n")

    lines.append("\n## Per-crop\n\n")
    per_crop = out[out["scope"] == "per_crop"]
    lines.append("| horizon | crop | comparison | n | dm_stat | p_value | verdict |\n|---|---|---|---|---|---|---|\n")
    for _, r in per_crop.iterrows():
        lines.append(f"| {r['horizon']} | {r['crop']} | {r['comparison']} | {r['n']} | {r['dm_stat']:.3f} | {r['p_value']:.4f} | {r['verdict']} |\n")

    n_sig_pooled = int((pooled["p_value"] < 0.05).sum())
    lines.append(
        f"\n## Findings\n\n- {n_sig_pooled}/{len(pooled)} pooled comparisons are significant at p<0.05.\n"
    )
    xgb_pooled = pooled[pooled["comparison"] == "Naive vs XGBoost"]
    if not xgb_pooled.empty:
        sig_h = xgb_pooled[xgb_pooled["p_value"] < 0.05]["horizon"].tolist()
        lines.append(
            f"- Naive vs XGBoost (pooled): significant at horizons {sig_h if sig_h else 'none'}.\n"
        )
    sn_pooled = pooled[pooled["comparison"] == "Naive vs Seasonal-Naive"]
    if not sn_pooled.empty:
        sig_h = sn_pooled[sn_pooled["p_value"] < 0.05]["horizon"].tolist()
        lines.append(
            f"- Naive vs Seasonal-Naive (pooled): significant at horizons {sig_h if sig_h else 'none'}.\n"
        )
    lines.append(
        "- Per-crop tests have far fewer observations than pooled (n per crop is the number of backtest "
        "origins, not origins x crops), so per-crop p-values are noisier / less powered -- read the pooled "
        "row as the headline, per-crop rows as detail.\n"
    )

    (REPORTS_RESULTS / "price_significance.md").write_text("".join(lines), encoding="utf-8")
    print("Wrote price_significance.csv / price_significance.md")


if __name__ == "__main__":
    sys.exit(main())
