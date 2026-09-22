"""Phase 1: yield prediction models.

0) Feature sanity check (fertilizer/pesticide year-proxy check, row counts)
   -> reports/results/feature_audit.md
1) Baselines + Ridge + RandomForest + XGBoost, trained on ALL crops/states,
   evaluated all-India / Maharashtra / per target crop in Maharashtra
   -> reports/results/yield_results.csv, yield_results.md
2) Ablation (best ML model: + area_ha, - rainfall, - year)
3) Regional generalization preview (best ML model: Maharashtra excluded vs included)
4) Plots + SHAP summary + findings write-up
5) Save best-overall model for the inference API (models/yield_best.*)
"""
from __future__ import annotations

import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error

from agriopt.config import (
    CROPS,
    MAIN_SEASON,
    RANDOM_SEED,
    REPORTS_RESULTS,
    STATE,
    TEST_START_YEAR,
    TRAIN_END_YEAR,
    YIELD_EVAL_METADATA_PATH,
    YIELD_EVAL_MODEL_PATH,
    YIELD_TO_SALEABLE_QTL_PER_HA,
)
from agriopt.models.yield_model import (
    CANON_TO_YIELD_NAME,
    CAT_COLS,
    CORE_NUM_COLS,
    FERT_PEST_COLS,
    BaselineLast,
    BaselineMean,
    SklearnYieldModel,
    XgbYieldModel,
    YIELD_NAME_TO_CANON,
    compute_metrics,
    decide_fertilizer_pesticide_inclusion,
    expected_yield_saleable,
    feature_variance_audit,
    load_model_frame,
    row_counts_report,
    save_model,
    train_test_split_by_year,
    tune_rf,
    tune_xgb,
    tuning_split,
)

PLAUSIBLE_SALEABLE_RANGES = {
    # crop -> (low, high) quintals of marketed product / ha. sugarcane/tur/
    # soybean/rice/wheat ranges are from the Phase 1 brief; jowar/cotton/
    # maize use the historical Maharashtra range (load_model_frame data)
    # extended 0.5x-2x as a sanity envelope (see feature_audit.md).
    "rice": (20, 50),
    "wheat": (20, 50),
    "tur": (5, 20),
    "soybean": (5, 20),
    "sugarcane": (100, 2000),
}


# --- Step 0: feature sanity check --------------------------------------------


def run_feature_audit(df: pd.DataFrame, dropped: pd.DataFrame) -> bool:
    audit = feature_variance_audit(df)
    include_fert_pest = decide_fertilizer_pesticide_inclusion(audit)
    counts = row_counts_report(df, CROPS, state=STATE)

    lines = ["# Feature audit\n"]
    lines.append(
        "\n## Data-quality: singleton extreme-outlier rows dropped before modeling\n"
        f"{len(dropped)} row(s) dropped (see `flag_singleton_extreme_outliers` in "
        "`agriopt.models.yield_model`): the ONLY observation for their "
        "(state, crop, season) group, at >20x the crop's national median yield "
        "-- e.g. Maharashtra Maize/Autumn/1997 at 989.87 t/ha, physically "
        "impossible. Multi-year patterns (e.g. Chhattisgarh Bajra consistently "
        "30-70x other states' median across 13 years) are NOT touched.\n"
    )
    if not dropped.empty:
        lines.append("\n| crop | season | year | state | area_ha | yield |\n|---|---|---|---|---|---|\n")
        for _, row in dropped.iterrows():
            lines.append(f"| {row['crop']} | {row['season']} | {row['year']} | {row['state']} | {row['area_ha']:.1f} | {row['yield']:.3f} |\n")

    lines.append(
        "\n## fertilizer_per_ha / pesticide_per_ha: year-proxy check\n"
        "Within-year coefficient of variation (std/mean) across all (state, crop, "
        f"season) rows. CV < {0.01} is treated as \"effectively a single national "
        "rate per year\" -- i.e. a year proxy carrying no information beyond what "
        "the `year` feature already provides.\n"
    )
    lines.append("\n| column | mean within-year std | mean within-year mean | mean within-year CV | year proxy? |\n")
    lines.append("|---|---|---|---|---|\n")
    for _, row in audit.iterrows():
        lines.append(
            f"| {row['column']} | {row['mean_within_year_std']:.6g} | {row['mean_within_year_mean']:.6g} | "
            f"{row['mean_within_year_cv']:.6g} | {row['year_proxy']} |\n"
        )
    verdict = (
        "**Verdict: fertilizer_per_ha and pesticide_per_ha are YEAR PROXIES "
        "(near-zero within-year variance) -> EXCLUDED from the main feature set "
        "(year is kept).**\n"
        if not include_fert_pest
        else "**Verdict: fertilizer_per_ha and pesticide_per_ha carry real "
        "within-year signal -> INCLUDED in the main feature set.**\n"
    )
    lines.append(f"\n{verdict}")

    lines.append(
        f"\n## Row counts: train (<={TRAIN_END_YEAR}) vs test (>={TEST_START_YEAR})\n"
    )
    lines.append(
        f"\n| crop | all-India train | all-India test | {STATE} train | {STATE} test |\n"
        "|---|---|---|---|---|\n"
    )
    for _, row in counts.iterrows():
        lines.append(
            f"| {row['crop']} | {row['all_india_train']} | {row['all_india_test']} | "
            f"{row[f'{STATE.lower()}_train']} | {row[f'{STATE.lower()}_test']} |\n"
        )

    (REPORTS_RESULTS / "feature_audit.md").write_text("".join(lines), encoding="utf-8")
    print(f"Feature audit: fert/pest include={include_fert_pest}. Wrote feature_audit.md")
    return include_fert_pest


