"""Yield model, evaluated only where the optimizer uses it.

The headline yield table (scripts/10_train_yield.py -> yield_results.csv) pools
every crop in Maharashtra, in whatever unit the Kaggle file uses (tonnes/ha for
most crops, bales/ha for cotton, milled-rice-equivalent for rice), so its pooled
MAE and R^2 mostly measure which crops have big numbers. This script reports,
for the 8 decision crops only and in the units the optimizer uses
(saleable quintals/ha):

  * per-crop MAE / MAPE / RMSE of the RandomForest against three baselines --
    last year, the mean of the last 3 years, and the all-years mean -- and
  * a flag wherever the RandomForest does NOT beat the last-3-year mean.

Two designs, both on the 4 test years 2016-2019 (so n=4 per crop -- directional):
  B. one-step-ahead (PRIMARY): for each decision year t, the RF refit on years
     <= t-1 (the same models the decision backtest uses) vs baselines computed
     from years <= t-1. This is how the model is used in practice.
  A. fixed origin: the single model trained on <= 2015 (models/yield_eval) predicts
     2016-2019 (up to 4 years ahead), baselines fitted on <= 2015.

Also regenerates reports/results/yield_results.md WITHOUT the pooled R^2 columns
(yield_results.csv is untouched, as an audit trail).

Writes reports/results/yield_decision_crops.csv / .md. Needs the models already
trained (does NOT retrain anything).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from agriopt.backtest.info import (
    _yield_series_leakfree,
    refit_yield_model_for_year,
    realized_yield_for_year,
    yield_forecast_for_year,
)
from agriopt.config import CROPS, MAIN_SEASON, REPORTS_RESULTS, STATE, YIELD_EVAL_MODEL_PATH, YIELD_TO_SALEABLE_QTL_PER_HA
from agriopt.models.yield_model import (
    CANON_TO_YIELD_NAME,
    BaselineLast,
    BaselineMean,
    BaselineRecentMean,
    load_model,
    load_model_frame,
    train_test_split_by_year,
)

YEARS = [2016, 2017, 2018, 2019]  # Maharashtra's yield data ends at 2019
METHODS = ["RandomForest", "Last year", "Last-3-year mean", "All-years mean"]


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    err = np.asarray(y_pred, dtype=float) - np.asarray(y_true, dtype=float)
    return {
        "n": int(len(err)),
        "MAE": float(np.mean(np.abs(err))),
        "MAPE": float(np.mean(np.abs(err) / np.abs(y_true)) * 100),
        "RMSE": float(np.sqrt(np.mean(err**2))),
    }


def one_step_ahead() -> pd.DataFrame:
    """Design B: RF refit on <= t-1 vs baselines from <= t-1, per decision crop."""
    rows = []
    preds = {crop: {m: [] for m in METHODS} for crop in CROPS}
    actual = {crop: [] for crop in CROPS}
    for t in YEARS:
        model, num_cols, meta = refit_yield_model_for_year(t)
        rf = yield_forecast_for_year(t, model, num_cols, meta["train_max_year"], crops=CROPS)
        for crop in CROPS:
            history = _yield_series_leakfree(crop, t - 1)  # saleable qtl/ha, years <= t-1
            truth = realized_yield_for_year(crop, t)
            if truth is None or history.empty:
                continue
            actual[crop].append(truth)
            preds[crop]["RandomForest"].append(rf[crop]["value"])
            preds[crop]["Last year"].append(float(history.iloc[-1]))
            preds[crop]["Last-3-year mean"].append(float(history.tail(3).mean()))
            preds[crop]["All-years mean"].append(float(history.mean()))
    for crop in CROPS:
        for method in METHODS:
            rows.append({"design": "one-step-ahead (refit each year)", "crop": crop, "method": method,
                         **_metrics(np.array(actual[crop]), np.array(preds[crop][method]))})
    return pd.DataFrame(rows)


def fixed_origin() -> pd.DataFrame:
    """Design A: the <=2015 model and baselines predict 2016-2019 rows of each crop's main season."""
    df, _ = load_model_frame()
    train, test = train_test_split_by_year(df)
    models = {
        "RandomForest": load_model(YIELD_EVAL_MODEL_PATH),
        "Last year": BaselineLast().fit(train),
        "Last-3-year mean": BaselineRecentMean(3).fit(train),
        "All-years mean": BaselineMean().fit(train),
    }
    rows = []
    for crop in CROPS:
        sub = test[(test["state"] == STATE) & (test["crop"] == CANON_TO_YIELD_NAME[crop]) & (test["season"] == MAIN_SEASON[crop])]
        sub = sub[sub["year"].isin(YEARS)]
        if sub.empty:
            continue
        to_qtl = np.vectorize(YIELD_TO_SALEABLE_QTL_PER_HA[crop])
        truth = to_qtl(sub["yield"].to_numpy(dtype=float))
        for method, model in models.items():
            rows.append({"design": "fixed origin (trained <= 2015)", "crop": crop, "method": method,
                         **_metrics(truth, to_qtl(np.asarray(model.predict(sub), dtype=float)))})
    return pd.DataFrame(rows)


