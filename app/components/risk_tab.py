"""Tab: Risk -- bootstrap profit distribution (B1/OURS/B2), P(loss)/P5/CVaR5
cards, plain explanation. Reuses agriopt.optim.risk (cached Sigma/deviation
matrix, no raw recompute) -- see app/data.py risk_inputs_from_cache.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from agriopt.optim.risk import RiskInputs, bootstrap_profit_resampled, historical_scenarios, portfolio_risk
from app.pipeline import ScenarioResult

STRATEGY_LABELS = {"B1": "Current mix", "OURS": "Recommendation", "B2": "Profit-max"}
N_BOOTSTRAP = 3000


def render_risk_tab(result: ScenarioResult, params_df: pd.DataFrame, risk_inputs: RiskInputs, R: np.ndarray, sugarcane_mode: str = "conservative") -> None:
    if not result.feasible:
        st.warning(result.message)
        return

    cost = params_df.loc[risk_inputs.crops, "cost_ha"].to_numpy(dtype=float)

    mode_label = "conservative (typical-crop std)" if sugarcane_mode == "conservative" else "FRP-based (measured)"
    st.caption(
        f"Sugarcane risk assumption: **{mode_label}**. "
        "Distributions below resample from the ~19 historical years on record -- illustrative, not a smooth "
        "continuous distribution (see agriopt.optim.risk.bootstrap_profit_resampled)."
    )

    fig = go.Figure()
    boot_results = {}
    for key, label in STRATEGY_LABELS.items():
        x = result.x.get(key)
        if x is None:
            continue
        x_reordered = np.array([x[list(params_df.index).index(c)] for c in risk_inputs.crops])
        boot, samples = bootstrap_profit_resampled(x_reordered, risk_inputs, R, cost, n=N_BOOTSTRAP, seed=42, return_samples=True)
        boot_results[key] = boot
        fig.add_trace(go.Violin(y=samples, name=label, box_visible=True, meanline_visible=True, points=False))

    fig.update_layout(title="Resampled historical profit distribution", yaxis_title="profit (Rs)", height=450)
    st.plotly_chart(fig, width="stretch")

    rec = boot_results.get("OURS")
    if rec is not None and not np.isnan(rec["mean"]):
        with st.container(horizontal=True):
            st.metric("P(loss)", f"{rec['P_loss']:.0%}", border=True)
            st.metric("Worst-5% profit (P5)", f"₹{rec['P5']:,.0f}", border=True)
            st.metric("CVaR5 (avg of worst 5%)", f"₹{rec['CVaR5']:,.0f}", border=True)

        st.info(
            f"In a resample of historical years, the recommendation has about a {rec['P_loss']:.0%} chance of a "
            f"loss; in the worst 5% of scenarios, expect roughly ₹{rec['CVaR5']:,.0f} profit."
        )

    x_ours = result.x.get("OURS")
    if x_ours is not None:
        x_reordered = np.array([x_ours[list(params_df.index).index(c)] for c in risk_inputs.crops])
        hs = historical_scenarios(x_reordered, risk_inputs, R, cost)
        risk_val = portfolio_risk(x_reordered, risk_inputs.Sigma)
        st.caption(
            f"Discrete historical record ({hs['n_years']} years): worst year would have earned "
            f"₹{hs['worst_year_profit']:,.0f} (year {hs['worst_year']}), {hs['n_loss_years']} loss year(s). "
            f"Portfolio risk (sqrt of variance): ₹{risk_val:,.0f}."
        )
