"""Sidebar inputs -> (Scenario, weights, run_clicked)."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import streamlit as st

from agriopt.optim.problem import Scenario
from app.pipeline import current_mix_water, weights_from_priority


@dataclass
class SidebarInputs:
    scenario: Scenario
    weights: tuple[float, float, float]
    run_clicked: bool


def render_sidebar(params_df_for_water_ref: pd.DataFrame) -> SidebarInputs:
    """`params_df_for_water_ref` is used only to compute the current-mix
    water reference shown next to the water-budget slider -- water use is
    price-mode independent (see agriopt.optim.baselines.current_mix), so
    either price mode's params work here."""
    with st.sidebar:
        st.subheader("Scenario inputs")

        land_ha = st.slider("Land (ha)", min_value=1, max_value=50, value=10, step=1)

        default_water_m3 = current_mix_water(params_df_for_water_ref, float(land_ha))
        st.caption(f"Current-mix water use at this land size: {default_water_m3:,.0f} m³")
        water_budget_m3 = st.slider(
            "Water budget (m³)",
            min_value=0.0,
            max_value=max(default_water_m3 * 2.0, 1.0),
            value=float(default_water_m3),
            step=max(default_water_m3 / 100, 1.0),
        )

        food_share_min = st.slider("Min food-crop share", min_value=0.0, max_value=0.6, value=0.3, step=0.05)
        max_share = st.slider("Max share per crop", min_value=0.2, max_value=1.0, value=0.5, step=0.05)

        price_mode_label = st.selectbox("Price mode", ["Market (last observed)", "MSP floor"])
        price_mode = "market" if price_mode_label.startswith("Market") else "msp_floor"

        priority = st.slider(
            "Priority: Profit ↔ Sustainability",
            min_value=0.0,
            max_value=1.0,
            value=0.5,
            step=0.05,
            help="Left = weight profit more heavily. Right = weight water/fertilizer more heavily.",
        )
        weights = weights_from_priority(priority)
        st.caption(f"pseudo-weights (profit, water, fert) = ({weights[0]:.2f}, {weights[1]:.2f}, {weights[2]:.2f})")

        run_clicked = st.button("Run", type="primary", width="stretch")

    scenario = Scenario(
        water_budget_m3=water_budget_m3,
        land_ha=float(land_ha),
        food_share_min=food_share_min,
        max_share=max_share,
        price_mode=price_mode,
    )
    return SidebarInputs(scenario=scenario, weights=weights, run_clicked=run_clicked)