def verdicts(long_df: pd.DataFrame) -> pd.DataFrame:
    """One row per (design, crop): RF vs the last-3-year mean and vs the best baseline."""
    out = []
    for (design, crop), g in long_df.groupby(["design", "crop"], sort=False):
        by = g.set_index("method")
        baselines = by.drop(index="RandomForest")
        best_name = baselines["MAE"].idxmin()
        out.append({
            "design": design, "crop": crop, "n": int(by.loc["RandomForest", "n"]),
            "rf_MAE": by.loc["RandomForest", "MAE"], "rf_MAPE": by.loc["RandomForest", "MAPE"],
            "last3_MAE": by.loc["Last-3-year mean", "MAE"], "last3_MAPE": by.loc["Last-3-year mean", "MAPE"],
            "best_baseline": best_name, "best_baseline_MAE": baselines.loc[best_name, "MAE"],
            "rf_skill_vs_last3": 1 - by.loc["RandomForest", "MAE"] / by.loc["Last-3-year mean", "MAE"],
            "rf_loses_to_last3": bool(by.loc["RandomForest", "MAE"] > by.loc["Last-3-year mean", "MAE"]),
            "rf_loses_to_best_baseline": bool(by.loc["RandomForest", "MAE"] > baselines.loc[best_name, "MAE"]),
        })
    return pd.DataFrame(out)


def write_md(long_df: pd.DataFrame, verdict_df: pd.DataFrame) -> None:
    lines = ["# Yield model on the 8 decision crops (saleable qtl/ha)\n\n"]
    lines.append(
        "Why not the pooled table: `yield_results.csv` pools every Maharashtra crop in whatever unit the Kaggle "
        "file uses (t/ha, bales/ha, milled-rice equivalent), so its pooled MAE and R^2 mostly reflect which "
        "crops have large numbers -- the pooled R^2 is dropped. Below, only the 8 crops the optimizer allocates, "
        "in the optimizer's units, with a last-3-year state-mean baseline. **n=4 test years (2016-2019) per crop: "
        "directional only.**\n\n"
    )
    for design, vdf in verdict_df.groupby("design", sort=False):
        lines.append(f"## {design}\n\n")
        lines.append("| crop | n | RF MAE | RF MAPE % | last-3-yr MAE | last-3-yr MAPE % | best baseline (MAE) | RF skill vs last-3-yr | RF beats last-3-yr? |\n|---|---|---|---|---|---|---|---|---|\n")
        for _, r in vdf.iterrows():
            lines.append(
                f"| {r['crop']} | {r['n']} | {r['rf_MAE']:.2f} | {r['rf_MAPE']:.1f} | {r['last3_MAE']:.2f} | {r['last3_MAPE']:.1f} | "
                f"{r['best_baseline']} ({r['best_baseline_MAE']:.2f}) | {r['rf_skill_vs_last3']:+.0%} | "
                f"{'**NO -- RF loses**' if r['rf_loses_to_last3'] else 'yes'} |\n"
            )
        n_lose = int(vdf["rf_loses_to_last3"].sum())
        n_lose_best = int(vdf["rf_loses_to_best_baseline"].sum())
        losers = ", ".join(vdf.loc[vdf["rf_loses_to_last3"], "crop"]) or "none"
        lines.append(
            f"\nRF loses to the last-3-year mean on **{n_lose}/{len(vdf)}** crops ({losers}) and to the best of the three "
            f"baselines on {n_lose_best}/{len(vdf)}. Mean MAPE over the 8 crops: RF "
            f"{vdf['rf_MAPE'].mean():.1f}% vs last-3-year mean {vdf['last3_MAPE'].mean():.1f}%.\n\n"
        )
        full = long_df[long_df["design"] == design].pivot(index="crop", columns="method", values="MAPE").reindex(vdf["crop"])
        lines.append("MAPE % by method:\n\n| crop | " + " | ".join(METHODS) + " |\n|---|" + "---|" * len(METHODS) + "\n")
        for crop, r in full.iterrows():
            lines.append(f"| {crop} | " + " | ".join(f"{r[m]:.1f}" for m in METHODS) + " |\n")
        lines.append("\n")
    (REPORTS_RESULTS / "yield_decision_crops.md").write_text("".join(lines), encoding="utf-8")
    print("Wrote yield_decision_crops.md")


def rewrite_pooled_table_without_r2() -> None:
    """yield_results.md without the *_R2 columns (csv left as the audit trail)."""
    spec = importlib.util.spec_from_file_location("train_10", REPO_ROOT / "scripts" / "10_train_yield.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    results_df = pd.read_csv(REPORTS_RESULTS / "yield_results.csv").set_index("model")
    shown = results_df[[c for c in results_df.columns if not c.endswith("_R2")]]
    lower = {c for c in shown.columns if c.endswith(("_MAE", "_RMSE", "_MAPE"))}
    md = [
        "# Yield model results (E1.1)\n\n",
        "> Pooled columns (`all_india_*`, `maharashtra_*`) mix crops in different units, so they mostly rank crops by "
        "magnitude; the pooled R^2 has been dropped. Use `yield_decision_crops.md` for the 8 crops the optimizer allocates.\n\n",
        mod.markdown_table_bold_best(shown, lower, set()),
    ]
    (REPORTS_RESULTS / "yield_results.md").write_text("".join(md), encoding="utf-8")
    print("Wrote yield_results.md (no R^2 columns)")


def main() -> None:
    long_df = pd.concat([one_step_ahead(), fixed_origin()], ignore_index=True)
    long_df.to_csv(REPORTS_RESULTS / "yield_decision_crops.csv", index=False)
    verdict_df = verdicts(long_df)
    verdict_df.to_csv(REPORTS_RESULTS / "yield_decision_crops_verdicts.csv", index=False)
    write_md(long_df, verdict_df)
    rewrite_pooled_table_without_r2()
    print(verdict_df.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
