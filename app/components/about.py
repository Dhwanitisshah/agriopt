"""Tab 5: About & limitations."""
from __future__ import annotations

import streamlit as st


def render_about_tab() -> None:
    st.subheader("About")
    st.markdown(
        "AgriOpt recommends a multi-crop hectare allocation for Maharashtra farmland, trading off "
        "profit, irrigation water need, and fertilizer use (NSGA-II over yield/price/cost/water/fertilizer "
        "estimates from the existing Phase 1-3 pipeline). It is a planning aid built on public data, not "
        "a substitute for local agronomic advice."
    )

    st.subheader("Known limitations")
    st.markdown(
        "- **Costs are all-India, not Maharashtra-specific.** Cost-of-cultivation figures come from national "
        "PIB price releases; state-level costs may differ.\n"
        "- **Fertilizer doses are mostly 2003/04-vintage.** Seven of eight crops use FAO's actual-use figures "
        "from 2003/04 (soybean uses a current ICAR-IISS recommended dose instead); usage has likely shifted since.\n"
        "- **Water is total crop water need, not net irrigation.** The water objective is FAO TM3's total "
        "seasonal water requirement, not requirement minus effective rainfall -- it overstates the water a "
        "rainfed/partially-rainfed crop would actually need to draw from irrigation.\n"
        "- **The price model is a naive persistence baseline.** A naive \"last observed price\" forecast beat "
        "the trained XGBoost model at every backtested horizon (3/6/12 months) -- commodity mandi prices are "
        "highly persistent month-to-month, so the deployed model is the naive one, not a learned one.\n"
        "- **Rainfall is a weak yield feature.** Dropping rainfall from the yield model's feature set slightly "
        "*improved* all-India MAE (10.397 → 9.663) in ablation -- it is kept for completeness but is not "
        "doing much predictive work.\n"
        "- **Rice and cotton yield units are an assumption.** The Kaggle dataset does not document its units; "
        "rice is assumed milled-rice-equivalent (converted to paddy) and cotton is assumed lint bales "
        "(converted to kapas) -- see docs/units.md.\n"
        "- **Sugarcane has no market price series**; it uses the government FRP instead of a forecast.\n"
        "- **profit_risk is a reported metric, not an optimization objective**, and assumes each crop's price "
        "risk is independent of the others (no covariance) -- likely wrong in practice, since monsoon-driven "
        "crops' prices tend to move together."
    )
