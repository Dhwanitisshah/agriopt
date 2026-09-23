import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import streamlit as st

from app import data as appdata
from app.components.about import render_about_tab
from app.components.comparison import render_comparison_tab
from app.components.evidence import render_evidence_tab
from app.components.recommendation import render_recommendation_tab
from app.components.sidebar import render_sidebar
from app.components.tradeoffs import render_tradeoffs_tab
from app.pipeline import run_pipeline

st.set_page_config(page_title="AgriOpt", page_icon=":material/agriculture:", layout="wide")


@st.cache_resource(show_spinner=False)
def _load_cache_raw() -> dict:
    return appdata.load_cache_raw()


@st.cache_data(show_spinner=False)
def _params_df(price_mode: str) -> "pd.DataFrame":
    raw = _load_cache_raw()
    return appdata.params_df_from_records(raw["price_modes"][price_mode])


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

if "scenario_result" not in st.session_state:
    st.session_state["scenario_result"] = None

if sidebar_inputs.run_clicked or st.session_state["scenario_result"] is None:
    with st.spinner("Running optimizer..."):
        st.session_state["scenario_result"] = run_pipeline(params_df, scenario, weights)

result = st.session_state["scenario_result"]

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Recommendation", "Trade-offs", "Strategy comparison", "Model inputs & evidence", "About & limitations"]
)

with tab1:
    render_recommendation_tab(result, params_df)
with tab2:
    render_tradeoffs_tab(result, params_df)
with tab3:
    render_comparison_tab(result)
with tab4:
    render_evidence_tab(params_df, cache_raw["yield_model_metadata"], cache_raw["price_model_metadata"])
with tab5:
    render_about_tab()
