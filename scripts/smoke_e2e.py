"""Headless end-to-end smoke test: cache -> params -> NSGA-II -> recommend ->
baselines, for the default scenario and one deliberately infeasible scenario.
No Streamlit involved. Exit code 0 on success, 1 on failure.
"""
from __future__ import annotations

import os

# Demo-hardening Item 1: see app/streamlit_app.py's matching block for why --
# must be set before numpy/pymoo/sklearn are imported (directly or via
# agriopt below).
for _env_var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ.setdefault(_env_var, "1")

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from agriopt.optim.problem import Scenario
from app import data as appdata
from app.pipeline import current_mix_water, run_pipeline, summary_sentence, weights_from_priority


def main() -> int:
    if not appdata.cache_exists():
        print(f"FAIL: missing cache at {appdata.CACHE_PATH} -- run {appdata.BUILD_CACHE_CMD} first")
        return 1

    raw = appdata.load_cache_raw()
    params_df = appdata.params_df_from_records(raw["price_modes"]["market"])
    weights = weights_from_priority(0.5)

    # --- default scenario -----------------------------------------------------
    land_ha = 10.0
    water_default = current_mix_water(params_df, land_ha)
    scenario = Scenario(water_budget_m3=water_default, land_ha=land_ha, food_share_min=0.3, max_share=0.5, price_mode="market")

    print(f"Default scenario: land={land_ha} water_budget={water_default:.1f} m3")
    result = run_pipeline(params_df, scenario, weights)
    if not result.feasible:
        print(f"FAIL: default scenario reported infeasible: {result.message}")
        return 1

    r1, r4 = result.evals["B1"], result.evals["OURS"]
    print(f"  B1 profit={r1['profit']:.0f} water={r1['water_m3']:.0f} feasible={r1['feasible']}")
    print(f"  OURS profit={r4['profit']:.0f} water={r4['water_m3']:.0f} feasible={r4['feasible']}")
    print(f"  NSGA-II runtime={result.nsga_runtime:.2f}s, front size={len(result.F_front)}")
    print(f"  Summary: {summary_sentence(r1, r4)}")

    # --- infeasible scenario ---------------------------------------------------
    infeasible_scenario = Scenario(
        water_budget_m3=1.0,  # far too little water for any allocation
        land_ha=land_ha,
        food_share_min=0.3,
        max_share=0.5,
        price_mode="market",
    )
    print("\nInfeasible scenario: water_budget=1.0 m3")
    infeasible_result = run_pipeline(params_df, infeasible_scenario, weights)
    if infeasible_result.feasible:
        print("FAIL: expected the near-zero water budget scenario to be infeasible, but it was feasible")
        return 1
    print(f"  OK: reported infeasible with message: {infeasible_result.message}")

    print("\nsmoke_e2e: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