# --- Evaluation helpers -------------------------------------------------------


def evaluate_model(model, all_india_test: pd.DataFrame, mh_test: pd.DataFrame, crops: list[str]) -> dict:
    result = {
        "all_india": compute_metrics(all_india_test["yield"], model.predict(all_india_test)),
        "maharashtra": compute_metrics(mh_test["yield"], model.predict(mh_test)) if len(mh_test) else None,
        "per_crop": {},
    }
    for crop in crops:
        name = CANON_TO_YIELD_NAME[crop]
        sub = mh_test[mh_test["crop"] == name]
        if sub.empty:
            result["per_crop"][crop] = None
            continue
        pred = model.predict(sub)
        m = compute_metrics(sub["yield"], pred)
        result["per_crop"][crop] = {"MAE": m["MAE"], "MAPE": m["MAPE"]}
    return result


def write_results_table(results: dict[str, dict], crops: list[str]) -> pd.DataFrame:
    rows = []
    for model_name, r in results.items():
        row = {"model": model_name}
        for scope in ("all_india", "maharashtra"):
            m = r[scope]
            if m is None:
                continue
            for metric, val in m.items():
                row[f"{scope}_{metric}"] = val
        for crop in crops:
            pc = r["per_crop"].get(crop)
            row[f"{crop}_MAE"] = pc["MAE"] if pc else np.nan
            row[f"{crop}_MAPE"] = pc["MAPE"] if pc else np.nan
        rows.append(row)
    return pd.DataFrame(rows).set_index("model")


def markdown_table_bold_best(df: pd.DataFrame, lower_is_better_cols: set[str], higher_is_better_cols: set[str]) -> str:
    lines = ["| model | " + " | ".join(df.columns) + " |\n"]
    lines.append("|---|" + "---|" * len(df.columns) + "\n")
    best_idx = {}
    for col in df.columns:
        series = df[col].dropna()
        if series.empty:
            continue
        if col in lower_is_better_cols:
            best_idx[col] = series.idxmin()
        elif col in higher_is_better_cols:
            best_idx[col] = series.idxmax()
    for model_name, row in df.iterrows():
        cells = [model_name]
        for col in df.columns:
            val = row[col]
            if pd.isna(val):
                cells.append("-")
                continue
            text = f"{val:.3f}" if isinstance(val, float) else str(val)
            if best_idx.get(col) == model_name:
                text = f"**{text}**"
            cells.append(text)
        lines.append("| " + " | ".join(cells) + " |\n")
    return "".join(lines)


# --- Main ----------------------------------------------------------------


