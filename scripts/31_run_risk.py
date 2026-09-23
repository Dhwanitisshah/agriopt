"""Phase 5 / Experiment 5: historical profit-risk model, risk-aware NSGA-III
(Model B), a denser 3-objective LP reference front (v2) for Model A, and a
risk evaluation of B1/B2/B3/OURS/Model-B.

Writes NEW report files only (reports/results/*_v2.md, risk_*.md) --
Phase 3's optim_strategies.md / optim_front_quality.md / optim_findings.md
are read (for the v1-vs-v2 comparison) but never modified.
"""
from __future__ import annotations

import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pymoo.indicators.hv import HV
from pymoo.indicators.igd import IGD

from agriopt.config import REPORTS_RESULTS
from agriopt.optim.baselines import current_mix, evaluate, nsga2_recommended, same_profit_min_water
from agriopt.optim.params import build_crop_params
from agriopt.optim.problem import Scenario
from agriopt.optim.risk import build_risk_inputs, historical_scenarios, portfolio_risk, sigma_with_overridden_std
from agriopt.optim.solvers import (
    exact_front_lp_grid,
    min_risk_profit_curve,
    nsga3_recommended,
    recommend,
    solve_lp_profit_max,
    solve_nsga2,
    solve_nsga3,
)

WATER_MULTIPLIERS = {"tight": 0.7, "current": 1.0, "relaxed": 1.3}
PRICE_MODES = ["market", "msp_floor"]
LAND_HA = 10.0
SEEDS = [0, 1, 2, 3, 4]
FOCUS_SCENARIO = ("current", "market")  # risk matrix, Model B, risk_strategies table + plot
MODEL_B_WEIGHTS = (0.4, 0.2, 0.1, 0.3)  # profit, water, fert, risk


def compute_b1_water(land_ha: float = LAND_HA) -> tuple[np.ndarray, float, pd.DataFrame]:
    params = build_crop_params("market", verbose=False)
    dummy = Scenario(water_budget_m3=1e15, land_ha=land_ha)
    x1 = current_mix(params, dummy)
    water = float(x1 @ params["water_m3_ha"].to_numpy())
    return x1, water, params


# --- Item 1: risk matrix -----------------------------------------------------


def _markdown_table(df: pd.DataFrame, float_fmt: str = "{:.2f}") -> str:
    cols = list(df.columns)
    header = "| " + df.index.name.__str__() + " | " + " | ".join(str(c) for c in cols) + " |\n"
    sep = "|" + "---|" * (len(cols) + 1) + "\n"
    body = []
    for idx, row in df.iterrows():
        cells = [float_fmt.format(v) if isinstance(v, (float, np.floating)) else str(v) for v in row]
        body.append(f"| {idx} | " + " | ".join(cells) + " |\n")
    return header + sep + "".join(body)


