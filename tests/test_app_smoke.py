import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def test_app_module_imports():
    import app.streamlit_app  # noqa: F401


def test_smoke_e2e_main_returns_0():
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "smoke_e2e.py")],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert "smoke_e2e: PASS" in result.stdout


def test_infeasible_scenario_handled_without_exception():
    from agriopt.optim.problem import Scenario
    from app import data as appdata
    from app.pipeline import run_pipeline, weights_from_priority

    raw = appdata.load_cache_raw()
    params_df = appdata.params_df_from_records(raw["price_modes"]["market"])

    scenario = Scenario(water_budget_m3=1.0, land_ha=10.0, food_share_min=0.3, max_share=0.5, price_mode="market")
    result = run_pipeline(params_df, scenario, weights_from_priority(0.5))

    assert result.feasible is False
    assert isinstance(result.message, str) and len(result.message) > 0


# --- Phase 6 -----------------------------------------------------------------


def test_apptest_all_tabs_render_normal_and_risk_aware_mode():
    """Runs scripts/check_app_tabs.py (an AppTest session, both modes) as a
    SEPARATE PROCESS rather than importing streamlit.testing.v1.AppTest
    in-process -- running an AppTest session and then making further direct
    pymoo/NSGA calls in the SAME process was observed to deadlock reliably
    on this environment (a genuine thread-join hang, reproduced repeatedly,
    not flaky timing) -- see scripts/check_app_tabs.py's docstring."""
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "check_app_tabs.py")],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=180,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert "check_app_tabs: PASS" in result.stdout


def test_presets_run_without_exception():
    """Exercises each farmer-profile preset's underlying logic (land_ha +
    water multiplier -> Scenario -> run_pipeline) directly rather than via a
    full Streamlit AppTest rerun per preset -- equivalent coverage of
    app.components.sidebar.PRESETS, without stacking up N extra full-script
    NSGA-II reruns in one pytest process (observed to destabilize pymoo/
    numpy's native threading on this Windows environment when combined with
    AppTest's own script-runner threads across a long test session).

    Threads `current_mix_share` from the cache into current_mix_water/
    run_pipeline, exactly as app/streamlit_app.py and
    app/components/sidebar.py do -- omitting it (as this test did before the
    CI/cloud fix) falls back to reading the gitignored yield_clean.parquet
    directly, which doesn't exist on a fresh CI checkout or a Streamlit
    Community Cloud deploy."""
    from agriopt.optim.problem import Scenario
    from app import data as appdata
    from app.components.sidebar import PRESETS
    from app.pipeline import current_mix_water, run_pipeline, weights_from_priority

    raw = appdata.load_cache_raw()
    params_df = appdata.params_df_from_records(raw["price_modes"]["market"])
    current_mix_share = raw.get("current_mix_shares")
    weights = weights_from_priority(0.5)
    current_land = 10.0

    for name, preset in PRESETS.items():
        land_ha = preset["land_ha"] if preset["land_ha"] is not None else current_land
        water_budget = preset["water_mult"] * current_mix_water(params_df, float(land_ha), current_mix_share)
        scenario = Scenario(water_budget_m3=water_budget, land_ha=float(land_ha))
        result = run_pipeline(params_df, scenario, weights, pop=16, gens=15, seed=0, current_mix_share=current_mix_share)
        assert result.feasible or isinstance(result.message, str), f"preset {name!r} raised or returned an unusable result"


