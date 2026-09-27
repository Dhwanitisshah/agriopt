# Hotfix (Streamlit Community Cloud): this is a src-layout package
# (pyproject.toml: packages under src/). Locally, `pip install -e .` puts
# src/agriopt on sys.path, so app/streamlit_app.py never needed to. On
# Streamlit Cloud, only requirements-app.txt is installed (no `pip install
# -e .` -- see the fresh-clone deploy-readiness check), so without this,
# `from agriopt...` raises ModuleNotFoundError. Must run before ANY project
# import, including the thread-env block below (which only touches `os`,
# but keeping this literally first avoids relying on that).
import sys, pathlib
_ROOT = pathlib.Path(__file__).resolve().parents[1]
for p in (_ROOT / "src", _ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import os

# Demo-hardening Item 1: cap native (BLAS/OpenMP/numba) thread pools to 1
# BEFORE numpy/pymoo/sklearn are imported (directly or transitively, e.g.
# via pandas/agriopt below). Left at their defaults, these libraries each
# spin up their own OS-level thread pool; under Streamlit's own script-run
# thread on Windows, repeated NSGA-II/NSGA-III runs across reruns were
# observed to destabilize those thread pools (intermittent native crashes/
# hangs deep in numpy/pymoo, unrelated to this app's own logic -- see
# scripts/stress_app.py and tests/test_app_smoke.py for how this was
# root-caused). setdefault() so an operator's own env still wins.
for _env_var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ.setdefault(_env_var, "1")

REPO_ROOT = _ROOT

import pandas as pd
import streamlit as st

from app import data as appdata
from app.components.about import render_about_tab
from app.components.backtest_tab import render_backtest_tab
from app.components.comparison import render_comparison_tab
from app.components.evidence import render_evidence_tab
from app.components.recommendation import render_recommendation_tab
from app.components.regional_tab import render_regional_tab
from app.components.risk_tab import render_risk_tab
from app.components.sidebar import render_sidebar
from app.components.tradeoffs import render_tradeoffs_tab
from app.pipeline import apply_price_shocks, run_pipeline
from app.presets import DEFAULT_RAINFALL_SCENARIO, DEFAULT_REGION, DEFAULT_WATER_BASIS

st.set_page_config(page_title="AgriOpt", page_icon=":material/agriculture:", layout="wide")


@st.cache_resource(show_spinner=False)
def _load_cache_raw() -> dict:
    return appdata.load_cache_raw()


@st.cache_data(show_spinner=False)
def _params_df(region: str, water_basis: str, rainfall_scenario: str, price_mode: str) -> pd.DataFrame:
    raw = _load_cache_raw()
    return appdata.params_df_for(raw, region, water_basis, rainfall_scenario, price_mode)


@st.cache_resource(show_spinner=False)
def _risk_inputs(sugarcane_mode: str):
    raw = _load_cache_raw()
    return appdata.risk_inputs_from_cache(raw, sugarcane_mode=sugarcane_mode)


st.title("AgriOpt — Multi-objective crop planning (Maharashtra)")

if not appdata.cache_exists():
    st.error(
        f"Missing precomputed crop params cache at `{appdata.CACHE_PATH}`. Build it first:\n\n"
        f"```\n{appdata.BUILD_CACHE_CMD}\n```"
    )
    st.stop()

cache_raw = _load_cache_raw()
# Reference df for the sidebar's water-slider default / preset buttons / FRP
# default -- always the app's own default region+water_basis+rainfall
# scenario (Maharashtra, net_irrigation, normal), regardless of what the
# region/water-basis selectors are currently set to. This is a cosmetic
# reference figure only (it just seeds slider defaults); the actual
# optimization below always uses params_df built from the REAL selected
# scenario fields. Avoided a sidebar re-order (region/water-basis selectors
# render after the water slider) for a same-run circular dependency.
params_market = _params_df(DEFAULT_REGION, DEFAULT_WATER_BASIS, DEFAULT_RAINFALL_SCENARIO, "market")
# Phase 10 deploy-readiness: B1 (current_mix)'s historical area share,
# precomputed offline into the cache (scripts/40_build_cache.py) -- the app
# never reads data/processed/yield_clean.parquet itself (gitignored, not
# present in a fresh clone). Threaded through render_sidebar/run_pipeline.
current_mix_share = cache_raw.get("current_mix_shares")

sidebar_inputs = render_sidebar(params_market, current_mix_share)
scenario = sidebar_inputs.scenario
weights = sidebar_inputs.weights
params_df = _params_df(scenario.region, scenario.water_basis, scenario.rainfall_scenario, scenario.price_mode)
params_df = apply_price_shocks(params_df, sidebar_inputs.price_multipliers, sidebar_inputs.sugarcane_frp_override)

risk_inputs = _risk_inputs(sidebar_inputs.sugarcane_risk_mode)
R = appdata.revenue_vector_from_cache(cache_raw)

if "scenario_result" not in st.session_state:
    st.session_state["scenario_result"] = None

# Demo-hardening Item 4: if the current inputs exactly match a farmer-profile
# preset at default settings, show scripts/40_build_cache.py's precomputed
# result instantly instead of re-running NSGA-II/NSGA-III -- checked on
# every rerun (not just Run clicks), so it applies right after a preset
# button fills the sidebar, before the user even presses Run.
sugarcane_default_frp = float(params_market.loc["sugarcane", "price"]) if "sugarcane" in params_market.index else 0.0
matched_preset = appdata.match_preset(
    scenario,
    sidebar_inputs.priority,
    sidebar_inputs.risk_aware,
    sidebar_inputs.risk_aversion,
    sidebar_inputs.sugarcane_risk_mode,
    sidebar_inputs.price_multipliers,
    sidebar_inputs.sugarcane_frp_override,
    sugarcane_default_frp,
    params_market,
    cache_raw,
)


if matched_preset is not None:
    mode_key = "risk_aware" if sidebar_inputs.risk_aware else "normal"
    cached_result = cache_raw["preset_results"][matched_preset][mode_key]
    st.session_state["scenario_result"] = appdata.scenario_result_from_cache(
        cached_result,
        scenario,
        weights,
        sidebar_inputs.weights4,
        sidebar_inputs.risk_aware,
        risk_inputs.Sigma if sidebar_inputs.risk_aware else None,
    )
elif sidebar_inputs.run_clicked or st.session_state["scenario_result"] is None:
    with st.spinner("Running optimizer..."):
        st.session_state["scenario_result"] = run_pipeline(
            params_df,
            scenario,
            weights,
            risk_aware=sidebar_inputs.risk_aware,
            weights4=sidebar_inputs.weights4,
            Sigma=risk_inputs.Sigma if sidebar_inputs.risk_aware else None,
            current_mix_share=current_mix_share,
        )

result = st.session_state["scenario_result"]

if result.feasible and result.risk_aware_failed:
    st.warning("Risk-aware optimisation failed; showing the standard 3-objective plan.")

if result.feasible and result.from_cache:
    st.caption(":material/bolt: cached result for this farmer profile -- shown instantly, not re-optimized.")

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(
    [
        "Recommendation",
        "Trade-offs",
        "Strategy comparison",
        "Risk",
        "Backtest (2016-2019)",
        "Regional view",
        "Model inputs & evidence",
        "About & limitations",
    ]
)

with tab1:
    render_recommendation_tab(result, params_df, cache_raw.get("conformal"))
with tab2:
    render_tradeoffs_tab(result, params_df)
with tab3:
    render_comparison_tab(result)
with tab4:
    render_risk_tab(result, params_df, risk_inputs, R, sugarcane_mode=sidebar_inputs.sugarcane_risk_mode)
with tab5:
    render_backtest_tab(cache_raw.get("backtest"))
with tab6:
    render_regional_tab(cache_raw.get("region_comparison"))
with tab7:
    render_evidence_tab(params_df, cache_raw["yield_model_metadata"], cache_raw["price_model_metadata"])
with tab8:
    render_about_tab()