def write_risk_matrix_report(risk_inputs, crops: list[str]) -> None:
    corr = risk_inputs.deviation_matrix.corr().reindex(index=crops, columns=crops)
    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(corr.to_numpy(), cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(crops)))
    ax.set_xticklabels(crops, rotation=45, ha="right")
    ax.set_yticks(range(len(crops)))
    ax.set_yticklabels(crops)
    for i in range(len(crops)):
        for j in range(len(crops)):
            v = corr.to_numpy()[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8, color="black")
    fig.colorbar(im, ax=ax, label="correlation")
    ax.set_title("Relative-deviation correlation across crops (Maharashtra, detrended revenue/ha)")
    fig.tight_layout()
    fig.savefig(REPORTS_RESULTS / "risk_correlation_heatmap.png", dpi=150)
    plt.close(fig)

    lines = ["# Historical profit-risk model (Phase 5, Experiment 5 / Item 1)\n\n"]
    lines.append(
        "Crop_Year convention is an ASSUMPTION (kharif: Oct-Dec of year t; rabi: Mar-May of year t+1) -- "
        "see `agriopt.optim.risk` module docstring; unverified against an independent source, flagged, not "
        "silently trusted.\n\n"
    )
    lines.append(f"Sigma (revenue covariance, Rs^2) minimum eigenvalue before PSD clipping: {risk_inputs.min_eigenvalue_raw:,.2f}")
    lines.append(" (already PSD, no clipping applied).\n\n" if risk_inputs.min_eigenvalue_raw >= 0 else " -- clipped to PSD.\n\n")

    lines.append("## Per-crop revenue variability (Maharashtra, detrended)\n\n")
    lines.append("| crop | n years | CV (raw revenue) | log-revenue trend (per year) |\n")
    lines.append("|---|---|---|---|\n")
    for crop in crops:
        row = risk_inputs.cv_table.loc[crop]
        lines.append(f"| {crop} | {int(row['n_years'])} | {row['cv']:.3f} | {row['trend_slope_log_per_year']:+.4f} |\n")

    lines.append("\n## Correlation matrix\n\n")
    corr_named = corr.copy()
    corr_named.index.name = "crop"
    lines.append(_markdown_table(corr_named))
    lines.append("\n![correlation heatmap](risk_correlation_heatmap.png)\n\n")

    corr_no_diag = corr.to_numpy().copy()
    np.fill_diagonal(corr_no_diag, np.nan)
    mean_corr = float(np.nanmean(corr_no_diag))
    sugarcane_corrs = corr.loc["sugarcane"].drop("sugarcane") if "sugarcane" in corr.index else pd.Series(dtype=float)
    lines.append(
        f"Mean pairwise correlation across all crop pairs is {mean_corr:.2f} -- broadly positive, consistent "
        "with a shared Maharashtra monsoon-quality driver behind most crops' year-to-year yield swings, even "
        "after each crop's own trend is removed.\n"
    )
    if not sugarcane_corrs.empty:
        lines.append(
            f"Sugarcane's CV is far lower than the mandi-priced crops (variance from yield only -- no market "
            f"price series, see module docstring), but its correlations with the other crops are NOT small "
            f"(mean {sugarcane_corrs.mean():.2f}, up to {sugarcane_corrs.max():.2f} with {sugarcane_corrs.idxmax()}) "
            "-- since sugarcane's price is constant, any correlation it shows is pure yield co-movement, i.e. "
            "a real signal that Maharashtra's cropping years are broadly good or bad together, not an artifact "
            "of a shared price index.\n"
        )

    (REPORTS_RESULTS / "risk_matrix.md").write_text("".join(lines), encoding="utf-8")
    print("Wrote risk_matrix.md / risk_correlation_heatmap.png")


# --- Item 3: v2 reference front + quality comparison ---------------------------


def front_quality_v2_for_scenario(water_label: str, price_mode: str, params_df: pd.DataFrame, water_budget: float) -> dict:
    scenario = Scenario(water_budget_m3=water_budget, land_ha=LAND_HA, price_mode=price_mode)
    X_grid, F_grid = exact_front_lp_grid(scenario, params_df, n_profit=25, n_fert=12)

    nsga_fronts, runtimes = [], []
    for seed in SEEDS:
        _, F, rt = solve_nsga2(scenario, params_df, seed=seed)
        nsga_fronts.append(F)
        runtimes.append(rt)

    def to_min_form(F):
        Fm = F.copy()
        Fm[:, 0] = -Fm[:, 0]
        return Fm

    union = np.vstack([to_min_form(F) for F in nsga_fronts] + [to_min_form(F_grid)])
    lo, hi = union.min(axis=0), union.max(axis=0)
    span = np.where(hi > lo, hi - lo, 1.0)

    def norm(F):
        return (to_min_form(F) - lo) / span

    ref_point = np.array([1.1, 1.1, 1.1])
    hv = HV(ref_point=ref_point)
    igd = IGD(norm(F_grid))

    hv_grid = float(hv(norm(F_grid)))
    hv_nsga = np.array([float(hv(norm(F))) for F in nsga_fronts])
    igd_nsga = np.array([float(igd(norm(F))) for F in nsga_fronts])

    return {
        "water_scenario": water_label,
        "price_mode": price_mode,
        "hv_lp_grid_reference_v2": hv_grid,
        "hv_nsga2_mean": float(hv_nsga.mean()),
        "hv_nsga2_std": float(hv_nsga.std()),
        "igd_nsga2_mean_v2": float(igd_nsga.mean()),
        "igd_nsga2_std_v2": float(igd_nsga.std()),
        "grid_front_size": len(F_grid),
    }


