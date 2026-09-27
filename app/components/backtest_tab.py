"""Tab: Backtest (2016-2019) -- static viewer over the Phase 7.1 decision
backtest results (reports/results/backtest_summary_v2.md /
backtest_fairness_v2.csv / backtest_findings_v2.md), precomputed into the
cache by scripts/40_build_cache.py's "backtest" block. This tab never
re-runs the backtest live -- it only renders committed, already-computed
numbers (same pattern as app/components/evidence.py's report-surfacing
sections)."""
from __future__ import annotations

import pandas as pd
import streamlit as st


def render_backtest_tab(backtest: dict | None) -> None:
    st.subheader("Decision backtest, 2016-2019 (leak-free)")
    st.caption(
        "Maharashtra's yield data has NO rows for year 2020 (any crop) -- every realized-outcome metric here "
        "is computed over n=4 years (2016-2019), not the intended 5. This is a real, documented data gap, "
        "not a bug (see reports/results/RESULTS_INDEX.md, 'Backtest' row). "
        "**n=4 is low statistical power: read these results as directional only, not statistically conclusive.**"
    )

    if not backtest:
        st.warning(
            "Backtest results not found in the cache -- rerun `python scripts\\40_build_cache.py` "
            "(reads reports/results/backtest_fairness_v2.csv and backtest_summary_v2.md)."
        )
        return

    st.markdown("**Win counts and water-matched capture ratio, by strategy (2016-2019, n=4)**")
    fairness_df = pd.DataFrame(backtest["fairness"])
    st.dataframe(fairness_df, hide_index=True, width="stretch")

    st.markdown("**Realized profit per year, B1_SCALED vs OURS vs MODEL_B vs ORACLE**")
    rows_df = pd.DataFrame(backtest["realized_profit_by_year"])
    if not rows_df.empty:
        st.dataframe(rows_df, hide_index=True, width="stretch")
    else:
        st.caption("Per-year realized profit rows not available in this cache build.")

    st.markdown("**Findings (Phase 7.1)**")
    for line in backtest.get("findings_bullets", []):
        st.markdown(f"- {line}")

    st.caption(
        "B2 (profit-max LP) and ORACLE are identical in every year/scenario tested -- both are profit-max LPs "
        "over the same physical feasible region, so this is expected, not a coincidence (see RESULTS_INDEX.md, "
        "row 'Backtest')."
    )