def test_price_shock_monotonic_and_downloads_nonempty():
    """Combines two checks on one pair of pipeline runs (rather than
    recomputing separately) to limit the total number of NSGA-II
    invocations in this test session: (1) halving sugarcane's FRP should
    never increase its recommended hectares; (2) the resulting plan's
    download artifacts (CSV/Markdown) are non-empty and well-formed.

    Threads `current_mix_share` from the cache -- see
    test_presets_run_without_exception's docstring for why."""
    from agriopt.optim.problem import Scenario
    from app import data as appdata
    from app.exports import build_plan_csv, build_summary_markdown
    from app.pipeline import apply_price_shocks, current_mix_water, run_pipeline, weights_from_priority

    raw = appdata.load_cache_raw()
    params_df = appdata.params_df_from_records(raw["price_modes"]["market"])
    current_mix_share = raw.get("current_mix_shares")
    crops = list(params_df.index)
    sc_idx = crops.index("sugarcane")

    water = current_mix_water(params_df, 10.0, current_mix_share) * 1.5
    scenario = Scenario(water_budget_m3=water, land_ha=10.0)
    weights = weights_from_priority(0.5)

    result_default = run_pipeline(params_df, scenario, weights, pop=20, gens=30, seed=0, current_mix_share=current_mix_share)
    assert result_default.feasible

    default_frp = float(params_df.loc["sugarcane", "price"])
    shocked_df = apply_price_shocks(params_df, sugarcane_frp_override=default_frp * 0.5)
    result_shocked = run_pipeline(shocked_df, scenario, weights, pop=20, gens=30, seed=0, current_mix_share=current_mix_share)
    assert result_shocked.feasible

    ha_default = result_default.x["OURS"][sc_idx]
    ha_shocked = result_shocked.x["OURS"][sc_idx]
    assert ha_shocked <= ha_default + 1e-6, f"sugarcane hectares rose after halving its price: {ha_default} -> {ha_shocked}"

    csv_text = build_plan_csv(result_default.x["OURS"], params_df)
    md_text = build_summary_markdown(result_default, params_df)
    assert len(csv_text) > 0 and "crop" in csv_text
    assert len(md_text) > 0 and "Recommended allocation" in md_text


def test_sugarcane_risk_toggle_never_errors():
    """Toggling the sugarcane risk assumption (Phase 6 Item 10) between
    'conservative' and 'frp_based' must never raise -- sugarcane hectares in
    the risk-aware recommendation may change or stay equal, either is fine.

    Threads `current_mix_share` from the cache -- see
    test_presets_run_without_exception's docstring for why."""
    from agriopt.optim.problem import Scenario
    from agriopt.optim.solvers import nsga3_recommended
    from app import data as appdata
    from app.pipeline import current_mix_water, weights4_from_priority_and_risk_aversion

    raw = appdata.load_cache_raw()
    params_df = appdata.params_df_from_records(raw["price_modes"]["market"])
    current_mix_share = raw.get("current_mix_shares")
    crops = list(params_df.index)
    sc_idx = crops.index("sugarcane")

    water = current_mix_water(params_df, 10.0, current_mix_share)
    scenario = Scenario(water_budget_m3=water, land_ha=10.0)
    weights4 = weights4_from_priority_and_risk_aversion(0.5, 0.5)

    hectares = {}
    for mode in ["conservative", "frp_based"]:
        risk_inputs = appdata.risk_inputs_from_cache(raw, sugarcane_mode=mode)
        x, _, _, _ = nsga3_recommended(params_df, scenario, risk_inputs.Sigma, weights=weights4, n_partitions=4, gens=40, seed=42)
        assert x is not None, f"NSGA-III returned no solution for sugarcane_mode={mode}"
        hectares[mode] = float(x[sc_idx])

    assert hectares["conservative"] >= 0 and hectares["frp_based"] >= 0


# --- CI/cloud hotfix: guard against ANY app code path reading raw data ------
#
# The bug this guards against: current_mix_water()/run_pipeline() accept an
# optional current_mix_share (falls back to reading the gitignored
# data/processed/yield_clean.parquet when omitted -- correct for pre-Phase-10
# scripts/tests run with the full dataset present, but a crash waiting to
# happen for any app-style caller that forgets to thread the cache's
# precomputed value). app/streamlit_app.py, sidebar.py, and data.py already
# thread it correctly everywhere (verified by inspection); the 3 tests above
# did not, until this fix. This test doesn't trust that inspection alone --
# it PHYSICALLY hides data/processed/*.parquet and models/ (renaming them
# aside and restoring in `finally`, even on failure) and then drives the same
# app.pipeline.run_pipeline entry point streamlit_app.py itself calls, across
# a sweep of region x water_basis x rainfall_scenario x risk_aware x
# sugarcane_mode. This does NOT literally cross every preset with every
# region/water-basis combo (5 presets x 5 regions x 2 water_basis x 2 risk x
# 2 sugarcane_mode = 200 NSGA runs is not a sane CI budget) -- instead it (a)
# runs all 5 presets (each fixing its own region/water_basis/
# rainfall_scenario) under both risk_aware settings and both sugarcane modes,
# and (b) separately sweeps every region x water_basis(x rainfall_scenario)
# combination at one fixed default scenario, so every axis named in the task
# is exercised at least once and every preset is exercised fully. Documented
# scoping decision, not a silent gap.
_RAW_DATA_PATHS_TO_HIDE = [
    "data/processed/yield_clean.parquet",
    "data/processed/prices_monthly.parquet",
    "models",
]


