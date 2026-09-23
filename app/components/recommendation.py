"""Tab 1: Recommendation -- KPI cards, allocation table + bar, plain-language summary."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from app.pipeline import ScenarioResult, pct_delta, summary_sentence

SEASON_LABELS = {"kharif": "Kharif", "rabi": "Rabi"}


def _crop_season_label(seasons: set) -> str:
    return " + ".join(SEASON_LABELS[s] for s in sorted(seasons))


def render_recommendation_tab(result: ScenarioResult, params_df: pd.DataFrame) -> None:
    if not result.feasible:
        st.warning(result.message)
        return

    r1, r4 = result.evals["B1"], result.evals["OURS"]

    with st.container(horizontal=True):
        st.metric("Profit (₹)", f"{r4['profit']:,.0f}", f"{pct_delta(r4['profit'], r1['profit']):+.1f}%", border=True)
        st.metric("Water (m³)", f"{r4['water_m3']:,.0f}", f"{pct_delta(r4['water_m3'], r1['water_m3']):+.1f}%", border=True, delta_color="inverse")
        st.metric("Fertilizer (kg)", f"{r4['fert_kg']:,.0f}", f"{pct_delta(r4['fert_kg'], r1['fert_kg']):+.1f}%", border=True, delta_color="inverse")
        st.metric("Food-crop share", f"{r4['food_share']:.0%}", f"{(r4['food_share'] - r1['food_share']) * 100:+.1f}pp", border=True)
        st.metric("Profit risk (₹)", f"{r4['profit_risk']:,.0f}", f"{pct_delta(r4['profit_risk'], r1['profit_risk']):+.1f}%", border=True, delta_color="inverse")

    st.info(summary_sentence(r1, r4))

    if not r4["feasible"]:
        st.caption(":material/warning: recommendation is at the edge of numerical tolerance on a constraint.")

    st.subheader("Recommended allocation")
    crops = list(params_df.index)
    x4 = result.x["OURS"]
    alloc_df = pd.DataFrame(
        {
            "crop": crops,
            "hectares": x4,
            "season": [_crop_season_label(params_df.loc[c, "seasons_occupied"]) for c in crops],
        }
    )
    alloc_df = alloc_df[alloc_df["hectares"] > 1e-6].sort_values("hectares", ascending=True)

    col1, col2 = st.columns([2, 1])
    with col1:
        fig = px.bar(
            alloc_df,
            x="hectares",
            y="crop",
            color="season",
            orientation="h",
            title="Hectares by crop (recommended)",
        )
        fig.update_layout(yaxis_title="", xaxis_title="hectares", legend_title="season")
        st.plotly_chart(fig, width="stretch")
    with col2:
        st.dataframe(
            alloc_df.rename(columns={"hectares": "ha"})[["crop", "ha", "season"]].sort_values("ha", ascending=False),
            hide_index=True,
            width="stretch",
        )
