"""Builds the NEW figures used in docs/handoff/ from COMMITTED result files only.

  fig02_how_it_works.png      simple left-to-right flow (matplotlib)
  fig03_headline_water_profit.png   current mix vs AgriOpt, backtest 2016-2019, default water
  fig07_yield_vs_baseline.png       yield model vs last-3-year mean, 8 decision crops
  fig08_regions_equal_budget.png    AgriOpt profit by region at the same water budget

fig01 (the README's mermaid diagram) is rendered separately in a browser; see
docs/handoff/FIGURES.md. Run: python scripts/make_handoff_figures.py
Inputs: reports/results/backtest_rows.csv, yield_decision_crops_verdicts.csv,
region_equal_budget.csv. Nothing here recomputes a result.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

REPO = Path(__file__).resolve().parent.parent
RES = REPO / "reports" / "results"
OUT = REPO / "docs" / "handoff" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

BLUE, ORANGE, GREY, GREEN = "#2b6cb0", "#dd6b20", "#718096", "#2f855a"


def fig_flow() -> None:
    steps = [
        ("Data", "yield 1997-2019\nmandi prices 2001-2025\nrainfall, MSP/FRP,\ncost, water need"),
        ("Models", "yield: RandomForest\nprice: Naive / XGBoost"),
        ("Per-hectare\neconomics", "profit, water,\nfertilizer, risk\nfor 8 crops"),
        ("Optimizer", "NSGA-II / NSGA-III\n+ exact LP polish"),
        ("Cached\nresults", "one JSON file,\nbuilt offline"),
        ("Streamlit\napp", "recommendation,\ntrade-offs, risk,\nbacktest"),
    ]
    fig, ax = plt.subplots(figsize=(13.4, 3.2))
    ax.set_xlim(0, 13.4)
    ax.set_ylim(0, 3.2)
    ax.axis("off")
    w, gap = 1.8, 0.4
    for i, (title, body) in enumerate(steps):
        x = 0.2 + i * (w + gap)
        ax.add_patch(FancyBboxPatch((x, 0.5), w, 2.2, boxstyle="round,pad=0.05", fc="#ebf4ff" if i % 2 == 0 else "#fffaf0", ec=BLUE, lw=1.5))
        ax.text(x + w / 2, 2.25, title, ha="center", va="center", fontsize=11, fontweight="bold")
        ax.text(x + w / 2, 1.25, body, ha="center", va="center", fontsize=8.5)
        if i < len(steps) - 1:
            ax.add_patch(FancyArrowPatch((x + w + 0.02, 1.6), (x + w + gap - 0.02, 1.6), arrowstyle="-|>", mutation_scale=14, color=GREY))
    ax.text(6.7, 0.12, "The app only reads the cached file -- it never loads the trained models.", ha="center", fontsize=9, style="italic", color=GREY)
    fig.tight_layout()
    fig.savefig(OUT / "fig02_how_it_works.png", dpi=170)
    plt.close(fig)


def fig_headline() -> None:
    df = pd.read_csv(RES / "backtest_rows.csv")
    df = df[(df.scenario == "default") & df.realized_profit.notna() & df.strategy.isin(["B1", "OURS"])]
    g = df.groupby("strategy").agg(profit=("realized_profit", "mean"), water=("water_m3", "mean"), n=("year", "nunique"))
    assert (g["n"] == 4).all()
    labels = ["Current crop mix", "AgriOpt"]
    order = ["B1", "OURS"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6))
    for ax, col, title, unit in (
        (axes[0], "profit", "Profit per year (realized)", "Rs"),
        (axes[1], "water", "Water used per year", "m3"),
    ):
        vals = [g.loc[k, col] for k in order]
        bars = ax.bar(labels, vals, color=[GREY, BLUE], width=0.55)
        ax.set_title(title, fontsize=12)
        ax.set_ylabel(unit)
        ax.set_ylim(0, max(vals) * 1.22)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v * 1.02, f"{v:,.0f}", ha="center", fontsize=10)
        change = (vals[1] / vals[0] - 1) * 100
        ax.text(0.5, 0.93, f"{change:+.1f}%", transform=ax.transAxes, ha="center", fontsize=15, fontweight="bold", color=GREEN if col == "water" else ORANGE)
    fig.suptitle("Backtest 2016-2019 (4 years, 10 ha farm, default water budget): same profit, much less water", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(OUT / "fig03_headline_water_profit.png", dpi=170)
    plt.close(fig)
    print(g.round(0).to_string())


def fig_yield() -> None:
    v = pd.read_csv(RES / "yield_decision_crops_verdicts.csv")
    v = v[v.design.str.startswith("one-step-ahead")].copy()
    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    x = range(len(v))
    w = 0.38
    ax.bar([i - w / 2 for i in x], v.rf_MAPE, w, label="RandomForest", color=BLUE)
    ax.bar([i + w / 2 for i in x], v.last3_MAPE, w, label="Last-3-year average", color=GREY)
    ax.set_xticks(list(x))
    ax.set_xticklabels(v.crop)
    ax.set_ylabel("error, % (lower is better)")
    ax.set_title("Yield forecast error, one year ahead (2016-2019)\nRandomForest beats the 3-year average on 3 of 8 crops")
    for i, (_, r) in enumerate(v.iterrows()):
        if r.rf_loses_to_last3:
            ax.text(i, max(r.rf_MAPE, r.last3_MAPE) + 0.8, "RF loses", ha="center", fontsize=8, color=ORANGE)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "fig07_yield_vs_baseline.png", dpi=170)
    plt.close(fig)


def fig_regions() -> None:
    e = pd.read_csv(RES / "region_equal_budget.csv")
    e = e[(e.rainfall == "normal") & (e.water_scenario == "current") & (e.strategy == "OURS")].set_index("region").profit
    order = ["konkan", "maharashtra", "madhya_maharashtra", "vidarbha", "marathwada"]
    budget = float(pd.read_csv(RES / "region_equal_budget.csv").query("rainfall == 'normal' and water_scenario == 'current'").budget_m3.iloc[0])
    fig, ax = plt.subplots(figsize=(9, 4.6))
    bars = ax.bar([r.replace("_", " ").title() for r in order], [e[r] for r in order], color=BLUE, width=0.6)
    for b in bars:
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() * 1.01, f"{b.get_height():,.0f}", ha="center", fontsize=9)
    ax.set_ylabel("AgriOpt profit, Rs per year (10 ha)")
    ax.set_title(f"Same water budget in every region ({budget:,.0f} m3, normal rainfall)")
    ax.set_ylim(0, max(e) * 1.15)
    fig.tight_layout()
    fig.savefig(OUT / "fig08_regions_equal_budget.png", dpi=170)
    plt.close(fig)


if __name__ == "__main__":
    fig_flow()
    fig_headline()
    fig_yield()
    fig_regions()
    print("wrote figures to", OUT)