def _hide_raw_data():
    """Renames each path in _RAW_DATA_PATHS_TO_HIDE to '<path>.hidden_for_test'
    if present, returning the list of (original, hidden) pairs actually
    moved (so cleanup only restores what this call itself hid)."""
    import os

    moved = []
    for rel in _RAW_DATA_PATHS_TO_HIDE:
        src = REPO_ROOT / rel
        if src.exists():
            dst = REPO_ROOT / (rel + ".hidden_for_test")
            os.rename(src, dst)
            moved.append((src, dst))
    return moved


def _restore_raw_data(moved):
    import os

    for src, dst in moved:
        if dst.exists():
            os.rename(dst, src)


def test_app_pipeline_never_reads_raw_data():
    """See module-level comment above this test for the bug + scoping this
    guards against. Runs entirely without data/processed/*.parquet or
    models/ present on disk -- any accidental raw-data read anywhere in the
    app.pipeline/app.data/app.components call chain raises FileNotFoundError
    here, exactly as it did in CI before this fix."""
    from agriopt.optim.problem import Scenario
    from app import data as appdata
    from app.components.sidebar import PRESETS
    from app.pipeline import current_mix_water, run_pipeline, weights4_from_priority_and_risk_aversion, weights_from_priority

    moved = _hide_raw_data()
    try:
        raw = appdata.load_cache_raw()
        current_mix_share = raw.get("current_mix_shares")
        assert current_mix_share, "cache is missing current_mix_shares -- nothing to guard, test itself is broken"

        weights = weights_from_priority(0.5)
        weights4 = weights4_from_priority_and_risk_aversion(0.5, 0.5)

        # (a) every preset, both risk-aware settings, both sugarcane modes
        # when risk-aware -- each preset already fixes its own region/
        # water_basis/rainfall_scenario (app/presets.py).
        for name, preset in PRESETS.items():
            region = preset.get("region", "maharashtra")
            water_basis = preset.get("water_basis", "net_irrigation")
            rainfall_scenario = preset.get("rainfall_scenario", "normal")
            params_df = appdata.params_df_for(raw, region, water_basis, rainfall_scenario, "market")
            land_ha = float(preset["land_ha"]) if preset["land_ha"] is not None else 10.0
            water = preset["water_mult"] * current_mix_water(params_df, land_ha, current_mix_share)
            scenario = Scenario(
                water_budget_m3=water, land_ha=land_ha, region=region, water_basis=water_basis, rainfall_scenario=rainfall_scenario
            )

            for risk_aware in (False, True):
                sugarcane_modes = ["conservative", "frp_based"] if risk_aware else [None]
                for sugarcane_mode in sugarcane_modes:
                    Sigma = appdata.risk_inputs_from_cache(raw, sugarcane_mode=sugarcane_mode).Sigma if risk_aware else None
                    result = run_pipeline(
                        params_df,
                        scenario,
                        weights,
                        pop=12,
                        gens=10,
                        seed=0,
                        risk_aware=risk_aware,
                        weights4=weights4,
                        Sigma=Sigma,
                        current_mix_share=current_mix_share,
                    )
                    assert result.feasible or isinstance(result.message, str), (
                        f"preset {name!r} risk_aware={risk_aware} sugarcane_mode={sugarcane_mode} "
                        "raised or returned an unusable result"
                    )

        # (b) every region x water_basis(x rainfall_scenario) combo, one
        # fixed default scenario, risk_aware=False -- covers combos no
        # preset touches (konkan/madhya_maharashtra/vidarbha, marathwada
        # under "normal", every region under "total_need").
        for region in raw["params"].keys():
            for water_basis, rainfall_scenarios in (("net_irrigation", ["normal", "dry"]), ("total_need", ["normal"])):
                for rainfall_scenario in rainfall_scenarios:
                    params_df = appdata.params_df_for(raw, region, water_basis, rainfall_scenario, "market")
                    water = current_mix_water(params_df, 10.0, current_mix_share) * 1.2
                    scenario = Scenario(
                        water_budget_m3=water, land_ha=10.0, region=region, water_basis=water_basis, rainfall_scenario=rainfall_scenario
                    )
                    result = run_pipeline(params_df, scenario, weights, pop=12, gens=10, seed=0, current_mix_share=current_mix_share)
                    assert result.feasible or isinstance(result.message, str), (
                        f"region={region!r} water_basis={water_basis!r} rainfall_scenario={rainfall_scenario!r} "
                        "raised or returned an unusable result"
                    )
    finally:
        _restore_raw_data(moved)
