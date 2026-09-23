"""Sidebar inputs -> (Scenario, weights, run_clicked) -- Phase 6 adds farmer
profile presets, risk-aware mode (+ risk-aversion, sugarcane risk toggle),
and a what-if price-shock expander."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd
import streamlit as st

from agriopt.config import CROPS
from agriopt.optim.problem import Scenario
from app.pipeline import current_mix_water, weights4_from_priority_and_risk_aversion, weights_from_priority

PRESETS = {
    "Small rainfed (2 ha, tight water)": {"land_ha": 2, "water_mult": 0.7},
    "Medium mixed (5 ha, current water)": {"land_ha": 5, "water_mult": 1.0},
    "Large irrigated (15 ha, relaxed water)": {"land_ha": 15, "water_mult": 1.3},
    "Drought year (current land, water x0.6)": {"land_ha": None, "water_mult": 0.6},
}

DEFAULTS = {
    "land_ha": 10,
    "food_share_min": 0.3,
    "max_share": 0.5,
    "price_mode_label": "Market (last observed)",
    "priority": 0.5,
    "risk_aware_mode": False,
    "risk_aversion": 0.5,
    "sugarcane_risk_mode_label": "Typical crop risk (conservative)",
}


@dataclass
class SidebarInputs:
    scenario: Scenario
    weights: tuple[float, float, float]
    weights4: tuple[float, float, float, float] | None
    risk_aware: bool
    sugarcane_risk_mode: str
    price_multipliers: dict = field(default_factory=dict)
    sugarcane_frp_override: float | None = None
    run_clicked: bool = False


def _apply_preset(name: str, params_df: pd.DataFrame) -> None:
    preset = PRESETS[name]
    land_ha = preset["land_ha"] if preset["land_ha"] is not None else st.session_state.get("land_ha", DEFAULTS["land_ha"])
    st.session_state["land_ha"] = land_ha
    st.session_state["water_budget_m3"] = preset["water_mult"] * current_mix_water(params_df, float(land_ha))


def render_sidebar(params_df_for_water_ref: pd.DataFrame) -> SidebarInputs:
    """`params_df_for_water_ref` (market-mode params) is used only to
    compute the current-mix water reference and the sugarcane FRP default
    -- both are price-mode independent."""
    for key, default in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default
    if "water_budget_m3" not in st.session_state:
        st.session_state["water_budget_m3"] = current_mix_water(params_df_for_water_ref, float(st.session_state["land_ha"]))

    with st.sidebar:
        st.subheader("Farmer profile")
        preset_cols = st.columns(2)
        for i, name in enumerate(PRESETS):
            with preset_cols[i % 2]:
                st.button(name, key=f"preset_{i}", on_click=_apply_preset, args=(name, params_df_for_water_ref), width="stretch")

        st.subheader("Scenario inputs")
        land_ha = st.slider("Land (ha)", min_value=1, max_value=50, key="land_ha")

        default_water_m3 = current_mix_water(params_df_for_water_ref, float(land_ha))
        st.caption(f"Current-mix water use at this land size: {default_water_m3:,.0f} m³")
        max_slider = max(default_water_m3 * 2.5, float(st.session_state["water_budget_m3"]) * 1.2, 1.0)
        water_budget_m3 = st.slider(
            "Water budget (m³)",
            min_value=0.0,
            max_value=max_slider,
            key="water_budget_m3",
        )

        food_share_min = st.slider("Min food-crop share", min_value=0.0, max_value=0.6, step=0.05, key="food_share_min")
        max_share = st.slider("Max share per crop", min_value=0.2, max_value=1.0, step=0.05, key="max_share")

        price_mode_label = st.selectbox("Price mode", ["Market (last observed)", "MSP floor"], key="price_mode_label")
        price_mode = "market" if price_mode_label.startswith("Market") else "msp_floor"

        priority = st.slider(
            "Priority: Profit ↔ Sustainability",
            min_value=0.0,
            max_value=1.0,
            step=0.05,
            key="priority",
            help="Left = weight profit more heavily. Right = weight water/fertilizer more heavily.",
        )
        weights = weights_from_priority(priority)
        st.caption(f"pseudo-weights (profit, water, fert) = ({weights[0]:.2f}, {weights[1]:.2f}, {weights[2]:.2f})")

        st.subheader("Risk-aware mode")
        risk_aware = st.toggle(
            "Risk-aware mode (4 objectives, NSGA-III)",
            key="risk_aware_mode",
            help="Adds a portfolio-risk objective (Phase 5 Model B) alongside profit/water/fert.",
        )
        weights4 = None
        sugarcane_risk_mode = "conservative"
        if risk_aware:
            risk_aversion = st.slider(
                "Risk aversion",
                min_value=0.0,
                max_value=1.0,
                step=0.05,
                key="risk_aversion",
                help="Higher = weight the risk objective more heavily in the NSGA-III recommendation.",
            )
            weights4 = weights4_from_priority_and_risk_aversion(priority, risk_aversion)
            st.caption(f"pseudo-weights (profit, water, fert, risk) = ({weights4[0]:.2f}, {weights4[1]:.2f}, {weights4[2]:.2f}, {weights4[3]:.2f})")

            sugarcane_risk_mode_label = st.radio(
                "Sugarcane risk",
                ["Typical crop risk (conservative)", "FRP-based (historical data)"],
                key="sugarcane_risk_mode_label",
            )
            sugarcane_risk_mode = "conservative" if sugarcane_risk_mode_label.startswith("Typical") else "frp_based"
            st.caption(
                ":material/info: FRP fixes sugarcane's price, so historical data shows low price risk; the "
                "conservative setting assumes typical crop variability. Results are sensitive to this choice."
            )

        st.subheader("What-if: price shocks")
        price_multipliers = {}
        sugarcane_default_frp = float(params_df_for_water_ref.loc["sugarcane", "price"]) if "sugarcane" in params_df_for_water_ref.index else 355.0
        with st.expander("Per-crop price multipliers", expanded=False):
            for crop in CROPS:
                if crop == "sugarcane":
                    continue
                price_multipliers[crop] = st.slider(f"{crop} price ×", min_value=0.5, max_value=1.5, value=1.0, step=0.05, key=f"shock_{crop}")
            sugarcane_frp_override = st.number_input(
                "Sugarcane FRP override (₹/qtl)",
                min_value=0.0,
                value=sugarcane_default_frp,
                step=5.0,
                key="sugarcane_frp_override",
            )

        active_shocks = [f"{c} ×{m:.2f}" for c, m in price_multipliers.items() if m != 1.0]
        if sugarcane_frp_override != sugarcane_default_frp:
            active_shocks.append(f"sugarcane FRP → ₹{sugarcane_frp_override:,.0f}/qtl")
        if active_shocks:
            st.warning("Active shocks: " + "; ".join(active_shocks))

        run_clicked = st.button("Run", type="primary", width="stretch")

    scenario = Scenario(
        water_budget_m3=water_budget_m3,
        land_ha=float(land_ha),
        food_share_min=food_share_min,
        max_share=max_share,
        price_mode=price_mode,
    )
    return SidebarInputs(
        scenario=scenario,
        weights=weights,
        weights4=weights4,
        risk_aware=risk_aware,
        sugarcane_risk_mode=sugarcane_risk_mode,
        price_multipliers=price_multipliers,
        sugarcane_frp_override=sugarcane_frp_override,
        run_clicked=run_clicked,
    )
