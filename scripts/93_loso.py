"""Phase 9 / E1.6: leave-one-state-out (LOSO) generalization test.

Extends E1.3 (yield_regional.md, Maharashtra-only in/out preview) to the 10
states with the most rows in the full all-India yield dataset. For each
state: train RandomForest (Phase 1's tuning protocol, year<=2015) on ALL
OTHER states' rows (the held-out state is entirely absent from training),
test on that state's OWN 2016-2020 rows -- compare to the normal
"in-state-included" model (Phase 1's model, trained on every state
including the target one, <=2015), evaluated on the same rows.

Also checks whether degradation correlates with crop-mix similarity: Jaccard
similarity of (state's crop set, in ALL years of data) vs (the pooled crop
set of the other 9 states) -- the "other states" comparison is the more
meaningful one here (not vs Maharashtra) since the OUT-OF-STATE model is
literally trained on those other states' crops, so a state whose crops
barely overlap with what the model was trained on is the crop-mix-similarity
question this experiment actually asks.

Writes reports/results/yield_loso.csv/.md + yield_loso.png. No existing
Phase 1-8 output files are touched.

ASSUMPTION (RF hyperparameters): re-derived via tune_rf per Phase 1's exact
protocol (models/yield_best.json doesn't persist them) -- same as
scripts/91/92. Reused across ALL 10 states' out-of-state models (retuning
per state would be its own confound: this experiment holds the modeling
protocol fixed and only removes the held-out state's rows).
"""
from __future__ import annotations

import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from agriopt.config import RANDOM_SEED, REPORTS_RESULTS, TEST_START_YEAR, TRAIN_END_YEAR
from agriopt.models.yield_model import (
    SklearnYieldModel,
    _force_single_threaded_predict,
    compute_metrics,
    load_model_frame,
    train_test_split_by_year,
    tune_rf,
    tuning_split,
)

N_STATES = 10
NUM_COLS = ["year", "rainfall_mm"]


def top_states(df: pd.DataFrame, n: int = N_STATES) -> list[str]:
    return df["state"].value_counts().head(n).index.tolist()


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return float("nan")
    return len(a & b) / len(a | b)


