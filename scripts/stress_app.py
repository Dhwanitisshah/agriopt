"""Demo-hardening Item 2: stress test.

1) Starts `streamlit run app/streamlit_app.py --server.headless true
   --server.port 8599` as a real subprocess, waits for it to come up, and
   confirms it stays alive/healthy for the duration of the stress run --
   this exercises the actual server process (thread env vars, real
   reruns-from-client-requests) that a live demo would run under.

2) Separately, drives 40 pipeline runs (20 normal mode, 20 risk-aware/
   NSGA-III mode) from a WORKER THREAD (mimicking Streamlit's own
   script-run thread model, which is where the destabilization documented
   in tests/test_app_smoke.py and scripts/check_app_tabs.py's docstring was
   observed), cycling all 4 presets and both sugarcane-risk settings. Each
   run gets a 30s cap enforced via a single-slot ThreadPoolExecutor
   (future.result(timeout=...)) -- a genuinely hung call can't be killed,
   but is detected, logged, and does not block the remaining runs (a fresh
   executor is used for the next call).

   AppTest is deliberately NOT used here for the repeated-run loop: running
   an AppTest session and then making further direct pymoo/NSGA calls in
   the SAME process was found to deadlock reliably (see
   scripts/check_app_tabs.py) -- calling app.pipeline.run_pipeline directly
   from a worker thread exercises the same NSGA-II/NSGA-III code path
   without that specific interaction.

Reports: runs completed, max/mean runtime, any hangs or crashes. Kills the
server at the end regardless of outcome.
"""
from __future__ import annotations

import os

# Demo-hardening Item 1: see app/streamlit_app.py's matching block.
for _env_var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ.setdefault(_env_var, "1")

import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PORT = 8599
SERVER_START_TIMEOUT_S = 30
PER_RUN_TIMEOUT_S = 30
N_RUNS_PER_MODE = 20


def _wait_for_server(port: int, timeout_s: int) -> bool:
    deadline = time.time() + timeout_s
    url = f"http://localhost:{port}/_stcore/health"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            pass
        time.sleep(0.5)
    return False


