"""Phase 6, Item 6: plan CSV + markdown summary for download buttons."""
from __future__ import annotations

import io

import pandas as pd

from app.pipeline import ScenarioResult, pct_delta, summary_sentence

SEASON_LABELS = {"kharif": "Kharif", "rabi": "Rabi"}


def build_plan_csv(x, params_df: pd.DataFrame) -> str:
    crops = list(params_df.index)
    df = pd.DataFrame(
        {
            "crop": crops,
            "hectares": x,
            "season": [" + ".join(SEASON_LABELS[s] for s in sorted(params_df.loc[c, "seasons_occupied"])) for c in crops],
        }
    )
    df = df[df["hectares"] > 1e-6].sort_values("hectares", ascending=False)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()


def build_summary_markdown(result: ScenarioResult, params_df: pd.DataFrame) -> str:
    scenario = result.scenario
    r1, r4 = result.evals["B1"], result.evals["OURS"]
    x4 = result.x["OURS"]
    crops = list(params_df.index)

    lines = ["# AgriOpt recommendation summary\n\n"]
    lines.append("## Inputs\n\n")
    lines.append(f"- Land: {scenario.land_ha:.1f} ha\n")
    lines.append(f"- Water budget: {scenario.water_budget_m3:,.0f} m3\n")
    lines.append(f"- Min food-crop share: {scenario.food_share_min:.0%}\n")
    lines.append(f"- Max share per crop: {scenario.max_share:.0%}\n")
    lines.append(f"- Price mode: {scenario.price_mode}\n")
    lines.append(f"- Risk-aware mode: {'on' if result.risk_aware else 'off'}\n\n")

    lines.append("## Recommended allocation\n\n")
    lines.append("| crop | hectares | season |\n|---|---|---|\n")
    for c in crops:
        ha = x4[crops.index(c)]
        if ha <= 1e-6:
            continue
        season = " + ".join(SEASON_LABELS[s] for s in sorted(params_df.loc[c, "seasons_occupied"]))
        lines.append(f"| {c} | {ha:.2f} | {season} |\n")

    lines.append("\n## KPIs vs current mix (B1)\n\n")
    lines.append("| metric | current mix | recommended | delta |\n|---|---|---|---|\n")
    lines.append(f"| profit (Rs) | {r1['profit']:,.0f} | {r4['profit']:,.0f} | {pct_delta(r4['profit'], r1['profit']):+.1f}% |\n")
    lines.append(f"| water (m3) | {r1['water_m3']:,.0f} | {r4['water_m3']:,.0f} | {pct_delta(r4['water_m3'], r1['water_m3']):+.1f}% |\n")
    lines.append(f"| fertilizer (kg) | {r1['fert_kg']:,.0f} | {r4['fert_kg']:,.0f} | {pct_delta(r4['fert_kg'], r1['fert_kg']):+.1f}% |\n")
    lines.append(f"| food-crop share | {r1['food_share']:.0%} | {r4['food_share']:.0%} | {(r4['food_share'] - r1['food_share']) * 100:+.1f}pp |\n")
    lines.append(f"| profit risk (Rs) | {r1['profit_risk']:,.0f} | {r4['profit_risk']:,.0f} | {pct_delta(r4['profit_risk'], r1['profit_risk']):+.1f}% |\n\n")

    lines.append(f"{summary_sentence(r1, r4)}\n\n")

    lines.append("## Assumptions and limitations\n\n")
    lines.append(
        "- Costs are all-India, not Maharashtra-specific; fertilizer doses are mostly 2003/04-vintage.\n"
        "- Water is total crop water need (FAO TM3), not net irrigation requirement.\n"
        "- The price model is a naive persistence forecast (beat a trained model on backtest).\n"
        "- Rice/cotton yield unit conversions (paddy/kapas) are documented assumptions, not verified ground truth.\n"
        "- Sugarcane has no market price series; it uses the government FRP instead of a forecast.\n"
        "- See the app's About & limitations tab and docs/ for the full list.\n"
    )

    return "".join(lines)
