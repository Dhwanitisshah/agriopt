"""Tab 3: Strategy comparison -- E3.1-style table (B1/B2/B3/recommended)
with % vs B1, for the current scenario inputs."""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from app.pipeline import ScenarioResult, pct_delta

STRATEGY_LABELS = {"B1": "B1 current mix", "B2": "B2 profit-max", "B3": "B3 same-profit-min-water", "OURS": "Recommended"}


def render_comparison_tab(result: ScenarioResult) -> None:
    if not result.feasible:
        st.warning(result.message)
        return

    b1 = result.evals["B1"]
    rows = []
    for key, label in STRATEGY_LABELS.items():
        r = result.evals[key]
        if r is None:
            rows.append({"strategy": label, "feasible": False})
            continue
        rows.append(
            {
                "strategy": label,
                "profit (₹)": r["profit"],
                "water (m³)": r["water_m3"],
                "fert (kg)": r["fert_kg"],
                "food share": r["food_share"],
                "n crops": r["n_crops"],
                "profit risk (₹)": r["profit_risk"],
                "profit % vs B1": pct_delta(r["profit"], b1["profit"]),
                "water % vs B1": pct_delta(r["water_m3"], b1["water_m3"]),
                "fert % vs B1": pct_delta(r["fert_kg"], b1["fert_kg"]),
                "feasible": r["feasible"],
            }
        )

    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        hide_index=True,
        width="stretch",
        column_config={
            "profit (₹)": st.column_config.NumberColumn(format="%.0f"),
            "water (m³)": st.column_config.NumberColumn(format="%.0f"),
            "fert (kg)": st.column_config.NumberColumn(format="%.0f"),
            "food share": st.column_config.NumberColumn(format="%.0%%"),
            "profit risk (₹)": st.column_config.NumberColumn(format="%.0f"),
            "profit % vs B1": st.column_config.NumberColumn(format="%+.1f%%"),
            "water % vs B1": st.column_config.NumberColumn(format="%+.1f%%"),
            "fert % vs B1": st.column_config.NumberColumn(format="%+.1f%%"),
        },
    )

    if not np.isnan(df.loc[df["strategy"] == "Recommended", "water % vs B1"].iloc[0]):
        rec = df[df["strategy"] == "Recommended"].iloc[0]
        st.caption(
            f"Recommended vs B1 (current mix): {rec['profit % vs B1']:+.1f}% profit, "
            f"{rec['water % vs B1']:+.1f}% water, {rec['fert % vs B1']:+.1f}% fertilizer."
        )
