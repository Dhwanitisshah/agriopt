import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pandas as pd
import streamlit as st

from app import data as appdata
from app.components.about import render_about_tab
from app.components.comparison import render_comparison_tab
from app.components.evidence import render_evidence_tab
from app.components.recommendation import render_recommendation_tab
from app.components.risk_tab import render_risk_tab
from app.components.sidebar import render_sidebar
from app.components.tradeoffs import render_tradeoffs_tab
from app.pipeline import apply_price_shocks, run_pipeline

st.set_page_config(page_title="AgriOpt", page_icon=":material/agriculture:", layout="wide")


@st.cache_resource(show_spinner=False)
def _load_cache_raw() -> dict:
    return appdata.load_cache_raw()


@st.cache_data(show_spinner=False)
def _params_df(price_mode: str) -> pd.DataFrame:
    raw = _load_cache_raw()
    return appdata.params_df_from_records(raw["price_modes"][price_mode])


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
params_market = _params_df("market")

sidebar_inputs = render_sidebar(params_market)
scenario = sidebar_inputs.scenario
weights = sidebar_inputs.weights
params_df = _params_df(scenario.price_mode)
params_df = apply_price_shocks(params_df, sidebar_inputs.price_multipliers, sidebar_inputs.sugarcane_frp_override)

risk_inputs = _risk_inputs(sidebar_inputs.sugarcane_risk_mode)
R = appdata.revenue_vector_from_cache(cache_raw)

if "scenario_result" not in st.session_state:
    st.session_state["scenario_result"] = None

if sidebar_inputs.run_clicked or st.session_state["scenario_result"] is None:
    with st.spinner("Running optimizer..."):
        st.session_state["scenario_result"] = run_pipeline(
            params_df,
            scenario,
            weights,
            risk_aware=sidebar_inputs.risk_aware,
            weights4=sidebar_inputs.weights4,
            Sigma=risk_inputs.Sigma if sidebar_inputs.risk_aware else None,
        )

result = st.session_state["scenario_result"]

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["Recommendation", "Trade-offs", "Strategy comparison", "Risk", "Model inputs & evidence", "About & limitations"]
)

with tab1:
    render_recommendation_tab(result, params_df)
with tab2:
    render_tradeoffs_tab(result, params_df)
with tab3:
    render_comparison_tab(result)
with tab4:
    render_risk_tab(result, params_df, risk_inputs, R, sugarcane_mode=sidebar_inputs.sugarcane_risk_mode)
with tab5:
    render_evidence_tab(params_df, cache_raw["yield_model_metadata"], cache_raw["price_model_metadata"])
with tab6:
    render_about_tab()
