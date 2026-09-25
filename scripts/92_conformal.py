"""Phase 9 / E1.5: split-conformal prediction intervals for the yield model.

Fit RandomForest on year<=2012 (all-India, matching Phase 1's population --
only the CUTOFF year changes), CALIBRATE the conformal quantile on
2013-2015 residuals (|log1p(yield_actual) - log1p(yield_pred)|, all-India),
at the 90% level (alpha=0.1), using the finite-sample-corrected quantile
(agriopt.stats.conformal.conformal_quantile). Apply the resulting interval
to the Maharashtra 2016-2020 test rows: report empirical coverage + mean
interval width (original units), overall and per crop.

Persists the fitted model + calibrated quantile(s) to
models/yield_conformal.joblib / .json so agriopt.models.yield_model.
predict_yield_interval() doesn't need to refit a RandomForest per call.

ASSUMPTION (RF hyperparameters): as in scripts/91_yield_significance.py,
models/yield_best.json doesn't persist raw RF hyperparams, so this script
re-derives them via tune_rf on a tuning window slid to end at 2012 (fit
<2010, validate 2010-2012 -- 3-year validation window, same shape as
Phase 1's fit<2013/validate 2013-2015), then fits on the full <=2012 set.
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from agriopt.config import (
    CROPS,
    RANDOM_SEED,
    REPORTS_RESULTS,
    STATE,
    YIELD_CONFORMAL_METADATA_PATH,
    YIELD_CONFORMAL_MODEL_PATH,
)
from agriopt.models.yield_model import (
    CANON_TO_YIELD_NAME,
    CAT_COLS,
    CORE_NUM_COLS,
    SklearnYieldModel,
    _force_single_threaded_predict,
    load_model_frame,
    save_model,
    tune_rf,
)
from agriopt.stats.conformal import conformal_coverage, conformal_quantile

FIT_END_YEAR = 2012
CALIB_START_YEAR, CALIB_END_YEAR = 2013, 2015
TEST_START_YEAR = 2016
ALPHA = 0.1


def main() -> None:
    REPORTS_RESULTS.mkdir(parents=True, exist_ok=True)
    df, _ = load_model_frame()
    num_cols = CORE_NUM_COLS

    fit_df = df[df["year"] <= FIT_END_YEAR].reset_index(drop=True)
    calib_df = df[(df["year"] >= CALIB_START_YEAR) & (df["year"] <= CALIB_END_YEAR)].reset_index(drop=True)
    test_df = df[df["year"] >= TEST_START_YEAR].reset_index(drop=True)
    mh_test = test_df[test_df["state"] == STATE].reset_index(drop=True)
    print(f"fit(<=  {FIT_END_YEAR}): {len(fit_df)} rows; calib({CALIB_START_YEAR}-{CALIB_END_YEAR}): {len(calib_df)} rows; "
          f"Maharashtra test(>= {TEST_START_YEAR}): {len(mh_test)} rows.")

    tune_fit = df[df["year"] < CALIB_START_YEAR - 3].reset_index(drop=True)
    tune_valid = df[(df["year"] >= CALIB_START_YEAR - 3) & (df["year"] <= FIT_END_YEAR)].reset_index(drop=True)
    print(f"Tuning RF: fit<{CALIB_START_YEAR - 3} ({len(tune_fit)} rows), "
          f"valid {CALIB_START_YEAR - 3}-{FIT_END_YEAR} ({len(tune_valid)} rows) ...")
    rf_params = tune_rf(tune_fit, tune_valid, num_cols)
    print(f"  RF params: {rf_params}")

    model = SklearnYieldModel("RandomForest", RandomForestRegressor(random_state=RANDOM_SEED, n_jobs=-1, **rf_params), num_cols)
    model.fit(fit_df)
    _force_single_threaded_predict(model)

    # log1p-space residuals (this repo's "log_yield" convention -- see
    # load_model_frame). model.pipeline.predict() returns log1p-scale
    # directly, avoiding a round-trip through expm1/log1p.
    X_calib = calib_df[CAT_COLS + num_cols]
    log_pred_calib = model.pipeline.predict(X_calib)
    log_actual_calib = calib_df["log_yield"].to_numpy(dtype=float)
    abs_resid_calib = np.abs(log_actual_calib - log_pred_calib)

    q_overall = conformal_quantile(abs_resid_calib, ALPHA)
    print(f"Overall calibrated quantile (log1p-space, alpha={ALPHA}): {q_overall:.4f} (n_calib={len(abs_resid_calib)})")

    q_per_crop = {}
    calib_with_resid = calib_df.copy()
    calib_with_resid["abs_resid"] = abs_resid_calib
    for crop in CROPS:
        name = CANON_TO_YIELD_NAME[crop]
        sub = calib_with_resid[calib_with_resid["crop"] == name]["abs_resid"].to_numpy()
        if len(sub) >= 5:  # too few calibration points -> unstable per-crop quantile, fall back to overall
            q_per_crop[crop] = conformal_quantile(sub, ALPHA)

    # --- apply to Maharashtra 2016-2020 test rows --------------------------
    X_test = mh_test[CAT_COLS + num_cols]
    log_pred_test = model.pipeline.predict(X_test)
    log_actual_test = mh_test["log_yield"].to_numpy(dtype=float)

    def coverage_for(rows_idx, q):
        lp = log_pred_test[rows_idx]
        la = log_actual_test[rows_idx]
        # coverage check done in LOG1P space (monotonic transform preserves
        # the guarantee -- see module docstring), reported in original units.
        cov = conformal_coverage(la, lp, q)
        actual_orig = np.expm1(la)
        pred_orig = np.expm1(lp)
        lower_orig = np.expm1(lp - q)
        upper_orig = np.expm1(lp + q)
        covered_orig = (actual_orig >= lower_orig) & (actual_orig <= upper_orig)
        assert np.array_equal(covered_orig, (la >= lp - q) & (la <= lp + q)), "log-space/original-space coverage mismatch"
        return {
            "coverage": cov["coverage"],
            "mean_width_orig": float(np.mean(upper_orig - lower_orig)),
            "n": cov["n"],
        }

    overall_idx = np.arange(len(mh_test))
    overall_cov = coverage_for(overall_idx, q_overall)
    print(f"Overall Maharashtra 2016-2020 coverage: {overall_cov['coverage']:.3f} (nominal {1 - ALPHA}), "
          f"mean width={overall_cov['mean_width_orig']:.2f}")

    rows = [{"crop": "ALL", "q_used": "overall", "q_log1p": q_overall, **overall_cov}]
    for crop in CROPS:
        name = CANON_TO_YIELD_NAME[crop]
        idx = np.where((mh_test["crop"] == name).to_numpy())[0]
        if len(idx) == 0:
            rows.append({"crop": crop, "q_used": "-", "q_log1p": np.nan, "coverage": np.nan, "mean_width_orig": np.nan, "n": 0})
            continue
        q_used = q_per_crop.get(crop, q_overall)
        cov = coverage_for(idx, q_used)
        rows.append({"crop": crop, "q_used": "per_crop" if crop in q_per_crop else "overall", "q_log1p": q_used, **cov})

    cov_df = pd.DataFrame(rows)
    cov_df.to_csv(REPORTS_RESULTS / "yield_conformal.csv", index=False)

    # --- persist model + metadata for predict_yield_interval() -------------
    meta = {
        "alpha": ALPHA,
        "level": 1 - ALPHA,
        "fit_end_year": FIT_END_YEAR,
        "calib_years": [CALIB_START_YEAR, CALIB_END_YEAR],
        "cat_cols": CAT_COLS,
        "num_cols": num_cols,
        "rf_params": rf_params,
        "q_overall": q_overall,
        "q_per_crop": q_per_crop,
        "n_calib": int(len(abs_resid_calib)),
        "note": "log1p-space residuals/quantile (this repo's log_yield convention, not plain log). "
                "Model fit on year<=2012 (all-India); NOT the production yield_best model.",
    }
    save_model(model, meta, model_path=YIELD_CONFORMAL_MODEL_PATH, metadata_path=YIELD_CONFORMAL_METADATA_PATH)
    print(f"Saved conformal model/metadata to {YIELD_CONFORMAL_MODEL_PATH} / {YIELD_CONFORMAL_METADATA_PATH}")

    # --- findings -----------------------------------------------------------
    miscalibrated = abs(overall_cov["coverage"] - (1 - ALPHA)) > 0.05
    lines = ["# Yield conformal prediction intervals (Phase 9 / E1.5)\n\n"]
    lines.append(
        f"Split conformal, log1p(yield)-space (this repo's `log_yield` convention -- log1p, not plain log; "
        "monotonic, so the coverage guarantee transfers unchanged to the exponentiated original-unit interval). "
        f"RandomForest fit on year<={FIT_END_YEAR} (all-India, n={len(fit_df)}), calibrated on "
        f"{CALIB_START_YEAR}-{CALIB_END_YEAR} residuals (all-India, n={len(abs_resid_calib)}), nominal level "
        f"{(1 - ALPHA) * 100:.0f}%. Applied to the Maharashtra {TEST_START_YEAR}-2020 test set "
        f"(n={len(mh_test)}).\n\n"
    )
    lines.append("| crop | q source | q (log1p) | coverage | nominal | mean width (orig units) | n |\n|---|---|---|---|---|---|---|\n")
    for _, r in cov_df.iterrows():
        cov_str = f"{r['coverage']:.3f}" if pd.notna(r["coverage"]) else "-"
        w_str = f"{r['mean_width_orig']:.2f}" if pd.notna(r["mean_width_orig"]) else "-"
        q_str = f"{r['q_log1p']:.4f}" if pd.notna(r["q_log1p"]) else "-"
        lines.append(f"| {r['crop']} | {r['q_used']} | {q_str} | {cov_str} | {1 - ALPHA:.2f} | {w_str} | {r['n']} |\n")

    lines.append("\n## Findings\n\n")
    if miscalibrated:
        lines.append(
            f"- **MISCALIBRATED**: overall empirical coverage ({overall_cov['coverage']:.3f}) is more than 5 "
            f"percentage points off the nominal {1 - ALPHA:.2f} level. This is a genuine finite-sample-exchangeability "
            "failure worth flagging plainly, not glossing over -- likely because Maharashtra 2016-2020 residuals "
            "are not exchangeable with the all-India 2013-2015 calibration set (distribution shift across states "
            "and/or across time), which is exactly the assumption split-conformal coverage depends on.\n"
        )
    else:
        lines.append(
            f"- Overall empirical coverage ({overall_cov['coverage']:.3f}) is within 5 points of the nominal "
            f"{1 - ALPHA:.2f} level -- the calibration set (all-India 2013-2015) generalizes reasonably to the "
            "Maharashtra 2016-2020 test set for this purpose.\n"
        )
    per_crop_df = cov_df[cov_df["crop"] != "ALL"].dropna(subset=["coverage"])
    if not per_crop_df.empty:
        off = per_crop_df[(per_crop_df["coverage"] - (1 - ALPHA)).abs() > 0.05]
        if not off.empty:
            lines.append(
                f"- Per-crop miscalibration (>5pt off nominal): {', '.join(off['crop'].tolist())} -- per-crop n is "
                "small (see the table), so these are noisier than the overall figure.\n"
            )
    (REPORTS_RESULTS / "yield_conformal.md").write_text("".join(lines), encoding="utf-8")
    print("Wrote yield_conformal.csv / yield_conformal.md")


if __name__ == "__main__":
    sys.exit(main())
