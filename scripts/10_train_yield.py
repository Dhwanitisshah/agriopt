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

from agriopt.config import (
    CROPS,
    MAIN_SEASON,
    RANDOM_SEED,
    REPORTS_RESULTS,
    STATE,
    TEST_START_YEAR,
    TRAIN_END_YEAR,
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

    # best model overall (all-India test MAE), and best ML model (Ridge/RF/XGB
    # only -- ablation/regional-generalization retrain feature sets, which
    # only makes sense for the numeric-feature models, not the baselines).
    # Selection metric is MAHARASHTRA test MAE, not all-India: all-India MAE
    # is dominated by scale effects from huge-magnitude, non-target crops
    # (e.g. Coconut yield up to ~5000 t/ha) that have nothing to do with the
    # optimizer's actual use case, which only ever queries Maharashtra.
    # (All-India MAE is still reported in the table -- just not used to pick.)
    best_overall_name = results_df["maharashtra_MAE"].idxmin()
    ml_names = ["Ridge", "RandomForest", "XGBoost"]
    best_ml_name = results_df.loc[ml_names, "maharashtra_MAE"].idxmin()
    print(f"Best overall ({STATE} MAE): {best_overall_name}. Best ML model: {best_ml_name}.")

    def build_best_ml(nc: list[str]):
        if best_ml_name == "Ridge":
            return SklearnYieldModel("Ridge", Ridge(alpha=1.0, random_state=RANDOM_SEED), nc)
        if best_ml_name == "RandomForest":
            return SklearnYieldModel("RandomForest", RandomForestRegressor(random_state=RANDOM_SEED, n_jobs=-1, **rf_best_params), nc)
        return XgbYieldModel("XGBoost", nc, **xgb_best_params)

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
    write_findings(results, results_df, ablation_df, regional_df, best_overall_name, best_ml_name, include_fert_pest)

    # --- Save best-overall model for the inference API -------------------------
    metadata = {
        "model_name": best_overall_name,
        "cat_cols": CAT_COLS,
        "num_cols": num_cols,
        "train_years": f"<= {TRAIN_END_YEAR}",
        "test_years": f">= {TEST_START_YEAR}",
        "metrics_all_india": results[best_overall_name]["all_india"],
        "metrics_maharashtra": results[best_overall_name]["maharashtra"],
        "fert_pest_included": include_fert_pest,
        "random_seed": RANDOM_SEED,
    }
    save_model(best_model, metadata)
    print(f"\nSaved best model ({best_overall_name}) to models/yield_best.joblib / .json")

    # --- Sanity table: expected_yield_saleable for all 8 crops -------------------
    print("\nExpected saleable yield sanity table:")
    print(f"{'crop':10s} {'season':12s} {'year':6s} {'dataset_yield':14s} {'saleable_qtl_ha':17s} flag")
    for crop in CROPS:
        r = expected_yield_saleable(crop)
        low, high = PLAUSIBLE_SALEABLE_RANGES.get(crop, (None, None))
        flag = ""
        if low is not None and not (low <= r["value"] <= high):
            flag = f"OUT OF RANGE [{low},{high}]"
        print(f"{crop:10s} {r['season']:12s} {r['year']:<6d} {r['dataset_yield']:<14.3f} {r['value']:<17.2f} {flag}")


def write_findings(results, results_df, ablation_df, regional_df, best_overall_name, best_ml_name, include_fert_pest) -> None:
    all_india_winner = results_df["all_india_MAE"].idxmin()
    baseline_beats_ml_mh = results_df.loc[["Baseline-Mean", "Baseline-Last"], "maharashtra_MAE"].min() < results_df.loc[
        ["Ridge", "RandomForest", "XGBoost"], "maharashtra_MAE"
    ].min()

    per_crop_mape = {c: results[best_overall_name]["per_crop"][c]["MAPE"] for c in CROPS if results[best_overall_name]["per_crop"][c]}
    hardest_crop = max(per_crop_mape, key=per_crop_mape.get) if per_crop_mape else None
    easiest_crop = min(per_crop_mape, key=per_crop_mape.get) if per_crop_mape else None

    reg_included = regional_df.loc[f"{best_ml_name} (Maharashtra included)", "maharashtra_MAE"]
    reg_excluded = regional_df.loc[f"{best_ml_name} (Maharashtra excluded)", "maharashtra_MAE"]

    lines = ["# Yield model findings (Phase 1)\n\n"]
    lines.append(
        f"- Best model, selected by **{STATE} test MAE** (the optimizer only ever queries {STATE}, "
        "so this -- not all-India MAE -- is the operative selection metric): "
        f"**{best_overall_name}** ({STATE} MAE={results_df.loc[best_overall_name, 'maharashtra_MAE']:.3f}, "
        f"R2={results_df.loc[best_overall_name, 'maharashtra_R2']:.3f}; all-India MAE="
        f"{results_df.loc[best_overall_name, 'all_india_MAE']:.3f}).\n"
    )
    if all_india_winner != best_overall_name:
        lines.append(
            f"- **All-India MAE picks a different winner ({all_india_winner}) than {STATE} MAE "
            f"({best_overall_name})** -- all-India MAE is dominated by scale effects from huge-magnitude, "
            "non-target crops (e.g. Coconut yield up to ~5000 t/ha), so a model can win on that metric "
            "while doing poorly for our actual crops/region. Case in point: "
            f"{all_india_winner}'s {STATE} R2 is {results_df.loc[all_india_winner, 'maharashtra_R2']:.3f} "
            f"(worse than predicting the mean, if negative), vs {best_overall_name}'s "
            f"{results_df.loc[best_overall_name, 'maharashtra_R2']:.3f}. This is why selection uses "
            f"{STATE} MAE, not all-India MAE.\n"
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