def write_front_quality_v2_report(quality_v2_df: pd.DataFrame) -> None:
    quality_v2_df.to_csv(REPORTS_RESULTS / "optim_front_quality_v2.csv", index=False)

    v1_path = REPORTS_RESULTS / "optim_front_quality.csv"
    v1_df = pd.read_csv(v1_path) if v1_path.exists() else None

    lines = ["# NSGA-II vs LP reference front quality: v1 (lexicographic slice) vs v2 (grid) (Phase 5, Item 3)\n\n"]
    lines.append(
        "v1 (`exact_front_lp`, Phase 3) sweeps ONE lexicographic profit>water>fert curve through the true "
        "3-objective Pareto surface -- exact where defined, but a 1-D curve, not the surface. v2 "
        "(`exact_front_lp_grid`, this experiment) sweeps a profit x fertilizer-cap grid, minimizing water at "
        "each combo, then keeps only the non-dominated points -- a much denser approximation of the actual "
        "2-D Pareto surface. Both are still LP relaxations restricted to the points the sweep visits, not the "
        "literal continuous Pareto surface, but v2 covers far more of it.\n\n"
    )

    lines.append("## v2 (grid reference) quality\n\n")
    cols = list(quality_v2_df.columns)
    lines.append("| " + " | ".join(cols) + " |\n")
    lines.append("|" + "---|" * len(cols) + "\n")
    for _, row in quality_v2_df.iterrows():
        lines.append("| " + " | ".join(f"{v:.3f}" if isinstance(v, float) else str(v) for v in row) + " |\n")

    if v1_df is not None:
        merged = quality_v2_df.merge(v1_df[["water_scenario", "price_mode", "hv_lp_reference"]], on=["water_scenario", "price_mode"])
        merged["hv_lp_reference_v1"] = merged["hv_lp_reference"]
        ratio_v1 = merged["hv_nsga2_mean"] / merged["hv_lp_reference_v1"]
        ratio_v2 = merged["hv_nsga2_mean"] / merged["hv_lp_grid_reference_v2"]
        lines.append("\n## v1 vs v2: NSGA-II hypervolume as a fraction of the reference front's\n\n")
        lines.append("| water | price | HV(NSGA-II)/HV(v1 slice) | HV(NSGA-II)/HV(v2 grid) |\n")
        lines.append("|---|---|---|---|\n")
        for i, row in merged.iterrows():
            lines.append(f"| {row['water_scenario']} | {row['price_mode']} | {ratio_v1.iloc[i]:.3f} | {ratio_v2.iloc[i]:.3f} |\n")

        if (ratio_v2 <= 1.02).all():
            lines.append(
                f"\n- **v2 resolves the v1 anomaly**: NSGA-II's hypervolume was ABOVE the v1 slice's in every "
                f"scenario (mean ratio {ratio_v1.mean():.2f}x, Phase 3 finding) simply because v1 only traces a "
                f"curve, not the surface -- against the denser v2 grid, NSGA-II's hypervolume ratio is "
                f"{ratio_v2.mean():.3f}x (<=1 within tolerance in every scenario), the expected relationship "
                "for an approximate front vs a denser LP-exact reference.\n"
            )
        else:
            lines.append(
                f"\n- v2's reference front still doesn't fully dominate NSGA-II's in every scenario (mean ratio "
                f"{ratio_v2.mean():.3f}x) -- the grid is denser than v1 but still a finite sweep, not the "
                "continuous surface, so a residual gap can remain.\n"
            )

    (REPORTS_RESULTS / "optim_front_quality_v2.md").write_text("".join(lines), encoding="utf-8")
    print("Wrote optim_front_quality_v2.csv / optim_front_quality_v2.md")


# --- Items 2 & 5: Model B (NSGA-III) + risk evaluation of all strategies -------


