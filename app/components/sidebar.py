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
from app.presets import (
    DEFAULT_FOOD_SHARE_MIN,
    DEFAULT_LAND_HA,
    DEFAULT_MAX_SHARE,
    DEFAULT_PRIORITY,
    DEFAULT_RAINFALL_SCENARIO,
    DEFAULT_REGION,
    DEFAULT_RISK_AVERSION,
    DEFAULT_WATER_BASIS,
    PRESETS,
    REGION_LABELS,
    WATER_BASIS_LABELS,
)

DEFAULTS = {
    "land_ha": int(DEFAULT_LAND_HA),
    "food_share_min": DEFAULT_FOOD_SHARE_MIN,
    "max_share": DEFAULT_MAX_SHARE,
    "price_mode_label": "Market (last observed)",
    "priority": DEFAULT_PRIORITY,
    "risk_aware_mode": False,
    "risk_aversion": DEFAULT_RISK_AVERSION,
    "sugarcane_risk_mode_label": "Typical crop risk (conservative)",
    "region_label": REGION_LABELS[DEFAULT_REGION],
    "water_basis_label": WATER_BASIS_LABELS[DEFAULT_WATER_BASIS],
    "rainfall_scenario": DEFAULT_RAINFALL_SCENARIO,
}


@dataclass
class SidebarInputs:
    scenario: Scenario
    weights: tuple[float, float, float]
    weights4: tuple[float, float, float, float] | None
    risk_aware: bool
    sugarcane_risk_mode: str
    priority: float
    risk_aversion: float
    price_multipliers: dict = field(default_factory=dict)
    sugarcane_frp_override: float | None = None
    run_clicked: bool = False


def _apply_preset(name: str, params_df: pd.DataFrame, current_mix_share: dict | None) -> None:
    preset = PRESETS[name]
    land_ha = preset["land_ha"] if preset["land_ha"] is not None else st.session_state.get("land_ha", DEFAULTS["land_ha"])
    st.session_state["land_ha"] = land_ha
    st.session_state["water_budget_m3"] = preset["water_mult"] * current_mix_water(params_df, float(land_ha), current_mix_share)
    st.session_state["region_label"] = REGION_LABELS[preset.get("region", DEFAULT_REGION)]
    st.session_state["water_basis_label"] = WATER_BASIS_LABELS[preset.get("water_basis", DEFAULT_WATER_BASIS)]
    st.session_state["rainfall_scenario"] = preset.get("rainfall_scenario", DEFAULT_RAINFALL_SCENARIO)


def render_sidebar(params_df_for_water_ref: pd.DataFrame, current_mix_share: dict | None = None) -> SidebarInputs:
    """`params_df_for_water_ref` (market-mode params) is used only to
    compute the current-mix water reference and the sugarcane FRP default
    -- both are price-mode independent. `current_mix_share` (Phase 10) is
    the cache's precomputed B1 historical area share -- see
    agriopt.optim.baselines.current_mix's docstring; passed through so this
    module never reads the gitignored yield_clean.parquet."""
    for key, default in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default
    if "water_budget_m3" not in st.session_state:
        st.session_state["water_budget_m3"] = current_mix_water(params_df_for_water_ref, float(st.session_state["land_ha"]), current_mix_share)

    with st.sidebar:
        st.subheader("Farmer profile")
        preset_cols = st.columns(2)
        for i, name in enumerate(PRESETS):
            with preset_cols[i % 2]:
                st.button(
                    name,
                    key=f"preset_{i}",
                    on_click=_apply_preset,
                    args=(name, params_df_for_water_ref, current_mix_share),
                    width="stretch",
                )

        st.subheader("Scenario inputs")
        land_ha = st.slider("Land (ha)", min_value=1, max_value=50, key="land_ha")

        default_water_m3 = current_mix_water(params_df_for_water_ref, float(land_ha), current_mix_share)
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

        st.subheader("Region & water basis")
        region_label = st.selectbox("Region", list(REGION_LABELS.values()), key="region_label")
        region = next(k for k, v in REGION_LABELS.items() if v == region_label)
        water_basis_label = st.selectbox("Water basis", list(WATER_BASIS_LABELS.values()), key="water_basis_label")
        water_basis = next(k for k, v in WATER_BASIS_LABELS.items() if v == water_basis_label)
        rainfall_scenario = "normal"
        if water_basis == "net_irrigation":
            rainfall_scenario_label = st.radio(
                "Rainfall scenario",
                ["Normal (30-yr mean)", "Dry (20th percentile year)"],
                key="rainfall_scenario_label",
                index=0 if st.session_state.get("rainfall_scenario", DEFAULT_RAINFALL_SCENARIO) == "normal" else 1,
            )
            rainfall_scenario = "normal" if rainfall_scenario_label.startswith("Normal") else "dry"
            st.session_state["rainfall_scenario"] = rainfall_scenario
        st.caption(
            "Region + water basis change how much water each crop is charged for (Phase 8/8.1) -- see the "
            "Regional view and Model inputs & evidence tabs."
        )

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
        risk_aversion = DEFAULT_RISK_AVERSION
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
        water_basis=water_basis,
        rainfall_scenario=rainfall_scenario,
        region=region,
    )
    return SidebarInputs(
        scenario=scenario,
        weights=weights,
        weights4=weights4,
        risk_aware=risk_aware,
        sugarcane_risk_mode=sugarcane_risk_mode,
        priority=priority,
        risk_aversion=risk_aversion,
        price_multipliers=price_multipliers,
        sugarcane_frp_override=sugarcane_frp_override,
        run_clicked=run_clicked,
    )