def main() -> None:
    REPORTS_RESULTS.mkdir(parents=True, exist_ok=True)

    print("Loading yield_clean.parquet ...")
    df, dropped = load_model_frame()
    print(f"  {len(df)} rows after dropping {len(dropped)} singleton extreme-outlier rows.")

    include_fert_pest = run_feature_audit(df, dropped)
    num_cols = CORE_NUM_COLS + (FERT_PEST_COLS if include_fert_pest else [])
    print(f"Main feature set: {CAT_COLS + num_cols}")

    train, test = train_test_split_by_year(df)
    all_india_test = test
    mh_test = test[test["state"] == STATE]
    print(f"Train: {len(train)} rows (<= {TRAIN_END_YEAR}). Test: {len(test)} rows (>= {TEST_START_YEAR}), "
          f"{len(mh_test)} in {STATE}.")

    tune_fit, tune_valid = tuning_split(train)
    print(f"Tuning: fit on {len(tune_fit)} rows (< 2013), validate on {len(tune_valid)} rows (2013-2015).")

    # --- fit baselines -----------------------------------------------------
    baseline_mean = BaselineMean().fit(train)
    baseline_last = BaselineLast().fit(train)

    # --- fit Ridge (no tuning grid specified) -------------------------------
    ridge = SklearnYieldModel("Ridge", Ridge(alpha=1.0, random_state=RANDOM_SEED), num_cols).fit(train)

    # --- tune + refit RandomForest -------------------------------------------
    print("Tuning RandomForest (12 combos) ...")
    rf_best_params = tune_rf(tune_fit, tune_valid, num_cols)
    print(f"  best RF params: {rf_best_params}")
    rf = SklearnYieldModel(
        "RandomForest", RandomForestRegressor(random_state=RANDOM_SEED, n_jobs=-1, **rf_best_params), num_cols
    ).fit(train)

    # --- tune + refit XGBoost -------------------------------------------------
    print("Tuning XGBoost (12 combos) ...")
    xgb_best_params = tune_xgb(tune_fit, tune_valid, num_cols)
    print(f"  best XGB params: {xgb_best_params}")
    xgb = XgbYieldModel("XGBoost", num_cols, **xgb_best_params).fit(train)

    models = {
        "Baseline-Mean": baseline_mean,
        "Baseline-Last": baseline_last,
        "Ridge": ridge,
        "RandomForest": rf,
        "XGBoost": xgb,
    }

    # --- E1.1: main results table --------------------------------------------
    print("\nEvaluating all models ...")
    results = {name: evaluate_model(model, all_india_test, mh_test, CROPS) for name, model in models.items()}
    results_df = write_results_table(results, CROPS)
    results_df.to_csv(REPORTS_RESULTS / "yield_results.csv")

    lower_better = {c for c in results_df.columns if c.endswith(("_MAE", "_RMSE", "_MAPE"))}
    higher_better = {c for c in results_df.columns if c.endswith("_R2")}
    md = ["# Yield model results (E1.1)\n\n", markdown_table_bold_best(results_df, lower_better, higher_better)]
    (REPORTS_RESULTS / "yield_results.md").write_text("".join(md), encoding="utf-8")
    print("Wrote yield_results.csv / yield_results.md")

    # --- Model family selection: VALIDATION Maharashtra MAE, NOT test --------
    # Selecting the winning model FAMILY on the test set would leak test
    # information into a modeling decision (the classic train/select/evaluate
    # conflation). Instead, refit each of the 5 families on tune_fit (<2013)
    # and pick by MAE on tune_valid's Maharashtra rows (2013-2015) -- the same
    # window RF/XGB hyperparameters were already tuned on, just now used to
    # choose AMONG families too. The test table above is unaffected/unchanged;
    # it's still computed for every model on the full <=2015-trained versions.
    ml_names = ["Ridge", "RandomForest", "XGBoost"]
    val_mh = tune_valid[tune_valid["state"] == STATE]
    print(f"\nSelecting best model family on VALIDATION {STATE} MAE "
          f"({len(val_mh)} rows, 2013-2015; fit on {len(tune_fit)} rows < 2013) -- not test.")
    val_models = {
        "Baseline-Mean": BaselineMean().fit(tune_fit),
        "Baseline-Last": BaselineLast().fit(tune_fit),
        "Ridge": SklearnYieldModel("Ridge", Ridge(alpha=1.0, random_state=RANDOM_SEED), num_cols).fit(tune_fit),
        "RandomForest": SklearnYieldModel(
            "RandomForest", RandomForestRegressor(random_state=RANDOM_SEED, n_jobs=-1, **rf_best_params), num_cols
        ).fit(tune_fit),
        "XGBoost": XgbYieldModel("XGBoost", num_cols, **xgb_best_params).fit(tune_fit),
    }
    val_mae = {name: float(mean_absolute_error(val_mh["yield"], m.predict(val_mh))) for name, m in val_models.items()}
    for name, mae in sorted(val_mae.items(), key=lambda kv: kv[1]):
        print(f"  {name:15s} validation {STATE} MAE = {mae:.4f}")

    best_overall_name = min(val_mae, key=val_mae.get)
    best_ml_name = min((k for k in val_mae if k in ml_names), key=lambda k: val_mae[k])
    test_would_have_picked = results_df["maharashtra_MAE"].idxmin()
    selection_changed = best_overall_name != test_would_have_picked
    print(f"Best overall (VALIDATION {STATE} MAE): {best_overall_name}. Best ML model: {best_ml_name}.")
    if selection_changed:
        print(f"  NOTE: differs from what TEST-based selection would have picked ({test_would_have_picked}).")

    def build_model_by_name(name: str, nc: list[str]):
        if name == "Baseline-Mean":
            return BaselineMean()
        if name == "Baseline-Last":
            return BaselineLast()
        if name == "Ridge":
            return SklearnYieldModel("Ridge", Ridge(alpha=1.0, random_state=RANDOM_SEED), nc)
        if name == "RandomForest":
            return SklearnYieldModel("RandomForest", RandomForestRegressor(random_state=RANDOM_SEED, n_jobs=-1, **rf_best_params), nc)
        if name == "XGBoost":
            return XgbYieldModel("XGBoost", nc, **xgb_best_params)
        raise ValueError(name)

    def build_best_ml(nc: list[str]):
        return build_model_by_name(best_ml_name, nc)

    # --- E1.2: ablation --------------------------------------------------------
    print("\nRunning ablation ...")
    train_ab = train.copy()
    train_ab["area_ha_log"] = np.log1p(train_ab["area_ha"])
    test_ab = test.copy()
    test_ab["area_ha_log"] = np.log1p(test_ab["area_ha"])
    mh_test_ab = test_ab[test_ab["state"] == STATE]

    ablations = {
        f"{best_ml_name} (main)": (num_cols, train, test, mh_test),
        f"{best_ml_name} + area_ha(log)": (num_cols + ["area_ha_log"], train_ab, test_ab, mh_test_ab),
        f"{best_ml_name} - rainfall": ([c for c in num_cols if c != "rainfall_mm"], train, test, mh_test),
        f"{best_ml_name} - year": ([c for c in num_cols if c != "year"], train, test, mh_test),
    }
    ablation_results = {}
    for label, (nc, tr, te, mte) in ablations.items():
        m = build_best_ml(nc).fit(tr)
        ablation_results[label] = evaluate_model(m, te, mte, CROPS)
    ablation_df = write_results_table(ablation_results, CROPS)
    ablation_df[[c for c in ablation_df.columns if c.startswith(("all_india", "maharashtra"))]].to_csv(
        REPORTS_RESULTS / "yield_ablation.csv"
    )
    ab_cols = [c for c in ablation_df.columns if c.startswith(("all_india", "maharashtra"))]
    ab_md = ["# Yield model ablation (E1.2)\n\n", markdown_table_bold_best(ablation_df[ab_cols], lower_better & set(ab_cols), higher_better & set(ab_cols))]
    (REPORTS_RESULTS / "yield_ablation.md").write_text("".join(ab_md), encoding="utf-8")
    print("Wrote yield_ablation.csv / yield_ablation.md")

    # --- E1.3: regional generalization preview ----------------------------------
    print("\nRunning regional generalization preview ...")
    train_no_mh = train[train["state"] != STATE]
    model_no_mh = build_best_ml(num_cols).fit(train_no_mh)
    model_with_mh = models[best_ml_name]

    regional_results = {
        f"{best_ml_name} (Maharashtra included)": evaluate_model(model_with_mh, all_india_test, mh_test, CROPS),
        f"{best_ml_name} (Maharashtra excluded)": evaluate_model(model_no_mh, all_india_test, mh_test, CROPS),
    }
    regional_df = write_results_table(regional_results, CROPS)
    regional_df.to_csv(REPORTS_RESULTS / "yield_regional.csv")
    reg_md = ["# Regional generalization preview (E1.3)\n\n", markdown_table_bold_best(regional_df, lower_better, higher_better)]
    (REPORTS_RESULTS / "yield_regional.md").write_text("".join(reg_md), encoding="utf-8")
    print("Wrote yield_regional.csv / yield_regional.md")

    # --- Plots -----------------------------------------------------------------
    print("\nPlotting ...")
    best_model = models[best_overall_name]

    fig, ax = plt.subplots(figsize=(7, 7))
    pred = best_model.predict(mh_test)
    ax.scatter(mh_test["yield"], pred, alpha=0.5, s=15)
    lims = [0, max(mh_test["yield"].max(), pred.max()) * 1.05]
    ax.plot(lims, lims, "r--", linewidth=1)
    ax.set_xlim(lims)
    ax.set_ylim(lims)
    ax.set_xlabel("actual yield")
    ax.set_ylabel("predicted yield")
    ax.set_title(f"{STATE} test set: predicted vs actual ({best_overall_name})")
    fig.tight_layout()
    fig.savefig(REPORTS_RESULTS / "pred_vs_actual.png", dpi=150)
    plt.close(fig)

    per_crop_mape = {c: results[best_overall_name]["per_crop"][c]["MAPE"] for c in CROPS if results[best_overall_name]["per_crop"][c]}
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(list(per_crop_mape.keys()), list(per_crop_mape.values()))
    ax.set_ylabel("MAPE (%)")
    ax.set_title(f"{STATE} per-crop MAPE ({best_overall_name})")
    plt.xticks(rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(REPORTS_RESULTS / "per_crop_mape.png", dpi=150)
    plt.close(fig)

    print("SHAP summary for XGBoost ...")
    sample = test.sample(n=min(2000, len(test)), random_state=RANDOM_SEED)
    X_sample = xgb._prep(sample, fit=False)
    explainer = shap.TreeExplainer(xgb.model)
    shap_values = explainer.shap_values(X_sample)
    fig = plt.figure(figsize=(9, 6))
    shap.summary_plot(shap_values, X_sample, show=False)
    plt.title("XGBoost SHAP summary (all-India test sample)")
    plt.tight_layout()
    plt.savefig(REPORTS_RESULTS / "shap_summary_xgb.png", dpi=150)
    plt.close("all")

    # --- Findings write-up -------------------------------------------------
    write_findings(
        results, results_df, ablation_df, regional_df, best_overall_name, best_ml_name, include_fert_pest,
        val_mae=val_mae, test_would_have_picked=test_would_have_picked, selection_changed=selection_changed,
    )

    # --- Save the EVAL model (<=2015, what the metrics above were computed on) --
    eval_model = models[best_overall_name]
    eval_metadata = {
        "model_name": best_overall_name,
        "cat_cols": CAT_COLS,
        "num_cols": num_cols,
        "train_years": f"<= {TRAIN_END_YEAR}",
        "train_max_year": TRAIN_END_YEAR,
        "test_years": f">= {TEST_START_YEAR}",
        "metrics_all_india": results[best_overall_name]["all_india"],
        "metrics_maharashtra": results[best_overall_name]["maharashtra"],
        "fert_pest_included": include_fert_pest,
        "random_seed": RANDOM_SEED,
        "selected_on": "validation (2013-2015, fit <2013)",
    }
    save_model(eval_model, eval_metadata, model_path=YIELD_EVAL_MODEL_PATH, metadata_path=YIELD_EVAL_METADATA_PATH)
    print(f"\nSaved eval model ({best_overall_name}, train <= {TRAIN_END_YEAR}) to models/yield_eval.joblib / .json")

    # --- Refit the SAME model family+hyperparams on ALL years for inference -----
    all_years_max = int(df["year"].max())
    inference_model = build_model_by_name(best_overall_name, num_cols).fit(df)
    inference_metadata = dict(eval_metadata)
    inference_metadata["train_years"] = f"<= {all_years_max} (all available years)"
    inference_metadata["train_max_year"] = all_years_max
    inference_metadata.pop("test_years", None)
    inference_metadata["note"] = "Refit on all years for inference; metrics above are from the <=2015 eval model, not this one."
    save_model(inference_model, inference_metadata)
    print(f"Saved inference model ({best_overall_name}, train <= {all_years_max}) to models/yield_best.joblib / .json")

    # --- Sanity table: expected_yield_saleable, EVAL model vs INFERENCE model ---
    print("\nExpected saleable yield sanity table (eval <=2015 model vs inference all-years model):")
    print(f"{'crop':10s} {'season':12s} {'year':6s} {'old(eval) qtl/ha':18s} {'new(inference) qtl/ha':22s} flag")
    for crop in CROPS:
        r_old = expected_yield_saleable(crop, model=eval_model, num_cols=num_cols)
        r_new = expected_yield_saleable(crop, model=inference_model, num_cols=num_cols)
        low, high = PLAUSIBLE_SALEABLE_RANGES.get(crop, (None, None))
        flag = ""
        if low is not None and not (low <= r_new["value"] <= high):
            flag = f"OUT OF RANGE [{low},{high}]"
        print(f"{crop:10s} {r_new['season']:12s} {r_new['year']:<6d} {r_old['value']:<18.2f} {r_new['value']:<22.2f} {flag}")


def write_findings(
    results, results_df, ablation_df, regional_df, best_overall_name, best_ml_name, include_fert_pest,
    val_mae, test_would_have_picked, selection_changed,
) -> None:
    all_india_winner = results_df["all_india_MAE"].idxmin()
    baseline_beats_ml_mh = results_df.loc[["Baseline-Mean", "Baseline-Last"], "maharashtra_MAE"].min() < results_df.loc[
        ["Ridge", "RandomForest", "XGBoost"], "maharashtra_MAE"
    ].min()

    per_crop_mape = {c: results[best_overall_name]["per_crop"][c]["MAPE"] for c in CROPS if results[best_overall_name]["per_crop"][c]}
    hardest_crop = max(per_crop_mape, key=per_crop_mape.get) if per_crop_mape else None
    easiest_crop = min(per_crop_mape, key=per_crop_mape.get) if per_crop_mape else None

    reg_included = regional_df.loc[f"{best_ml_name} (Maharashtra included)", "maharashtra_MAE"]
    reg_excluded = regional_df.loc[f"{best_ml_name} (Maharashtra excluded)", "maharashtra_MAE"]

    lines = ["# Yield model findings (Phase 1 / Phase 2 fix)\n\n"]
    lines.append(
        "- **Model selected on validation, not test.** Best model family chosen by "
        f"{STATE} MAE on the validation window (fit <2013, evaluate 2013-2015): "
        f"**{best_overall_name}** (validation {STATE} MAE="
        f"{val_mae[best_overall_name]:.4f}; next best: "
        f"{', '.join(f'{k}={v:.4f}' for k, v in sorted(val_mae.items(), key=lambda kv: kv[1]) if k != best_overall_name)}).\n"
    )
    if selection_changed:
        lines.append(
            f"- **The winner changed vs test-based selection**: picking by test-set {STATE} MAE instead "
            f"would have chosen **{test_would_have_picked}** (test {STATE} MAE="
            f"{results_df.loc[test_would_have_picked, 'maharashtra_MAE']:.3f}) instead of "
            f"**{best_overall_name}** (test {STATE} MAE={results_df.loc[best_overall_name, 'maharashtra_MAE']:.3f}). "
            "Validation-based selection is used for the actual deployed model to avoid fitting the "
            "selection decision to the test set.\n"
        )
    else:
        lines.append(
            f"- Validation-based selection agrees with what test-based selection would have picked "
            f"({best_overall_name}) -- the fix changes the *methodology* (no more test-set leakage into "
            "model selection) without changing the outcome here.\n"
        )
    lines.append(
        f"- Test-set metrics reported below are for **{best_overall_name}** "
        f"({STATE} test MAE={results_df.loc[best_overall_name, 'maharashtra_MAE']:.3f}, "
        f"R2={results_df.loc[best_overall_name, 'maharashtra_R2']:.3f}; all-India test MAE="
        f"{results_df.loc[best_overall_name, 'all_india_MAE']:.3f}) -- computed purely for reporting, "
        "played no role in selecting it.\n"
    )
    if all_india_winner != best_overall_name:
        lines.append(
            f"- All-India test MAE would have picked a different model ({all_india_winner}) than "
            f"{STATE} MAE ({best_overall_name}) -- all-India MAE is dominated by scale effects from "
            "huge-magnitude, non-target crops (e.g. Coconut yield up to ~5000 t/ha), so a model can win "
            "on that metric while doing poorly for our actual crops/region. Case in point: "
            f"{all_india_winner}'s {STATE} R2 is {results_df.loc[all_india_winner, 'maharashtra_R2']:.3f} "
            f"(worse than predicting the mean, if negative), vs {best_overall_name}'s "
            f"{results_df.loc[best_overall_name, 'maharashtra_R2']:.3f}.\n"
        )
    lines.append(
        f"- {'A baseline (Baseline-Mean/Baseline-Last) beats every ML model on ' + STATE + ' MAE' if baseline_beats_ml_mh else 'Every ML model (Ridge/RandomForest/XGBoost) beats both baselines on ' + STATE + ' MAE'} "
        "-- yield is a fairly stable, group-predictable quantity given (state, crop, season) history, so this is not surprising either way.\n"
    )
    lines.append(
        f"- Hardest {STATE} crop by MAPE: **{hardest_crop}** ({per_crop_mape.get(hardest_crop, float('nan')):.1f}%). "
        f"Easiest: **{easiest_crop}** ({per_crop_mape.get(easiest_crop, float('nan')):.1f}%).\n"
    )
    lines.append(
        f"- fertilizer_per_ha/pesticide_per_ha were {'INCLUDED' if include_fert_pest else 'EXCLUDED'} from the "
        "main feature set (see feature_audit.md) -- they were found to be "
        f"{'genuinely informative within-year' if include_fert_pest else 'a year proxy (near-zero within-year variance), so year alone covers that signal'}.\n"
    )
    lines.append(
        f"- Ablation ({best_ml_name}): adding area_ha(log) changed all-India MAE from "
        f"{ablation_df.loc[f'{best_ml_name} (main)', 'all_india_MAE']:.3f} to "
        f"{ablation_df.loc[f'{best_ml_name} + area_ha(log)', 'all_india_MAE']:.3f}; "
        f"dropping rainfall changed it to {ablation_df.loc[f'{best_ml_name} - rainfall', 'all_india_MAE']:.3f}; "
        f"dropping year changed it to {ablation_df.loc[f'{best_ml_name} - year', 'all_india_MAE']:.3f} "
        "(see yield_ablation.md for the full breakdown, all-India + Maharashtra).\n"
    )
    lines.append(
        f"- Regional generalization ({best_ml_name}): training WITHOUT Maharashtra rows gives "
        f"{STATE} test MAE={reg_excluded:.3f}, vs {reg_included:.3f} when Maharashtra is included "
        f"({'a real drop' if reg_excluded > reg_included * 1.1 else 'a small/no drop'} in accuracy when "
        f"the model has never seen {STATE} data -- relevant for how much local calibration the "
        "optimizer's yield model will eventually need).\n"
    )
    lines.append(
        "- MAPE is computed on original-scale yield per crop; crops with naturally low absolute yield "
        "(e.g. pulses like tur) can show higher MAPE for the same absolute error than high-yield crops "
        "(e.g. sugarcane), since MAPE divides by the (small) true value -- read MAE alongside MAPE, not MAPE alone.\n"
    )
    lines.append(
        "- This is Phase 1 (yield only): predicted yield feeds the optimizer's profit objective only after "
        "conversion to quintals of marketed product via YIELD_TO_SALEABLE_QTL_PER_HA (rice/cotton unit "
        "assumptions, docs/units.md) and multiplication by a price forecast (Phase 2+, not built yet).\n"
    )
    (REPORTS_RESULTS / "yield_findings.md").write_text("".join(lines), encoding="utf-8")
    print("Wrote yield_findings.md")


if __name__ == "__main__":
    sys.exit(main())