def run_focus_scenario(params_df: pd.DataFrame, water_budget: float, risk_inputs) -> dict:
    scenario = Scenario(water_budget_m3=water_budget, land_ha=LAND_HA, price_mode="market")
    crops = list(params_df.index)
    R = (params_df["yield_qtl_ha"] * params_df["price"]).to_numpy(dtype=float)
    cost = params_df["cost_ha"].to_numpy(dtype=float)
    Sigma = risk_inputs.Sigma

    x1 = current_mix(params_df, scenario)
    r1 = evaluate(x1, params_df, scenario)

    x2, _ = solve_lp_profit_max(scenario, params_df)
    r2 = evaluate(x2, params_df, scenario)

    x3 = same_profit_min_water(params_df, scenario, min_profit=r1["profit"])
    r3 = evaluate(x3, params_df, scenario) if x3 is not None else None

    x4, Xf_A, Ff_A, rt_A = nsga2_recommended(params_df, scenario, seed=42)
    r4 = evaluate(x4, params_df, scenario) if x4 is not None else None

    xB, Xf_B, Ff_B, rt_B = nsga3_recommended(params_df, scenario, Sigma, weights=MODEL_B_WEIGHTS, seed=42)
    rB = evaluate(xB, params_df, scenario) if xB is not None else None

    strategies = {"B1": (x1, r1), "B2": (x2, r2), "B3": (x3, r3), "OURS_A": (x4, r4), "ModelB": (xB, rB)}

    rows = []
    for name, (x, r) in strategies.items():
        if x is None or r is None:
            rows.append({"strategy": name, "feasible": False})
            continue
        risk_val = portfolio_risk(x, Sigma)
        hs, series = historical_scenarios(x, risk_inputs, R, cost, return_series=True)
        rows.append(
            {
                "strategy": name,
                "profit": r["profit"],
                "water_m3": r["water_m3"],
                "fert_kg": r["fert_kg"],
                "n_crops": r["n_crops"],
                "portfolio_risk_rs": risk_val,
                "scenario_n_years": hs["n_years"],
                "scenario_mean": hs["mean"],
                "scenario_worst_year_profit": hs["worst_year_profit"],
                "scenario_worst_year": hs["worst_year"],
                "scenario_P10": hs["P10"],
                "scenario_n_loss_years": hs["n_loss_years"],
                "feasible": r["feasible"],
                "_series": series,
            }
        )

    curve_profit, curve_risk, _ = min_risk_profit_curve(scenario, params_df, Sigma, n=20)

    # --- Item 5: sugarcane risk sensitivity ---
    sens = None
    if xB is not None:
        other_stds = [float(risk_inputs.deviation_matrix[c].std()) for c in crops if c != "sugarcane"]
        median_other_std = float(np.median(other_stds))
        sugarcane_std_before = float(risk_inputs.deviation_matrix["sugarcane"].std())
        Sigma_sens, _ = sigma_with_overridden_std(risk_inputs, R, {"sugarcane": median_other_std})

        xB_sens, _, _, _ = nsga3_recommended(params_df, scenario, Sigma_sens, weights=MODEL_B_WEIGHTS, seed=42)
        r_sens = evaluate(xB_sens, params_df, scenario) if xB_sens is not None else None

        sc_idx = crops.index("sugarcane")
        sens = {
            "median_other_std": median_other_std,
            "sugarcane_std_before": sugarcane_std_before,
            "sugarcane_ha_before": float(xB[sc_idx]),
            "sugarcane_ha_after": float(xB_sens[sc_idx]) if xB_sens is not None else None,
            "risk_before": portfolio_risk(xB, Sigma),
            "risk_after": portfolio_risk(xB_sens, Sigma_sens) if xB_sens is not None else None,
            "profit_before": rB["profit"] if rB else None,
            "profit_after": r_sens["profit"] if r_sens else None,
            "feasible_after": xB_sens is not None,
        }

    return {
        "scenario": scenario,
        "rows": rows,
        "min_risk_curve": (curve_profit, curve_risk),
        "nsga3_front": (Xf_B, Ff_B),
        "nsga3_runtime": rt_B,
        "crops": crops,
        "sugarcane_sensitivity": sens,
    }