def main() -> None:
    REPORTS_RESULTS.mkdir(parents=True, exist_ok=True)
    df, _ = load_model_frame()
    train, test = train_test_split_by_year(df)

    states = top_states(df, N_STATES)
    print(f"Top {N_STATES} states by row count: {states}")

    # --- shared RF hyperparams (Phase 1 protocol, reused for every state) ---
    tune_fit, tune_valid = tuning_split(train)
    rf_params = tune_rf(tune_fit, tune_valid, NUM_COLS)
    print(f"RF params (shared across all LOSO runs): {rf_params}")

    def make_rf():
        return SklearnYieldModel("RandomForest", RandomForestRegressor(random_state=RANDOM_SEED, n_jobs=-1, **rf_params), NUM_COLS)

    print("Fitting in-state-included model (Phase 1 protocol, <=2015, all states) ...")
    model_included = make_rf().fit(train)
    _force_single_threaded_predict(model_included)

    rows = []
    for state in states:
        state_test = test[test["state"] == state]
        if state_test.empty:
            print(f"  {state}: no test rows (2016-2020), skipping.")
            continue

        train_excl = train[train["state"] != state].reset_index(drop=True)
        assert state not in set(train_excl["state"].unique()), f"LOSO leak: {state} present in train_excl"
        model_excluded = make_rf().fit(train_excl)
        _force_single_threaded_predict(model_excluded)

        pred_in = model_included.predict(state_test)
        pred_out = model_excluded.predict(state_test)
        m_in = compute_metrics(state_test["yield"], pred_in)
        m_out = compute_metrics(state_test["yield"], pred_out)

        crops_state = set(df[df["state"] == state]["crop"].unique())
        crops_others = set(df[df["state"] != state]["crop"].unique())
        jac = jaccard(crops_state, crops_others)

        mae_degradation_pct = (m_out["MAE"] - m_in["MAE"]) / m_in["MAE"] * 100 if m_in["MAE"] else float("nan")
        mape_degradation_pct = (
            (m_out["MAPE"] - m_in["MAPE"]) / m_in["MAPE"] * 100 if m_in["MAPE"] and not np.isnan(m_in["MAPE"]) else float("nan")
        )

        rows.append(
            {
                "state": state,
                "n_test_rows": len(state_test),
                "mae_in": m_in["MAE"],
                "mae_out": m_out["MAE"],
                "mae_degradation_pct": mae_degradation_pct,
                "mape_in": m_in["MAPE"],
                "mape_out": m_out["MAPE"],
                "mape_degradation_pct": mape_degradation_pct,
                "crop_jaccard_vs_other_states": jac,
            }
        )
        print(f"  {state:16s} n={len(state_test):4d} MAE in={m_in['MAE']:.3f} out={m_out['MAE']:.3f} "
              f"degradation={mae_degradation_pct:+.1f}% jaccard={jac:.3f}")

    loso_df = pd.DataFrame(rows).sort_values("mae_degradation_pct")
    loso_df.to_csv(REPORTS_RESULTS / "yield_loso.csv", index=False)

    # --- plot: in vs out MAE per state --------------------------------------
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(loso_df))
    width = 0.35
    ax.bar(x - width / 2, loso_df["mae_in"], width, label="in-state-included")
    ax.bar(x + width / 2, loso_df["mae_out"], width, label="out-of-state-trained (LOSO)")
    ax.set_xticks(x)
    ax.set_xticklabels(loso_df["state"], rotation=30, ha="right")
    ax.set_ylabel("MAE (yield, dataset units)")
    ax.set_title("Leave-one-state-out: in-state-included vs out-of-state-trained MAE")
    ax.legend()
    fig.tight_layout()
    fig.savefig(REPORTS_RESULTS / "yield_loso.png", dpi=150)
    plt.close(fig)

    # --- crop-mix similarity vs degradation: simple correlation -------------
    valid = loso_df.dropna(subset=["mae_degradation_pct", "crop_jaccard_vs_other_states"])
    corr = float(valid["mae_degradation_pct"].corr(valid["crop_jaccard_vs_other_states"])) if len(valid) > 2 else float("nan")

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.scatter(valid["crop_jaccard_vs_other_states"], valid["mae_degradation_pct"])
    for _, r in valid.iterrows():
        ax.annotate(r["state"], (r["crop_jaccard_vs_other_states"], r["mae_degradation_pct"]), fontsize=8)
    ax.set_xlabel("crop-mix Jaccard similarity (state vs pooled other 9 states)")
    ax.set_ylabel("MAE degradation (%) out-of-state vs in-state")
    ax.set_title(f"Crop-mix similarity vs generalization degradation (r={corr:.2f})")
    fig.tight_layout()
    fig.savefig(REPORTS_RESULTS / "yield_loso_crop_mix.png", dpi=150)
    plt.close(fig)

    # --- write-up ------------------------------------------------------------
    best = loso_df.iloc[0]
    worst = loso_df.iloc[-1]
    lines = ["# Leave-one-state-out generalization (Phase 9 / E1.6, extends E1.3)\n\n"]
    lines.append(
        f"Top {N_STATES} states by row count in the full (all-India) yield dataset: {', '.join(states)}. "
        "For each: RandomForest (Phase 1 protocol, hyperparameters re-derived once via `tune_rf` and shared "
        "across all 10 runs -- see ASSUMPTION in the script docstring) trained on year<=2015, either WITH the "
        "held-out state's rows (in-state-included, the normal Phase 1 model) or WITHOUT them at all "
        "(out-of-state-trained, LOSO) -- tested on the held-out state's own 2016-2020 rows in both cases.\n\n"
    )
    lines.append(
        "| state | n test rows | MAE in | MAE out | degradation % | MAPE in | MAPE out | MAPE degradation % | crop Jaccard vs other states |\n"
        "|---|---|---|---|---|---|---|---|---|\n"
    )
    for _, r in loso_df.iterrows():
        lines.append(
            f"| {r['state']} | {r['n_test_rows']} | {r['mae_in']:.3f} | {r['mae_out']:.3f} | {r['mae_degradation_pct']:+.1f}% | "
            f"{r['mape_in']:.1f} | {r['mape_out']:.1f} | {r['mape_degradation_pct']:+.1f}% | {r['crop_jaccard_vs_other_states']:.3f} |\n"
        )

    lines.append("\n## Findings\n\n")
    lines.append(
        f"- Best-generalizing state (smallest MAE degradation when excluded): **{best['state']}** "
        f"({best['mae_degradation_pct']:+.1f}%). Worst: **{worst['state']}** ({worst['mae_degradation_pct']:+.1f}%).\n"
    )
    lines.append(
        f"- Correlation between crop-mix Jaccard similarity (state vs pooled other {N_STATES - 1} states) and MAE "
        f"degradation: r={corr:.2f} "
        f"({'a state whose crops barely overlap with the training pool degrades more when excluded, as expected' if corr < -0.2 else 'no strong linear relationship in this small (n=' + str(len(valid)) + ') sample -- read the scatter (yield_loso_crop_mix.png), not just r, given how few points there are'}).\n"
    )
    lines.append(
        f"- n={N_STATES} states is a small sample for a correlation claim -- same small-n caveat as the Phase 7 "
        "backtest and other n<20 comparisons in this repo; treat the sign/rough magnitude as suggestive, not a "
        "precise estimate.\n"
    )
    lines.append(
        "- Maharashtra itself is included in this LOSO table (row above) and should read consistently with "
        "E1.3's Maharashtra in/out preview (yield_regional.md) -- both measure the same thing, this one across "
        f"{N_STATES} states instead of just Maharashtra.\n"
    )
    (REPORTS_RESULTS / "yield_loso.md").write_text("".join(lines), encoding="utf-8")
    print("Wrote yield_loso.csv / yield_loso.md / yield_loso.png / yield_loso_crop_mix.png")


if __name__ == "__main__":
    sys.exit(main())
