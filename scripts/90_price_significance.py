"""Phase 9 / E2.3: Diebold-Mariano significance tests for the price model.

For each horizon h in {3, 6, 12}: Naive vs XGBoost, and Naive vs
Seasonal-Naive, absolute-error loss, HLN-corrected DM test -- a PANEL test
across all PRICE_CROPS (time-clustered variance: each origin month is one
cluster, so the effective n is the number of months, not months x 7 crops;
cross-checked with a moving-block bootstrap over months) and PER-CROP.
The earlier test stacked the 7 crops into one long series, treating
months x crops errors as independent although crops' prices co-move within a
month; that stacked p-value is kept in the csv (`p_value_stacked`) only to show
how much it overstated significance. Rows are paired by (crop, origin_month)
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
from agriopt.stats.dm_test import block_bootstrap_pvalue, diebold_mariano, dm_verdict, panel_diebold_mariano

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
        # PANEL across crops, time-clustered (see module docstring and
        # agriopt.stats.dm_test.panel_diebold_mariano). The stacked
        # (crop-by-crop concatenated) test is computed too, for the audit column only.
        loss_diff = (valid[col1] - valid["actual"]).abs() - (valid[col2] - valid["actual"]).abs()
        panel = loss_diff.groupby([valid["origin_month"], valid["crop"]]).first().unstack("crop")
        if len(panel) >= 4:
            stat, p, n_months = panel_diebold_mariano(panel, h)
            p_boot, _ = block_bootstrap_pvalue(panel, block_len=max(h, 6))
            stacked = valid.sort_values(["crop", "origin_month"])
            _, p_stacked = diebold_mariano(_errors(stacked, col1), _errors(stacked, col2), h)
            rows.append(
                {
                    "horizon": h,
                    "scope": "panel",
                    "crop": "ALL",
                    "comparison": f"{label1} vs {label2}",
                    "n": n_months,
                    "n_obs_stacked": int(len(stacked)),
                    "dm_stat": stat,
                    "p_value": p,
                    "p_value_bootstrap": p_boot,
                    "p_value_stacked": p_stacked,
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

    lines.append("## Panel (all 7 PRICE_CROPS, time-clustered; n = origin months)\n\n")
    lines.append(
        "`p_value` = HLN-corrected DM on the month-averaged loss differential (h-1 HAC lags); "
        "`p_boot` = moving-block bootstrap over months (block = max(h, 6)); "
        "`p_stacked` = the earlier test that stacked crops as if independent (shown only to quantify its "
        "overstatement; do not cite).\n\n"
    )
    pooled = out[out["scope"] == "panel"]
    lines.append("| horizon | comparison | months | stacked obs | dm_stat | p_value | p_boot | p_stacked | verdict |\n|---|---|---|---|---|---|---|---|---|\n")
    for _, r in pooled.iterrows():
        lines.append(
            f"| {r['horizon']} | {r['comparison']} | {int(r['n'])} | {int(r['n_obs_stacked'])} | {r['dm_stat']:.3f} | {r['p_value']:.4f} | "
            f"{r['p_value_bootstrap']:.4f} | {r['p_value_stacked']:.4f} | {r['verdict']} |\n"
        )

    lines.append("\n## Per-crop\n\n")
    per_crop = out[out["scope"] == "per_crop"]
    lines.append("| horizon | crop | comparison | n | dm_stat | p_value | verdict |\n|---|---|---|---|---|---|---|\n")
    for _, r in per_crop.iterrows():
        lines.append(f"| {r['horizon']} | {r['crop']} | {r['comparison']} | {r['n']} | {r['dm_stat']:.3f} | {r['p_value']:.4f} | {r['verdict']} |\n")

    n_sig_pooled = int((pooled["p_value"] < 0.05).sum())
    n_sig_stacked = int((pooled["p_value_stacked"] < 0.05).sum())
    n_sig_both = int(((pooled["p_value"] < 0.05) & (pooled["p_value_bootstrap"] < 0.05)).sum())
    lines.append(
        f"\n## Findings\n\n- {n_sig_pooled}/{len(pooled)} panel comparisons are significant at p<0.05 "
        f"({n_sig_both} also by the block bootstrap); the stacked test would have called {n_sig_stacked}/{len(pooled)} significant.\n"
    )
    xgb_pooled = pooled[pooled["comparison"] == "Naive vs XGBoost"]
    if not xgb_pooled.empty:
        sig_h = xgb_pooled[xgb_pooled["p_value"] < 0.05]["horizon"].tolist()
        lines.append(
            f"- Naive vs XGBoost (panel): significant at horizons {sig_h if sig_h else 'none'}.\n"
        )
    sn_pooled = pooled[pooled["comparison"] == "Naive vs Seasonal-Naive"]
    if not sn_pooled.empty:
        sig_h = sn_pooled[sn_pooled["p_value"] < 0.05]["horizon"].tolist()
        lines.append(
            f"- Naive vs Seasonal-Naive (panel): significant at horizons {sig_h if sig_h else 'none'}.\n"
        )
    lines.append(
        "- The panel test's n is the number of origin MONTHS (one cluster each), so it is far less powered than "
        "the stacked test pretended to be; per-crop tests have the same n per crop but a single series, so they "
        "are noisier still -- read the panel row as the headline, per-crop rows as detail.\n"
    )

    (REPORTS_RESULTS / "price_significance.md").write_text("".join(lines), encoding="utf-8")
    print("Wrote price_significance.csv / price_significance.md")


if __name__ == "__main__":
    sys.exit(main())
