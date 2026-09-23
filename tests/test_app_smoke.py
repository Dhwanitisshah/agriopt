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
    AppTest's own script-runner threads across a long test session)."""
    from agriopt.optim.problem import Scenario
    from app import data as appdata
    from app.components.sidebar import PRESETS
    from app.pipeline import current_mix_water, run_pipeline, weights_from_priority

    raw = appdata.load_cache_raw()
    params_df = appdata.params_df_from_records(raw["price_modes"]["market"])
    weights = weights_from_priority(0.5)
    current_land = 10.0

    for name, preset in PRESETS.items():
        land_ha = preset["land_ha"] if preset["land_ha"] is not None else current_land
        water_budget = preset["water_mult"] * current_mix_water(params_df, float(land_ha))
        scenario = Scenario(water_budget_m3=water_budget, land_ha=float(land_ha))
        result = run_pipeline(params_df, scenario, weights, pop=16, gens=15, seed=0)
        assert result.feasible or isinstance(result.message, str), f"preset {name!r} raised or returned an unusable result"


def test_price_shock_monotonic_and_downloads_nonempty():
    """Combines two checks on one pair of pipeline runs (rather than
    recomputing separately) to limit the total number of NSGA-II
    invocations in this test session: (1) halving sugarcane's FRP should
    never increase its recommended hectares; (2) the resulting plan's
    download artifacts (CSV/Markdown) are non-empty and well-formed."""
    from agriopt.optim.problem import Scenario
    from app import data as appdata
    from app.exports import build_plan_csv, build_summary_markdown
    from app.pipeline import apply_price_shocks, current_mix_water, run_pipeline, weights_from_priority

    raw = appdata.load_cache_raw()
    params_df = appdata.params_df_from_records(raw["price_modes"]["market"])
    crops = list(params_df.index)
    sc_idx = crops.index("sugarcane")

    water = current_mix_water(params_df, 10.0) * 1.5
    scenario = Scenario(water_budget_m3=water, land_ha=10.0)
    weights = weights_from_priority(0.5)

    result_default = run_pipeline(params_df, scenario, weights, pop=20, gens=30, seed=0)
    assert result_default.feasible

    default_frp = float(params_df.loc["sugarcane", "price"])
    shocked_df = apply_price_shocks(params_df, sugarcane_frp_override=default_frp * 0.5)
    result_shocked = run_pipeline(shocked_df, scenario, weights, pop=20, gens=30, seed=0)
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
    the risk-aware recommendation may change or stay equal, either is fine."""
    from agriopt.optim.problem import Scenario
    from agriopt.optim.solvers import nsga3_recommended
    from app import data as appdata
    from app.pipeline import current_mix_water, weights4_from_priority_and_risk_aversion

    raw = appdata.load_cache_raw()
    params_df = appdata.params_df_from_records(raw["price_modes"]["market"])
    crops = list(params_df.index)
    sc_idx = crops.index("sugarcane")

    water = current_mix_water(params_df, 10.0)
    scenario = Scenario(water_budget_m3=water, land_ha=10.0)
    weights4 = weights4_from_priority_and_risk_aversion(0.5, 0.5)

    hectares = {}
    for mode in ["conservative", "frp_based"]:
        risk_inputs = appdata.risk_inputs_from_cache(raw, sugarcane_mode=mode)
        x, _, _, _ = nsga3_recommended(params_df, scenario, risk_inputs.Sigma, weights=weights4, n_partitions=4, gens=40, seed=42)
        assert x is not None, f"NSGA-III returned no solution for sugarcane_mode={mode}"
        hectares[mode] = float(x[sc_idx])

    assert hectares["conservative"] >= 0 and hectares["frp_based"] >= 0