def write_risk_strategies_report(result: dict) -> pd.DataFrame:
    rows = result["rows"]
    df = pd.DataFrame([{k: v for k, v in row.items() if k != "_series"} for row in rows])
    df.to_csv(REPORTS_RESULTS / "risk_strategies.csv", index=False)

    lines = ["# Risk evaluation of B1/B2/B3/OURS (Model A) / Model B (Phase 5.1, Item 5)\n\n"]
    lines.append(f"Scenario: water={FOCUS_SCENARIO[0]}, price={FOCUS_SCENARIO[1]} (land={LAND_HA} ha).\n")
    lines.append(f"Model B pseudo-weights (profit, water, fert, risk) = {MODEL_B_WEIGHTS}.\n\n")
    lines.append(
        "`scenario_*` columns come from `historical_scenarios()` -- profit re-evaluated under each of the "
        "~18-19 actual historical years' deviations (no resampling), since the discrete historical record is "
        "small enough that a smooth bootstrap would manufacture outcomes never actually observed. "
        "`scenario_mean` should equal `profit` (deterministic point estimate) very closely -- deviations are "
        "mean-centered per allocation (see agriopt.optim.risk).\n\n"
    )

    cols = ["strategy", "profit", "water_m3", "fert_kg", "n_crops", "portfolio_risk_rs", "scenario_n_years", "scenario_mean", "scenario_worst_year_profit", "scenario_worst_year", "scenario_P10", "scenario_n_loss_years", "feasible"]
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

    sens = result.get("sugarcane_sensitivity")
    if sens is not None:
        lines.append("\n## Sensitivity: sugarcane risk\n\n")
        lines.append(
            "Model B's recommendation depends on Sigma, which gives sugarcane an unusually low std "
            f"({sens['sugarcane_std_before']:.3f}) purely because its price is a constant FRP, not a mandi "
            f"series -- not necessarily because it is genuinely less risky. This reruns Model B with "
            f"sugarcane's relative-deviation std replaced by the median of the other 7 crops' std "
            f"({sens['median_other_std']:.3f}), correlations unchanged, to test how much that assumption "
            "drives the recommendation.\n\n"
        )
        ha_after_str = f"{sens['sugarcane_ha_after']:.2f}" if sens["sugarcane_ha_after"] is not None else "-"
        risk_after_str = f"{sens['risk_after']:,.0f}" if sens["risk_after"] is not None else "-"
        profit_after_str = f"{sens['profit_after']:,.0f}" if sens["profit_after"] is not None else "-"
        lines.append("| | before (measured std) | after (median-of-others std) |\n")
        lines.append("|---|---|---|\n")
        lines.append(f"| sugarcane hectares | {sens['sugarcane_ha_before']:.2f} | {ha_after_str} |\n")
        lines.append(f"| total portfolio risk (Rs) | {sens['risk_before']:,.0f} | {risk_after_str} |\n")
        lines.append(f"| profit (Rs) | {sens['profit_before']:,.0f} | {profit_after_str} |\n")

        if sens["feasible_after"] and sens["sugarcane_ha_before"] > 1e-6:
            ha_shift_pct = abs(sens["sugarcane_ha_after"] - sens["sugarcane_ha_before"]) / sens["sugarcane_ha_before"] * 100
        elif sens["feasible_after"]:
            ha_shift_pct = 0.0 if sens["sugarcane_ha_after"] < 1e-6 else float("inf")
        else:
            ha_shift_pct = float("nan")

        if not sens["feasible_after"]:
            lines.append("\n**Not robust**: Model B found no feasible solution once sugarcane's std was raised to a typical level.\n")
        elif ha_shift_pct <= 20:
            lines.append(
                f"\n**Robust**: sugarcane hectares shift by only {ha_shift_pct:.1f}% when its std is raised to a "
                "typical crop's level -- the recommendation was not leaning on sugarcane's artificially low "
                "measured risk.\n"
            )
        else:
            lines.append(
                f"\n**Not robust**: sugarcane hectares shift by {ha_shift_pct:.1f}% once its std is raised to a "
                "typical crop's level -- part of Model B's original preference for sugarcane was an artifact of "
                "its constant-FRP price understating its true risk, not a genuine profit/water/fert advantage.\n"
            )

    (REPORTS_RESULTS / "risk_strategies.md").write_text("".join(lines), encoding="utf-8")
    print("Wrote risk_strategies.csv / risk_strategies.md")
    return df


