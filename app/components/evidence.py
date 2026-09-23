"""Tab 4: Model inputs & evidence -- per-crop params, model metrics, SHAP, sources."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from agriopt.config import CROP_REFERENCE_CSV, REPO_ROOT

SHAP_IMAGE = REPO_ROOT / "reports" / "results" / "shap_summary_xgb.png"
RISK_HEATMAP_IMAGE = REPO_ROOT / "reports" / "results" / "risk_correlation_heatmap.png"
ABLATION_CSV = REPO_ROOT / "reports" / "results" / "ablation_decisions.csv"
FRONT_QUALITY_V2_CSV = REPO_ROOT / "reports" / "results" / "optim_front_quality_v2.csv"


def _source_label(row: pd.Series) -> str:
    parts = [f"price: CEDA Agmarknet / {row['cost_source']}", f"water: {row['water_source']}", f"fert: {row['fert_source']}"]
    return "; ".join(parts)


def render_evidence_tab(params_df: pd.DataFrame, yield_meta: dict, price_meta: dict) -> None:
    st.subheader("Per-crop inputs")
    ref = pd.read_csv(CROP_REFERENCE_CSV).set_index("crop")

    rows = []
    for crop, row in params_df.iterrows():
        ref_row = ref.loc[crop]
        msp = ref_row["msp_rs_per_qtl"]
        msp_display = f"{msp:,.0f}" if pd.notna(msp) else f"FRP {ref_row['admin_price_rs_per_qtl']:,.0f}"
        rows.append(
            {
                "crop": crop,
                "yield (qtl/ha)": row["yield_qtl_ha"],
                "price (₹/qtl)": row["price"],
                "MSP/FRP (₹/qtl)": msp_display,
                "cost (₹/ha)": row["cost_ha"],
                "profit (₹/ha)": row["profit_ha"],
                "water (m³/ha)": row["water_m3_ha"],
                "fert (kg/ha)": row["fert_kg_ha"],
                "source": _source_label(ref_row),
            }
        )
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

    st.subheader("Yield model")
    m = yield_meta["metrics_maharashtra"]
    st.markdown(
        f"**{yield_meta['model_name']}**, trained on years {yield_meta['train_years']} — "
        f"Maharashtra validation/test metrics: MAE={m['MAE']:.3f} qtl/ha, RMSE={m['RMSE']:.3f}, "
        f"R²={m['R2']:.3f}, MAPE={m['MAPE']:.1f}%."
    )
    st.caption(yield_meta.get("note", ""))

    st.subheader("Price model")
    mae_h12 = price_meta["backtest_overall_mae_h12"]
    mae_str = ", ".join(f"{k}={v:,.0f}" for k, v in mae_h12.items())
    st.markdown(
        f"Selected method for horizon=12 months: **{price_meta['method']}** (backtest MAE, Rs/qtl: {mae_str}). "
        f"Backtest window: {price_meta['backtest_window']}."
    )

    st.subheader("Yield model feature importance (SHAP)")
    if SHAP_IMAGE.exists():
        st.image(str(SHAP_IMAGE), width="stretch")
    else:
        st.caption(f"SHAP summary image not found at {SHAP_IMAGE}")

    st.subheader("Risk model (Phase 5)")
    if RISK_HEATMAP_IMAGE.exists():
        st.image(str(RISK_HEATMAP_IMAGE), width="stretch", caption="Relative-deviation correlation across crops (detrended revenue/ha)")
    else:
        st.caption(f"Risk correlation heatmap not found at {RISK_HEATMAP_IMAGE}")

    st.markdown("**NSGA-II vs LP reference front quality (v2 grid front)**")
    if FRONT_QUALITY_V2_CSV.exists():
        st.dataframe(pd.read_csv(FRONT_QUALITY_V2_CSV), hide_index=True, width="stretch")
    else:
        st.caption(f"{FRONT_QUALITY_V2_CSV.name} not found -- run scripts/31_run_risk.py.")

    st.markdown("**Information ablation (Experiment 4)**")
    if ABLATION_CSV.exists():
        st.dataframe(pd.read_csv(ABLATION_CSV), hide_index=True, width="stretch")
        st.caption("B2/B3 rows: profit loss vs the FULL-information decision. OURS rows: dominance + deltas vs FULL (see reports/results/ablation_decisions.md).")
    else:
        st.caption(f"{ABLATION_CSV.name} not found -- run scripts/50_ablation.py.")

    st.subheader("Data sources")
    st.markdown(
        "- **Yield**: Kaggle *crop-yield-in-indian-states-dataset* (APY-style: area/production/yield by state/crop/season/year)\n"
        "- **Prices**: CEDA Agmarknet API (primary, mandi modal prices); Kaggle mandi CSV (secondary, few crops)\n"
        "- **Cost of cultivation & MSP**: PIB Kharif/Rabi Marketing Season price releases\n"
        "- **Sugarcane price**: CCEA Fair and Remunerative Price (FRP), not MSP\n"
        "- **Water need**: FAO TM3 crop water requirement tables\n"
        "- **Fertilizer dose**: FAO (2005) *Fertilizer use by crop in India*, Table 13 (soybean: ICAR-IISS recommended dose)"
    )
