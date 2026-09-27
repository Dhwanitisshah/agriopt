"""Tab: Regional view -- static viewer over the Phase 8.1 region comparison
(reports/results/region_comparison.md and optim_strategies_{konkan,
marathwada}.csv), precomputed into the cache by scripts/40_build_cache.py's
"region_comparison" block. Static/precomputed like the Backtest tab, not a
live-optimizer view."""
from __future__ import annotations

import pandas as pd
import streamlit as st


def render_regional_tab(region_comparison: dict | None) -> None:
    st.subheader("Regional view: Konkan vs Marathwada (net irrigation basis)")
    st.caption(
        "Side-by-side recommended allocation (OURS, NSGA-II) at the current water / market price scenario, "
        "for Maharashtra's two most contrasting IMD subdivisions: Konkan (high-rainfall coastal) and "
        "Marathwada (drought-prone, semi-arid). See reports/results/region_comparison.md (Phase 8.1)."
    )

    if not region_comparison:
        st.warning(
            "Region comparison results not found in the cache -- rerun `python scripts\\40_build_cache.py` "
            "(reads reports/results/optim_strategies_konkan.csv and optim_strategies_marathwada.csv)."
        )
        return

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Konkan**")
        st.dataframe(pd.DataFrame(region_comparison["konkan_strategies"]), hide_index=True, width="stretch")
    with col2:
        st.markdown("**Marathwada**")
        st.dataframe(pd.DataFrame(region_comparison["marathwada_strategies"]), hide_index=True, width="stretch")

    st.markdown("**OURS allocation summary**")
    st.dataframe(pd.DataFrame(region_comparison["ours_summary"]), hide_index=True, width="stretch")

    st.markdown("**Findings (Phase 8.1)**")
    for line in region_comparison.get("findings_bullets", []):
        st.markdown(f"- {line}")