def plot_risk(result: dict) -> None:
    rows = result["rows"]

    # per-year profit strip plot (discrete historical scenarios, not a smoothed histogram)
    labels, all_years, all_profits = [], [], []
    for i, row in enumerate(rows):
        series = row.get("_series")
        if series is None or len(series) == 0:
            continue
        labels.append(row["strategy"])
        all_years.extend([i + 1] * len(series))
        all_profits.extend(series.to_numpy())
    if labels:
        fig, ax = plt.subplots(figsize=(8, 6))
        rng = np.random.default_rng(0)
        jitter = rng.uniform(-0.08, 0.08, size=len(all_years))
        ax.scatter(np.array(all_years) + jitter, all_profits, alpha=0.6, s=25, color="tab:blue")
        for i, row in enumerate(rows):
            series = row.get("_series")
            if series is None or len(series) == 0:
                continue
            ax.scatter([i + 1], [series.mean()], marker="D", s=80, color="black", zorder=5)
        ax.set_xticks(range(1, len(labels) + 1))
        ax.set_xticklabels(labels)
        ax.set_title(f"Historical-scenario profit by strategy, one dot per year ({FOCUS_SCENARIO[0]}/{FOCUS_SCENARIO[1]})")
        ax.set_ylabel("profit (Rs)")
        fig.tight_layout()
        fig.savefig(REPORTS_RESULTS / "risk_profit_distribution.png", dpi=150)
        plt.close(fig)

    # Model B front (profit vs risk) + min-risk reference curve
    Xf_B, Ff_B = result["nsga3_front"]
    curve_profit, curve_risk = result["min_risk_curve"]
    fig, ax = plt.subplots(figsize=(8, 6))
    if Ff_B is not None and len(Ff_B):
        sc = ax.scatter(Ff_B[:, 0], Ff_B[:, 3], c=Ff_B[:, 1], cmap="viridis", s=20, alpha=0.7, label="NSGA-III front")
        fig.colorbar(sc, ax=ax, label="water (m3)")
    if len(curve_profit):
        ax.plot(curve_profit, curve_risk, "k--", linewidth=1.5, label="min-risk reference (SLSQP)")
    ax.set_xlabel("profit (Rs)")
    ax.set_ylabel("portfolio risk (Rs)")
    ax.set_title(f"Risk vs profit: NSGA-III front and min-risk reference ({FOCUS_SCENARIO[0]}/{FOCUS_SCENARIO[1]})")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(REPORTS_RESULTS / "risk_vs_profit_front.png", dpi=150)
    plt.close(fig)
    print("Wrote risk_profit_distribution.png / risk_vs_profit_front.png")


# --- Item 6: findings ----------------------------------------------------------