def _server_is_alive(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://localhost:{port}/_stcore/health", timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def _one_pipeline_run(params_df, scenario, weights, risk_aware, weights4, Sigma, current_mix_share=None):
    from app.pipeline import run_pipeline

    t0 = time.perf_counter()
    result = run_pipeline(
        params_df,
        scenario,
        weights,
        risk_aware=risk_aware,
        weights4=weights4,
        Sigma=Sigma,
        current_mix_share=current_mix_share,
    )
    return result, time.perf_counter() - t0


def run_stress_loop() -> dict:
    from agriopt.optim.problem import Scenario
    from app import data as appdata
    from app.pipeline import current_mix_water, weights4_from_priority_and_risk_aversion, weights_from_priority
    from app.presets import DEFAULT_FOOD_SHARE_MIN, DEFAULT_LAND_HA, DEFAULT_MAX_SHARE, DEFAULT_PRICE_MODE, DEFAULT_PRIORITY, DEFAULT_RISK_AVERSION, PRESETS

    raw = appdata.load_cache_raw()
    params_df = appdata.params_df_from_records(raw["price_modes"]["market"])
    current_mix_share = raw.get("current_mix_shares")  # Phase 10: never reads yield_clean.parquet
    weights = weights_from_priority(DEFAULT_PRIORITY)
    weights4 = weights4_from_priority_and_risk_aversion(DEFAULT_PRIORITY, DEFAULT_RISK_AVERSION)
    preset_names = list(PRESETS.keys())
    sugarcane_modes = ["conservative", "frp_based"]

    plan = []
    for i in range(N_RUNS_PER_MODE):
        preset = PRESETS[preset_names[i % len(preset_names)]]
        land_ha = float(preset["land_ha"]) if preset["land_ha"] is not None else DEFAULT_LAND_HA
        water_budget = preset["water_mult"] * current_mix_water(params_df, land_ha, current_mix_share)
        scenario = Scenario(water_budget_m3=water_budget, land_ha=land_ha, food_share_min=DEFAULT_FOOD_SHARE_MIN, max_share=DEFAULT_MAX_SHARE, price_mode=DEFAULT_PRICE_MODE)
        plan.append({"mode": "normal", "scenario": scenario, "risk_aware": False, "weights4": None, "Sigma": None})

    for i in range(N_RUNS_PER_MODE):
        preset = PRESETS[preset_names[i % len(preset_names)]]
        land_ha = float(preset["land_ha"]) if preset["land_ha"] is not None else DEFAULT_LAND_HA
        water_budget = preset["water_mult"] * current_mix_water(params_df, land_ha, current_mix_share)
        scenario = Scenario(water_budget_m3=water_budget, land_ha=land_ha, food_share_min=DEFAULT_FOOD_SHARE_MIN, max_share=DEFAULT_MAX_SHARE, price_mode=DEFAULT_PRICE_MODE)
        sugarcane_mode = sugarcane_modes[i % len(sugarcane_modes)]
        risk_inputs = appdata.risk_inputs_from_cache(raw, sugarcane_mode=sugarcane_mode)
        plan.append({"mode": f"risk_aware/{sugarcane_mode}", "scenario": scenario, "risk_aware": True, "weights4": weights4, "Sigma": risk_inputs.Sigma})

    runtimes = []
    n_completed = 0
    n_hung = 0
    n_crashed = 0
    n_infeasible = 0

    for i, run in enumerate(plan):
        executor = ThreadPoolExecutor(max_workers=1)  # fresh executor per call -- abandon a hung worker rather than reuse it
        future = executor.submit(
            _one_pipeline_run, params_df, run["scenario"], weights, run["risk_aware"], run["weights4"], run["Sigma"], current_mix_share
        )
        try:
            result, runtime_s = future.result(timeout=PER_RUN_TIMEOUT_S)
            runtimes.append(runtime_s)
            n_completed += 1
            if not result.feasible:
                n_infeasible += 1
            print(f"  [{i + 1:2d}/{len(plan)}] mode={run['mode']:<18s} land={run['scenario'].land_ha:5.1f} runtime={runtime_s:.2f}s feasible={result.feasible}")
        except FutureTimeoutError:
            n_hung += 1
            print(f"  [{i + 1:2d}/{len(plan)}] mode={run['mode']:<18s} land={run['scenario'].land_ha:5.1f} HUNG (>{PER_RUN_TIMEOUT_S}s, abandoned)")
        except Exception as exc:
            n_crashed += 1
            print(f"  [{i + 1:2d}/{len(plan)}] mode={run['mode']:<18s} land={run['scenario'].land_ha:5.1f} CRASHED: {exc!r}")
        finally:
            executor.shutdown(wait=False)

    return {
        "n_planned": len(plan),
        "n_completed": n_completed,
        "n_hung": n_hung,
        "n_crashed": n_crashed,
        "n_infeasible": n_infeasible,
        "runtimes": runtimes,
    }


def main() -> int:
    print(f"Starting Streamlit server on port {PORT} ...")
    server = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", str(REPO_ROOT / "app" / "streamlit_app.py"), "--server.headless", "true", "--server.port", str(PORT)],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        if not _wait_for_server(PORT, SERVER_START_TIMEOUT_S):
            print(f"FAIL: server did not become healthy within {SERVER_START_TIMEOUT_S}s")
            return 1
        print("Server healthy. Running 40-iteration pipeline stress loop (worker thread, mimicking Streamlit's script thread) ...")

        stats = run_stress_loop()

        server_alive_after = _server_is_alive(PORT)
        print(f"\nServer still healthy after stress loop: {server_alive_after}")

    finally:
        print("Stopping server ...")
        server.terminate()
        try:
            server.wait(timeout=15)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=15)

    runtimes = stats["runtimes"]
    print("\n=== Stress test results ===")
    print(f"Planned runs:    {stats['n_planned']}")
    print(f"Completed:       {stats['n_completed']}")
    print(f"Hung (>{PER_RUN_TIMEOUT_S}s):    {stats['n_hung']}")
    print(f"Crashed:         {stats['n_crashed']}")
    print(f"Infeasible:      {stats['n_infeasible']}")
    if runtimes:
        print(f"Runtime (completed runs): max={max(runtimes):.2f}s mean={sum(runtimes) / len(runtimes):.2f}s min={min(runtimes):.2f}s")
    print(f"Server alive at end of loop: {server_alive_after}")

    ok = stats["n_hung"] == 0 and stats["n_crashed"] == 0 and server_alive_after
    print("\nstress_app: PASS" if ok else "\nstress_app: FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
