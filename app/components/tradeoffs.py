"""Tab 2: Trade-offs -- NSGA-II Pareto scatter (profit vs water, color=fert),
current mix / profit-max / min-water / recommendation markers, LP reference
front overlay."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from agriopt.optim.solvers import exact_front_lp
from app.pipeline import ScenarioResult

LP_FRONT_N = 30
MARKERS = {
    "B1 current mix": ("square", "red"),
    "B2 profit-max": ("triangle-up", "orange"),
    "B3 same-profit-min-water": ("diamond", "purple"),
    "Recommended": ("star", "blue"),
}


def _hover_text(x: np.ndarray, crops: list[str]) -> str:
    parts = [f"{c}: {v:.2f} ha" for c, v in zip(crops, x) if v > 1e-6]
    return "<br>".join(parts) if parts else "(no allocation)"


def render_tradeoffs_tab(result: ScenarioResult, params_df: pd.DataFrame) -> None:
    if not result.feasible:
        st.warning(result.message)
        return

    crops = list(params_df.index)
    F = result.F_front
    X = result.X_front

    hover = [_hover_text(x, crops) for x in X]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=F[:, 0],
            y=F[:, 1],
            mode="markers",
            marker=dict(
                size=8,
                color=F[:, 2],
                colorscale="Viridis",
                colorbar=dict(title="fert (kg)"),
                showscale=True,
            ),
            text=hover,
            hovertemplate="profit=%{x:,.0f}<br>water=%{y:,.0f}<br>%{text}<extra></extra>",
            name="NSGA-II front",
        )
    )

    with st.spinner("Computing LP reference front..."):
        _, F_lp = exact_front_lp(result.scenario, n=LP_FRONT_N, params_df=params_df)
    if len(F_lp):
        order = np.argsort(F_lp[:, 1])
        fig.add_trace(
            go.Scatter(
                x=F_lp[order, 0],
                y=F_lp[order, 1],
                mode="lines",
                line=dict(color="black", width=1.5, dash="dot"),
                name="LP ε-constraint reference (profit→water→fert)",
            )
        )

    labels_x = {
        "B1 current mix": "B1",
        "B2 profit-max": "B2",
        "B3 same-profit-min-water": "B3",
        "Recommended": "OURS",
    }
    for label, (symbol, color) in MARKERS.items():
        r = result.evals[labels_x[label]]
        if r is None:
            continue
        x_alloc = result.x[labels_x[label]]
        fig.add_trace(
            go.Scatter(
                x=[r["profit"]],
                y=[r["water_m3"]],
                mode="markers",
                marker=dict(symbol=symbol, size=16, color=color, line=dict(color="black", width=1)),
                text=[_hover_text(x_alloc, crops)],
                hovertemplate=f"{label}<br>" + "profit=%{x:,.0f}<br>water=%{y:,.0f}<br>%{text}<extra></extra>",
                name=label,
            )
        )

    fig.update_layout(
        xaxis_title="profit (₹)",
        yaxis_title="water (m³)",
        title="Pareto front: profit vs water (color = fertilizer)",
        height=550,
    )
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "The LP reference front is an exact lexicographic profit→water→fert slice through objective "
        "space, not the full trade-off surface -- see docs/formulation.md and the About tab."
    )