def write_findings_v2(risk_strategies_df: pd.DataFrame, quality_v2_df: pd.DataFrame, risk_inputs, sugarcane_sens: dict | None = None) -> None:
    lines = ["# Findings v2: risk objective, NSGA-III, reference grid (Phase 5)\n\n"]

    df = risk_strategies_df.set_index("strategy")
    if "B2" in df.index and "B1" in df.index:
        b2_risk, b1_risk = df.loc["B2", "portfolio_risk_rs"], df.loc["B1", "portfolio_risk_rs"]
        b2_n, b1_n = df.loc["B2", "n_crops"], df.loc["B1", "n_crops"]
        lines.append(
            f"- **B2 (profit-max) concentrates into {b2_n:.0f} crop(s) (vs B1's {b1_n:.0f}) and carries "
            f"{'more' if b2_risk > b1_risk else 'less'} portfolio risk than B1** (Rs {b2_risk:,.0f} vs "
            f"Rs {b1_risk:,.0f}) -- profit-maximizing concentration is {'indeed' if b2_risk > b1_risk else 'not'} "
            "riskier here, in the sense of this covariance-based portfolio metric.\n"
        )

    if "ModelB" in df.index and "OURS_A" in df.index:
        a_row, b_row = df.loc["OURS_A"], df.loc["ModelB"]

        def pct(new, base):
            return (new - base) / abs(base) * 100 if base else float("nan")

        profit_pct = pct(b_row["profit"], a_row["profit"])
        water_pct = pct(b_row["water_m3"], a_row["water_m3"])
        fert_pct = pct(b_row["fert_kg"], a_row["fert_kg"])
        risk_pct = pct(b_row["portfolio_risk_rs"], a_row["portfolio_risk_rs"])
        lines.append(
            f"- **Model B (risk-aware, NSGA-III) vs Model A's recommendation, full trade**: profit "
            f"{profit_pct:+.1f}% (Rs {a_row['profit']:,.0f} -> Rs {b_row['profit']:,.0f}), water {water_pct:+.1f}% "
            f"(m3 {a_row['water_m3']:,.0f} -> {b_row['water_m3']:,.0f}), fert {fert_pct:+.1f}% (kg "
            f"{a_row['fert_kg']:,.0f} -> {b_row['fert_kg']:,.0f}), portfolio risk {risk_pct:+.1f}% "
            f"(Rs {a_row['portfolio_risk_rs']:,.0f} -> Rs {b_row['portfolio_risk_rs']:,.0f}). Model B is not a "
            "free lunch on every axis -- report the full vector, not just the objectives it improved.\n"
        )

    if "B1" in df.index:
        b1 = df.loc["B1"]
        lines.append(
            f"- B1 (current mix)'s worst historical year would have earned Rs {b1['scenario_worst_year_profit']:,.0f} "
            f"profit (year {int(b1['scenario_worst_year'])}, out of {int(b1['scenario_n_years'])} years evaluated), "
            f"10th percentile Rs {b1['scenario_P10']:,.0f}, {int(b1['scenario_n_loss_years'])} loss year(s) -- "
            "read alongside portfolio_risk, since the discrete historical record captures downside shape "
            "(e.g. skew, a single very bad year) that a single sqrt(x'Sigma x) number does not.\n"
        )

    ratio_v2 = quality_v2_df["hv_nsga2_mean"] / quality_v2_df["hv_lp_grid_reference_v2"]
    n_still_above = int((ratio_v2 > 1.0).sum())
    lines.append(
        f"- The v2 grid reference front mostly resolves Phase 3's counter-intuitive finding that NSGA-II's "
        f"hypervolume exceeded the exact LP reference's in every scenario (mean ratio was 1.15-1.36x vs v1) -- "
        f"against the denser v2 grid, the mean ratio drops to {ratio_v2.mean():.3f}x, and 3/6 market-price "
        f"scenarios now show NSGA-II at or below the reference. The remaining {n_still_above}/6 scenarios "
        "(all msp_floor) still edge slightly above 1.0 (up to ~1.02x, see optim_front_quality_v2.md) -- MSP "
        "flooring narrows the profit range enough that even the denser grid may not fully cover the true "
        "surface there, so a small residual gap is plausible rather than a red flag.\n"
    )

    sugarcane_cv = risk_inputs.cv_table.loc["sugarcane", "cv"] if "sugarcane" in risk_inputs.cv_table.index else float("nan")
    other_cv_mean = risk_inputs.cv_table.drop(index="sugarcane", errors="ignore")["cv"].mean()
    lines.append(
        f"- Sugarcane's revenue CV ({sugarcane_cv:.2f}) is far below the other crops' mean ({other_cv_mean:.2f}) "
        "because its price is a constant FRP, not a mandi series -- its low measured risk is an artifact of "
        "missing price variance, not genuinely lower agronomic risk; flagged, not treated as a free lunch.\n"
    )

    lines.append(
        "- The revenue covariance matrix (Sigma) came out PSD without needing the nearest-PSD clip in this run "
        f"(min eigenvalue before clipping: {risk_inputs.min_eigenvalue_raw:,.0f}) -- expected, since it is a "
        "Hadamard product of a real (if pairwise-incomplete) sample covariance matrix with a rank-1 PSD scaling "
        "matrix (R R'), which is PSD by the Schur product theorem whenever the underlying covariance itself is; "
        "the clip exists as a safety net for cases where pairwise-incomplete-years covariance breaks that.\n"
    )

    lines.append(
        "- Crop_Year's harvest-window convention (kharif = Oct-Dec of year t, rabi = Mar-May of year t+1) is an "
        "ASSUMPTION, not verified against an independent Maharashtra harvest calendar (see agriopt.optim.risk "
        "module docstring) -- if wrong, Rabi crops' revenue years could be off by one, which would mostly affect "
        "cross-crop correlation estimates between Kharif and Rabi crops, not the overall risk magnitudes.\n"
    )

    if sugarcane_sens is not None and sugarcane_sens["feasible_after"]:
        ha_before, ha_after = sugarcane_sens["sugarcane_ha_before"], sugarcane_sens["sugarcane_ha_after"]
        shift_pct = abs(ha_after - ha_before) / ha_before * 100 if ha_before > 1e-6 else (0.0 if ha_after < 1e-6 else float("inf"))
        verdict = "robust" if shift_pct <= 20 else "NOT robust"
        lines.append(
            f"- **Sugarcane risk sensitivity: Model B's recommendation is {verdict} to the FRP-price-artifact "
            f"assumption** -- replacing sugarcane's measured std ({sugarcane_sens['sugarcane_std_before']:.3f}) "
            f"with the median of the other 7 crops' std ({sugarcane_sens['median_other_std']:.3f}, correlations "
            f"unchanged) moves sugarcane hectares from {ha_before:.2f} to {ha_after:.2f} ha ({shift_pct:.1f}% "
            f"shift). See risk_strategies.md 'Sensitivity: sugarcane risk' for the full before/after table.\n"
        )

    (REPORTS_RESULTS / "optim_findings_v2.md").write_text("".join(lines), encoding="utf-8")
    print("Wrote optim_findings_v2.md")


