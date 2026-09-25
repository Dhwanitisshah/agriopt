"""Phase 9 / E1.4: significance tests for the yield model on the Maharashtra
test set (year >= 2016).

Refits RandomForest/XGBoost/Ridge/Baseline-Mean on year<=2015 (train,
mirroring Phase 1's `tune_rf`/`tune_xgb` protocol exactly -- see the
ASSUMPTION note below on why hyperparameters are re-derived rather than
loaded from models/yield_best.json), then:
  1) Wilcoxon signed-rank test (scipy.stats.wilcoxon) on ABSOLUTE ERRORS,
     paired by Maharashtra test row, for RF vs XGB / RF vs Baseline-Mean /
     RF vs Ridge.
  2) Bootstrap 95% CI (2000 resamples, seed=42, resample rows w/
     replacement) for MAE of each of the 4 models.

ASSUMPTION: models/yield_best.json does not persist the raw RandomForest/
XGBoost hyperparameter dict (only metrics/feature lists -- confirmed by
inspection), so there is nothing saved to reuse. Instead this script
re-runs `tune_rf`/`tune_xgb` on the EXACT SAME tuning split Phase 1 used
(`tuning_split`: fit < 2013, validate 2013-2015) to reproduce the same
hyperparameter selection, then fits each family on the full <=2015 train
set -- the same protocol `scripts/10_train_yield.py` and
`agriopt.backtest.info.refit_yield_model_for_year` both already use.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge

from agriopt.config import CROPS, RANDOM_SEED, REPORTS_RESULTS, STATE
from agriopt.models.yield_model import (
    BaselineMean,
    CORE_NUM_COLS,
    SklearnYieldModel,
    XgbYieldModel,
    _force_single_threaded_predict,
    load_model_frame,
    train_test_split_by_year,
    tune_rf,
    tune_xgb,
    tuning_split,
)
from agriopt.stats.bootstrap import bootstrap_metric_ci, mae


def build_models(train: pd.DataFrame, num_cols: list[str]) -> dict:
    tune_fit, tune_valid = tuning_split(train)
    rf_params = tune_rf(tune_fit, tune_valid, num_cols)
    xgb_params = tune_xgb(tune_fit, tune_valid, num_cols)
    print(f"  RF params: {rf_params}")
    print(f"  XGB params: {xgb_params}")

    rf = SklearnYieldModel("RandomForest", RandomForestRegressor(random_state=RANDOM_SEED, n_jobs=-1, **rf_params), num_cols)
    rf.fit(train)
    _force_single_threaded_predict(rf)  # Phase 8: reproducible predict()

    xgb = XgbYieldModel("XGBoost", num_cols, **xgb_params).fit(train)
    ridge = SklearnYieldModel("Ridge", Ridge(alpha=1.0, random_state=RANDOM_SEED), num_cols).fit(train)
    baseline = BaselineMean().fit(train)

    return {"RandomForest": rf, "XGBoost": xgb, "Ridge": ridge, "Baseline-Mean": baseline}


def main() -> None:
    REPORTS_RESULTS.mkdir(parents=True, exist_ok=True)

    df, _ = load_model_frame()
    train, test = train_test_split_by_year(df)
    mh_test = test[test["state"] == STATE].reset_index(drop=True)
    print(f"Maharashtra test rows: {len(mh_test)}")

    num_cols = CORE_NUM_COLS  # fert/pest excluded, matches models/yield_best.json (fert_pest_included=false)
    print("Refitting RF/XGB/Ridge/Baseline-Mean on <=2015 train (Phase 1 tuning protocol) ...")
    models = build_models(train, num_cols)

    y_true = mh_test["yield"].to_numpy(dtype=float)
    abs_err = {}
    for name, model in models.items():
        pred = model.predict(mh_test)
        abs_err[name] = np.abs(y_true - pred)

    # --- 1) Wilcoxon signed-rank on absolute errors, paired by test row ---
    pairs = [("RandomForest", "XGBoost"), ("RandomForest", "Baseline-Mean"), ("RandomForest", "Ridge")]
    wilcoxon_rows = []
    for m1, m2 in pairs:
        d = abs_err[m1] - abs_err[m2]
        if np.allclose(d, 0.0):
            stat, p = 0.0, 1.0
        else:
            stat, p = wilcoxon(abs_err[m1], abs_err[m2])
        verdict = (
            f"No significant difference between {m1} and {m2} (p={p:.3f})."
            if p >= 0.05
            else f"{m2 if d.mean() > 0 else m1} has significantly lower absolute error than {m1 if d.mean() > 0 else m2} (p={p:.3f})."
        )
        wilcoxon_rows.append(
            {
                "comparison": f"{m1} vs {m2}",
                "n": len(d),
                "mean_abs_err_diff": float(d.mean()),
                "wilcoxon_stat": float(stat),
                "p_value": float(p),
                "verdict": verdict,
            }
        )
    wilcoxon_df = pd.DataFrame(wilcoxon_rows)
    wilcoxon_df.to_csv(REPORTS_RESULTS / "yield_significance_wilcoxon.csv", index=False)

    # --- 2) Bootstrap 95% CI for MAE of each model -------------------------
    boot_rows = []
    for name, model in models.items():
        pred = model.predict(mh_test)
        ci = bootstrap_metric_ci(y_true, pred, mae, n_boot=2000, seed=RANDOM_SEED)
        boot_rows.append({"model": name, "MAE": ci["point"], "ci_lo_95": ci["ci_lo"], "ci_hi_95": ci["ci_hi"], "n_boot": ci["n_boot"]})
    boot_df = pd.DataFrame(boot_rows)
    boot_df.to_csv(REPORTS_RESULTS / "yield_significance_bootstrap.csv", index=False)

    # --- write-up -----------------------------------------------------------
    lines = ["# Yield model significance (Phase 9 / E1.4)\n\n"]
    lines.append(f"Maharashtra test set (year >= 2016), n={len(mh_test)} rows. Models refit on year<=2015.\n\n")

    lines.append("## Wilcoxon signed-rank test on absolute errors (paired by test row)\n\n")
    lines.append("| comparison | n | mean abs-err diff | statistic | p-value | verdict |\n|---|---|---|---|---|---|\n")
    for _, r in wilcoxon_df.iterrows():
        lines.append(f"| {r['comparison']} | {r['n']} | {r['mean_abs_err_diff']:.4f} | {r['wilcoxon_stat']:.2f} | {r['p_value']:.4f} | {r['verdict']} |\n")

    lines.append("\n## Bootstrap 95% CI for MAE (2000 resamples, seed=42)\n\n")
    lines.append("| model | MAE | 95% CI low | 95% CI high |\n|---|---|---|---|\n")
    for _, r in boot_df.iterrows():
        lines.append(f"| {r['model']} | {r['MAE']:.4f} | {r['ci_lo_95']:.4f} | {r['ci_hi_95']:.4f} |\n")

    n_sig = int((wilcoxon_df["p_value"] < 0.05).sum())
    lines.append(f"\n## Findings\n\n- {n_sig}/{len(wilcoxon_df)} RF-vs-X comparisons are significant at p<0.05.\n")
    for _, r in wilcoxon_df.iterrows():
        lines.append(f"- {r['verdict']}\n")
    lines.append(
        f"- n={len(mh_test)} Maharashtra test rows -- small-sample caveat applies (same spirit as the Phase 7 "
        "backtest's n=4/5-year caveat): a handful of crop-years dominate the paired differences.\n"
    )

    (REPORTS_RESULTS / "yield_significance.md").write_text("".join(lines), encoding="utf-8")
    print("Wrote yield_significance_wilcoxon.csv / yield_significance_bootstrap.csv / yield_significance.md")


if __name__ == "__main__":
    sys.exit(main())
