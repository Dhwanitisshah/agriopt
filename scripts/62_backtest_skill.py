"""Backtest validity checks: does the backtest actually measure forecast skill?

Three questions the headline backtest (scripts/60_backtest.py, 61_backtest_v2.py)
cannot answer on its own:

1. LOOK-AHEAD. The headline run plans every crop on 1 May of year t and reads
   rabi prices as of May. An earlier version read rabi prices in October while
   still planning in May. `info_set="season"` reproduces that; the difference is
   what the look-ahead was worth.
2. SUGARCANE. Sugarcane carries the highest net profit per hectare and its price
   is an administered FRP known before the season, so on the all-crop run it can
   dominate B2 and ORACLE alike and mask forecast skill on the market crops.
   The no-sugarcane variant removes it.
3. WHERE THE FORECAST LOSES. ORACLE knows everything. ORACLE_PRICE knows only
   the realized prices (yields forecast), ORACLE_YIELD only the realized yields
   (prices forecast). Comparing them with B2 splits the gap to perfect foresight
   into a price part and a yield part. If B2 == ORACLE in every cell the
   backtest cannot rank forecasters at all, so the number of cells in which
   B2's allocation differs from ORACLE's is reported for every variant.

Writes reports/results/backtest_skill.csv and backtest_skill.md.
Run after scripts/60_backtest.py has populated models/backtest (RF refits are cached).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from agriopt.config import CROPS, REPORTS_RESULTS

ALLOC_TOL_HA = 1e-4
VARIANTS = {
    "headline (May info, all crops)": {"info_set": "may", "crops": CROPS},
    "legacy look-ahead (rabi prices read in October)": {"info_set": "season", "crops": CROPS},
    "no sugarcane (May info)": {"info_set": "may", "crops": [c for c in CROPS if c != "sugarcane"]},
}
STRATS = ["B1", "B2", "B3", "OURS", "MODEL_B", "ORACLE_PRICE", "ORACLE_YIELD", "ORACLE"]


def load_backtest_module():
    spec = importlib.util.spec_from_file_location("backtest_60", REPO_ROOT / "scripts" / "60_backtest.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_variant(backtest, info_set: str, crops: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (rows, b2_vs_oracle) over the decision years that have a realized outcome."""
    rows, alloc = [], []
    for t in backtest.YEARS:
        year_rows, meta = backtest.run_year(t, info_set=info_set, crops=crops)
        rows.extend(year_rows)
        if len(meta["missing_realized"]) == len(crops):
            continue  # 2020: no realized outcome for any crop
        for label, xs in meta["x_store"].items():
            x2, xo = xs.get("B2"), xs.get("ORACLE")
            if x2 is None or xo is None:
                continue
            diff = np.abs(np.asarray(x2, dtype=float) - np.asarray(xo, dtype=float))
            alloc.append({"year": t, "scenario": label, "identical": bool((diff < ALLOC_TOL_HA).all()), "max_abs_diff_ha": float(diff.max())})
    return pd.DataFrame(rows).dropna(subset=["realized_profit"]), pd.DataFrame(alloc)


def summarise(variant: str, rows: pd.DataFrame, alloc: pd.DataFrame) -> list[dict]:
    out = []
    for scenario, sdf in rows.groupby("scenario"):
        mean = sdf.groupby("strategy")["realized_profit"].mean()
        oracle, b2, b1 = mean.get("ORACLE"), mean.get("B2"), mean.get("B1")
        gap = oracle - b2
        n_cells = int((alloc["scenario"] == scenario).sum())
        n_differ = int(((alloc["scenario"] == scenario) & ~alloc["identical"]).sum())
        rec = {
            "variant": variant, "scenario": scenario, "n_years": int(sdf["year"].nunique()),
            "b2_alloc_differs_from_oracle": f"{n_differ}/{n_cells}",
            "gap_oracle_minus_b2": gap,
        }
        for s in STRATS:
            rec[f"mean_profit_{s}"] = float(mean.get(s, np.nan))
        # share of the gap each partial-foresight oracle closes (they overlap; not additive)
        for s, key in (("ORACLE_PRICE", "gap_closed_by_price_foresight"), ("ORACLE_YIELD", "gap_closed_by_yield_foresight")):
            rec[key] = float((mean.get(s, np.nan) - b2) / gap) if gap and gap > 0 else float("nan")
        rec["b2_capture_vs_oracle"] = float(b2 / oracle) if oracle else float("nan")
        rec["ours_minus_b1"] = float(mean.get("OURS", np.nan) - b1)
        out.append(rec)
    return out


