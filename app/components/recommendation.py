"""Tab 1: Recommendation -- KPI cards, allocation table + bar, plain-language
summary, "why these crops?" explanations, binding constraints, downloads."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from app.explain import binding_constraints, crop_reasons
from app.exports import build_plan_csv, build_summary_markdown
from app.pipeline import ScenarioResult, pct_delta, summary_sentence

SEASON_LABELS = {"kharif": "Kharif", "rabi": "Rabi"}


def _crop_season_label(seasons: set) -> str:
    return " + ".join(SEASON_LABELS[s] for s in sorted(seasons))


def render_recommendation_tab(result: ScenarioResult, params_df: pd.DataFrame, conformal: dict | None = None) -> None:
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

    if conformal is not None:
        q_per_crop = conformal.get("q_per_crop", {})
        q_overall = conformal.get("q_overall")
        level_pct = (1.0 - conformal.get("alpha", 0.1)) * 100
        rows = []
        for crop in crops:
            if crop not in alloc_df["crop"].values:
                continue
            q = q_per_crop.get(crop, q_overall)
            if q is None:
                continue
            y = float(params_df.loc[crop, "yield_qtl_ha"])
            # Same log1p +/- q +/- expm1 construction as
            # agriopt.models.yield_model.predict_yield_interval, applied to
            # the already-known point yield estimate in params_df instead of
            # a live model call (the cache stores only the calibrated
            # quantile q, not the model itself -- see scripts/40_build_cache.py).
            lo = float(np.expm1(np.log1p(y) - q))
            hi = float(np.expm1(np.log1p(y) + q))
            rows.append({"crop": crop, "yield (qtl/ha)": round(y, 2), "90% interval": f"{lo:.1f} - {hi:.1f}"})
        if rows:
            with st.expander(f"Yield uncertainty ({level_pct:.0f}% conformal interval)", expanded=False):
                st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
                st.caption(
                    "Split-conformal intervals (Phase 9), calibrated on 2013-2015 residuals in log1p-yield space "
                    "-- per-crop where calibrated, else the overall quantile. See the Model inputs & evidence tab "
                    "(E1.5) for coverage and per-crop caveats."
                )

    with st.expander("Why these crops?", expanded=False):
        Sigma = result.Sigma if result.risk_aware else None
        reasons = crop_reasons(x4, params_df, result.scenario, Sigma=Sigma)
        for crop in crops:
            if crop in reasons:
                st.markdown(f"**{crop}** — {reasons[crop]}")
        if Sigma is None:
            st.caption("Enable risk-aware mode to see each crop's share of total portfolio risk.")

        st.markdown("**Binding constraints**")
        binding_df = pd.DataFrame(binding_constraints(x4, params_df, result.scenario))
        binding_df["used"] = binding_df["used"].round(1)
        binding_df["limit"] = binding_df["limit"].round(1)
        st.dataframe(binding_df, hide_index=True, width="stretch")

    st.subheader("Download")
    dl_col1, dl_col2 = st.columns(2)
    with dl_col1:
        st.download_button(
            "Download plan (CSV)",
            data=build_plan_csv(x4, params_df),
            file_name="agriopt_plan.csv",
            mime="text/csv",
            width="stretch",
        )
    with dl_col2:
        st.download_button(
            "Download summary (Markdown)",
            data=build_summary_markdown(result, params_df),
            file_name="agriopt_summary.md",
            mime="text/markdown",
            width="stretch",
        )