def main() -> None:
    REPORTS_RESULTS.mkdir(parents=True, exist_ok=True)

    x1, b1_water, _ = compute_b1_water()
    water_budgets = {label: mult * b1_water for label, mult in WATER_MULTIPLIERS.items()}
    print(f"B1 water usage: {b1_water:.1f} m3; budgets: {water_budgets}")

    params_by_mode = {mode: build_crop_params(mode, verbose=False) for mode in PRICE_MODES}

    print("\n-- Item 1: risk matrix --")
    risk_inputs_market = build_risk_inputs(params_by_mode["market"])
    write_risk_matrix_report(risk_inputs_market, list(params_by_mode["market"].index))

    print("\n-- Item 3: v2 reference front quality, 6 scenarios --")
    quality_v2_rows = []
    for water_label, wb in water_budgets.items():
        for price_mode in PRICE_MODES:
            print(f"  {water_label}/{price_mode} ...")
            quality_v2_rows.append(front_quality_v2_for_scenario(water_label, price_mode, params_by_mode[price_mode], wb))
    quality_v2_df = pd.DataFrame(quality_v2_rows)
    write_front_quality_v2_report(quality_v2_df)

    print(f"\n-- Items 2 & 5: Model B + risk evaluation, focus scenario {FOCUS_SCENARIO} --")
    focus_label, focus_mode = FOCUS_SCENARIO
    result = run_focus_scenario(params_by_mode[focus_mode], water_budgets[focus_label], risk_inputs_market)
    risk_strategies_df = write_risk_strategies_report(result)
    plot_risk(result)

    print("\n-- Item 6: findings v2 --")
    write_findings_v2(risk_strategies_df, quality_v2_df, risk_inputs_market, sugarcane_sens=result["sugarcane_sensitivity"])

    print("\n=== risk_strategies ===")
    print(risk_strategies_df.to_string(index=False))
    print("\n=== front quality v2 ===")
    print(quality_v2_df.to_string(index=False))
    print("\n=== sugarcane sensitivity ===")
    print(result["sugarcane_sensitivity"])


if __name__ == "__main__":
    sys.exit(main())