def write_md(df: pd.DataFrame) -> None:
    lines = ["# Backtest validity: look-ahead, sugarcane, and where the forecast loses (2016-2019, n=4)\n\n"]
    lines.append(
        "Mean realized profit per year (Rs, 10 ha) over the four decision years with an outcome. `default` water "
        "budget = B1's own water footprint, `tight` = 0.7x. **n=4: read as four case studies, not as statistics.**\n\n"
    )
    for variant, vdf in df.groupby("variant", sort=False):
        lines.append(f"## {variant}\n\n")
        cols = ["scenario"] + [f"mean_profit_{s}" for s in STRATS] + ["b2_alloc_differs_from_oracle", "gap_closed_by_price_foresight", "gap_closed_by_yield_foresight"]
        lines.append("| " + " | ".join(c.replace("mean_profit_", "") for c in cols) + " |\n|" + "---|" * len(cols) + "\n")
        for _, r in vdf.iterrows():
            cells = []
            for c in cols:
                v = r[c]
                if isinstance(v, float):
                    cells.append(f"{v:.0%}" if c.startswith("gap_closed") and not np.isnan(v) else (f"{v:,.0f}" if not np.isnan(v) else "-"))
                else:
                    cells.append(str(v))
            lines.append("| " + " | ".join(cells) + " |\n")
        lines.append("\n")

    head = df[df["variant"].str.startswith("headline")].set_index("scenario")
    legacy = df[df["variant"].str.startswith("legacy")].set_index("scenario")
    nosc = df[df["variant"].str.startswith("no sugarcane")].set_index("scenario")
    lines.append("## What this shows\n\n")
    for scenario in head.index:
        lines.append(
            f"- **{scenario} water, look-ahead**: reading rabi prices in October instead of May moves OURS's mean "
            f"realized profit by {legacy.loc[scenario, 'mean_profit_OURS'] - head.loc[scenario, 'mean_profit_OURS']:+,.0f} Rs/yr and B2's by "
            f"{legacy.loc[scenario, 'mean_profit_B2'] - head.loc[scenario, 'mean_profit_B2']:+,.0f} Rs/yr (positive = the look-ahead flattered the result).\n"
        )
    for scenario in head.index:
        lines.append(
            f"- **{scenario} water, forecast skill**: B2's allocation differs from ORACLE's in "
            f"{head.loc[scenario, 'b2_alloc_differs_from_oracle']} cells (all crops) and "
            f"{nosc.loc[scenario, 'b2_alloc_differs_from_oracle']} cells without sugarcane; B2 captures "
            f"{head.loc[scenario, 'b2_capture_vs_oracle']:.0%} of ORACLE (all crops) vs {nosc.loc[scenario, 'b2_capture_vs_oracle']:.0%} without sugarcane. "
            f"Knowing only the realized prices closes {head.loc[scenario, 'gap_closed_by_price_foresight']:.0%} of the gap, knowing only the realized yields "
            f"{head.loc[scenario, 'gap_closed_by_yield_foresight']:.0%} (the two overlap).\n"
        )
    (REPORTS_RESULTS / "backtest_skill.md").write_text("".join(lines), encoding="utf-8")
    print("Wrote backtest_skill.md")


def main() -> None:
    backtest = load_backtest_module()
    records = []
    for variant, kw in VARIANTS.items():
        print(f"-- {variant} --")
        rows, alloc = run_variant(backtest, kw["info_set"], kw["crops"])
        records.extend(summarise(variant, rows, alloc))
    df = pd.DataFrame(records)
    df.to_csv(REPORTS_RESULTS / "backtest_skill.csv", index=False)
    print("Wrote backtest_skill.csv")
    write_md(df)
    print(df.drop(columns=[c for c in df.columns if c.startswith("mean_profit_") and not c.endswith(("OURS", "B2", "ORACLE"))]).to_string(index=False))


if __name__ == "__main__":
    main()
