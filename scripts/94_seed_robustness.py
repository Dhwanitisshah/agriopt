"""Phase 9 / E3.4: NSGA-II / NSGA-III seed robustness.

10 seeds (0-9) for each algorithm on the DEFAULT scenario (water_budget_m3 =
B1's "current" water usage, i.e. WATER_MULTIPLIERS["current"]=1.0x, matching
scripts/30_run_optimizer.py's canonical default; land_ha=10.0,
price_mode="market" -- both Scenario defaults). Reports:
  - Hypervolume (HV) mean +/- std + 95% CI (normal approximation, given only
    n=10 -- see Findings for the small-n caveat, same spirit as Phase 7's
    n=4/5 backtest caveat).
  - The pseudo-weights RECOMMENDED allocation's per-crop std of hectares
    across the 10 seeds' fronts -- how sensitive the FINAL recommendation is
    to the optimizer's random seed, not just the front's HV.

Phase 8 fixed NSGA-II/III's own reproducibility bug (RF n_jobs=-1
nondeterminism in build_crop_params, not pymoo's seeding) -- the seed-to-seed
variation measured here is NSGA's own stochastic search variation, not that
old bug (confirmed: params_df is built ONCE and reused across all 10 seeds
per algorithm here, so the objective coefficients are identical for every
seed within an algorithm; only the GA's own random search differs).
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd
from pymoo.indicators.hv import HV
from scipy import stats as sstats

from agriopt.config import CROPS, REPORTS_RESULTS
from agriopt.optim.params import build_crop_params
from agriopt.optim.problem import Scenario
from agriopt.optim.risk import build_risk_inputs
from agriopt.optim.solvers import recommend, solve_nsga2, solve_nsga3

SEEDS = list(range(10))
LAND_HA = 10.0
WATER_MULTIPLIER_CURRENT = 1.0  # matches scripts/30_run_optimizer.py WATER_MULTIPLIERS["current"]


def compute_default_scenario(params_df: pd.DataFrame) -> Scenario:
    """B1 water usage at price_mode='market', x1 water demand -- same
    definition as scripts/30_run_optimizer.py's compute_b1_water(), at the
    'current' (1.0x) multiplier, i.e. this repo's canonical default
    scenario."""
    from agriopt.optim.baselines import current_mix

    dummy = Scenario(water_budget_m3=1e15, land_ha=LAND_HA)
    x1 = current_mix(params_df, dummy)
    water = float(x1 @ params_df["water_m3_ha"].to_numpy())
    return Scenario(water_budget_m3=water * WATER_MULTIPLIER_CURRENT, land_ha=LAND_HA, price_mode="market")


def normal_95ci(vals: np.ndarray) -> tuple[float, float]:
    n = len(vals)
    mean, std = float(np.mean(vals)), float(np.std(vals, ddof=1))
    se = std / np.sqrt(n)
    half = sstats.t.ppf(0.975, df=n - 1) * se
    return mean - half, mean + half


def hv_for_fronts(fronts: list[np.ndarray]) -> np.ndarray:
    """Normalize all fronts jointly (min-max per objective across the union
    of all seeds' fronts), same convention as scripts/30_run_optimizer.py's
    front_quality_for_scenario, then compute HV per seed with ref_point at
    [1.1]*n_obj in normalized minimize-form space."""
    def to_min_form(F):
        Fm = F.copy()
        Fm[:, 0] = -Fm[:, 0]
        return Fm

    non_empty = [f for f in fronts if len(f) > 0]
    if not non_empty:
        return np.full(len(fronts), np.nan)
    union = np.vstack([to_min_form(f) for f in non_empty])
    lo, hi = union.min(axis=0), union.max(axis=0)
    span = np.where(hi > lo, hi - lo, 1.0)
    n_obj = union.shape[1]
    ref_point = np.full(n_obj, 1.1)
    hv = HV(ref_point=ref_point)
    out = []
    for f in fronts:
        if len(f) == 0:
            out.append(np.nan)
            continue
        norm = (to_min_form(f) - lo) / span
        out.append(float(hv(norm)))
    return np.array(out)


def per_crop_allocation_std(X_list: list[np.ndarray], crops: list[str]) -> pd.Series:
    X_arr = np.array(X_list)  # (n_seeds, n_crops)
    return pd.Series(X_arr.std(axis=0), index=crops)


def main() -> None:
    REPORTS_RESULTS.mkdir(parents=True, exist_ok=True)

    print("Building crop params (market price, total_need water basis -- reused across all seeds) ...")
    params_df = build_crop_params("market", verbose=False)
    crops = list(params_df.index)
    scenario = compute_default_scenario(params_df)
    print(f"Default scenario: water_budget_m3={scenario.water_budget_m3:.1f}, land_ha={scenario.land_ha}")

    # --- NSGA-II: 10 seeds ---------------------------------------------------
    print("\nNSGA-II: 10 seeds ...")
    nsga2_fronts, nsga2_X_rec = [], []
    for seed in SEEDS:
        X, F, _ = solve_nsga2(scenario, params_df, seed=seed)
        nsga2_fronts.append(F)
        if len(F) > 0:
            idx = recommend(F)
            nsga2_X_rec.append(X[idx])
        print(f"  seed={seed}: front size={len(F)}")

    hv_nsga2 = hv_for_fronts(nsga2_fronts)
    ci2 = normal_95ci(hv_nsga2)
    alloc_std_nsga2 = per_crop_allocation_std(nsga2_X_rec, crops)

    # --- NSGA-III: 10 seeds --------------------------------------------------
    print("\nBuilding risk inputs for NSGA-III (Sigma) ...")
    risk_inputs = build_risk_inputs(params_df, crops)
    Sigma = risk_inputs.Sigma

    print("NSGA-III: 10 seeds ...")
    nsga3_fronts, nsga3_X_rec = [], []
    for seed in SEEDS:
        X, F, _ = solve_nsga3(scenario, params_df, Sigma, seed=seed)
        nsga3_fronts.append(F)
        if len(F) > 0:
            idx = recommend(F, weights=(0.4, 0.2, 0.1, 0.3))
            nsga3_X_rec.append(X[idx])
        print(f"  seed={seed}: front size={len(F)}")

    hv_nsga3 = hv_for_fronts(nsga3_fronts)
    ci3 = normal_95ci(hv_nsga3)
    alloc_std_nsga3 = per_crop_allocation_std(nsga3_X_rec, crops)

    # --- write CSVs -----------------------------------------------------------
    hv_df = pd.DataFrame(
        {
            "algorithm": ["NSGA-II", "NSGA-III"],
            "hv_mean": [float(np.nanmean(hv_nsga2)), float(np.nanmean(hv_nsga3))],
            "hv_std": [float(np.nanstd(hv_nsga2, ddof=1)), float(np.nanstd(hv_nsga3, ddof=1))],
            "hv_ci95_lo": [ci2[0], ci3[0]],
            "hv_ci95_hi": [ci2[1], ci3[1]],
            "n_seeds": [len(SEEDS), len(SEEDS)],
        }
    )
    hv_df.to_csv(REPORTS_RESULTS / "optim_seed_robustness_hv.csv", index=False)

    alloc_df = pd.DataFrame({"crop": crops, "nsga2_alloc_std_ha": alloc_std_nsga2.values, "nsga3_alloc_std_ha": alloc_std_nsga3.values})
    alloc_df.to_csv(REPORTS_RESULTS / "optim_seed_robustness_allocation.csv", index=False)

    # --- write-up ---------------------------------------------------------
    lines = ["# NSGA-II / NSGA-III seed robustness (Phase 9 / E3.4)\n\n"]
    lines.append(
        f"10 seeds (0-9), default scenario (water_budget_m3={scenario.water_budget_m3:.1f} m3 -- B1's 'current' "
        "water usage at price_mode='market', matching scripts/30_run_optimizer.py's canonical default; "
        f"land_ha={scenario.land_ha}). params_df is built ONCE and reused across every seed within an algorithm, "
        "so all seed-to-seed variation below is NSGA's own stochastic-search variation (Phase 8 already fixed "
        "the RF-nondeterminism bug that used to contaminate this).\n\n"
    )
    lines.append("## Hypervolume (normalized, joint ref_point=[1.1]*n_obj)\n\n")
    lines.append("| algorithm | HV mean | HV std | 95% CI (normal approx, n=10) |\n|---|---|---|---|\n")
    for _, r in hv_df.iterrows():
        lines.append(f"| {r['algorithm']} | {r['hv_mean']:.4f} | {r['hv_std']:.4f} | [{r['hv_ci95_lo']:.4f}, {r['hv_ci95_hi']:.4f}] |\n")
    lines.append(
        "\n**Small-n caveat**: n=10 seed-runs is a small sample for a CI (same spirit as the Phase 7 backtest's "
        "n=4/5-year caveat) -- the normal-approximation CI here is a rough guide to seed sensitivity, not a "
        "precise interval.\n"
    )

    lines.append("\n## Recommended allocation: per-crop std of hectares across the 10 seeds\n\n")
    lines.append("| crop | NSGA-II alloc std (ha) | NSGA-III alloc std (ha) |\n|---|---|---|\n")
    for _, r in alloc_df.iterrows():
        lines.append(f"| {r['crop']} | {r['nsga2_alloc_std_ha']:.3f} | {r['nsga3_alloc_std_ha']:.3f} |\n")

    most_sensitive_2 = alloc_df.loc[alloc_df["nsga2_alloc_std_ha"].idxmax(), "crop"]
    most_sensitive_3 = alloc_df.loc[alloc_df["nsga3_alloc_std_ha"].idxmax(), "crop"]
    lines.append(
        f"\n- Most seed-sensitive crop in the final recommendation: **{most_sensitive_2}** (NSGA-II), "
        f"**{most_sensitive_3}** (NSGA-III) -- i.e. which crop's recommended hectares swing most just from "
        "changing the optimizer's random seed, holding the scenario and params fixed.\n"
    )
    lines.append(
        f"- Mean per-crop allocation std: NSGA-II={alloc_df['nsga2_alloc_std_ha'].mean():.3f} ha, "
        f"NSGA-III={alloc_df['nsga3_alloc_std_ha'].mean():.3f} ha (out of land_ha={scenario.land_ha}) -- "
        f"{'a non-trivial share of total land' if alloc_df['nsga2_alloc_std_ha'].mean() > 0.05 * scenario.land_ha else 'a small share of total land'}, "
        "worth disclosing to a user who reruns the optimizer and gets a slightly different plan each time.\n"
    )
    (REPORTS_RESULTS / "optim_seed_robustness.md").write_text("".join(lines), encoding="utf-8")
    print("Wrote optim_seed_robustness_hv.csv / optim_seed_robustness_allocation.csv / optim_seed_robustness.md")


if __name__ == "__main__":
    sys.exit(main())
