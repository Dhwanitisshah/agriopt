"""Audit prices: (1) raw Kaggle mandi CSV coverage (secondary source) ->
reports/eda/price_report.md, and (2) the CEDA+Kaggle merged
data/processed/prices_monthly.parquet built by scripts/03_fetch_ceda_prices.py
-> coverage table appended to reports/eda/eda_report.md and
reports/eda/prices_monthly.png.

Run scripts/03_fetch_ceda_prices.py first -- this script only reads the
parquet it produces, it does not fetch or rebuild it.
"""
from __future__ import annotations

import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from agriopt.config import (
    CROPS,
    CROP_NAME_MAP,
    DATA_PROCESSED,
    PRICES_MONTHLY_PARQUET,
    PRICE_RAW_CSV,
    REPORTS_EDA,
    STATE,
)
from agriopt.data.price_data import (
    CEDA_TRACKED_CROPS,
    TARGET_COMMODITIES,
    compute_monthly_coverage,
    coverage_report,
    filter_target,
    load_raw_prices,
)

MIN_MONTHS = 60


def audit_kaggle_secondary() -> None:
    print(f"Loading raw Kaggle price data from {PRICE_RAW_CSV} ...")
    raw_cols = pd.read_csv(PRICE_RAW_CSV, nrows=0).columns.tolist()
    print(f"Actual columns: {raw_cols}")

    df = load_raw_prices()
    print(f"Loaded {len(df)} rows, {len(df.columns)} columns.")

    no_price_anywhere = sorted(k for k in CROPS if CROP_NAME_MAP[k]["ceda_commodity"] is None and CROP_NAME_MAP[k]["kaggle_price"] is None)

    lines: list[str] = []
    lines.append("# Price dataset audit (Kaggle mandi CSV -- secondary source)\n")
    lines.append(f"Source: `{PRICE_RAW_CSV}`\n")
    lines.append(f"\nActual raw columns: `{raw_cols}`\n")
    lines.append("\nUnit: Rs/quintal (Min_Price, Max_Price, Modal_Price).\n")
    lines.append(
        "\nThis is the SECONDARY price source (see `price_report` vs "
        "`eda_report.md` \"Price coverage\" for the CEDA-primary, merged view). "
        "It only fills months CEDA lacks.\n"
    )

    all_commodities = sorted(df["Commodity"].unique())
    lines.append("\n## Commodity coverage\n")
    lines.append(f"- The entire dataset (all states) contains only {len(all_commodities)} "
                  f"distinct commodities: {all_commodities}\n")
    lines.append(f"- Of the 8 AgriOpt target crops, Kaggle price data exists for: "
                  f"{sorted(TARGET_COMMODITIES)}\n")
    if no_price_anywhere:
        lines.append(
            f"- **No price coverage at all (neither CEDA nor Kaggle) for**: {no_price_anywhere}. "
            "See admin_price_rs_per_qtl (FRP) in crop_reference.csv instead.\n"
        )
        print(f"NOTE: no mandi price source (CEDA or Kaggle) for: {no_price_anywhere}")

    mh_target = filter_target(df, state=STATE)
    print(f"{STATE} rows for target commodities: {len(mh_target)}")

    lines.append(f"\n## {STATE} coverage for available Kaggle target commodities\n")
    cov = coverage_report(mh_target)
    lines.append("\n| commodity | n_rows | min_date | max_date | n_markets | n_missing_dates | n_distinct_dates |\n")
    lines.append("|---|---|---|---|---|---|---|\n")
    for _, row in cov.iterrows():
        lines.append(
            f"| {row['commodity']} | {row['n_rows']} | {row['min_date'].date()} | "
            f"{row['max_date'].date()} | {row['n_markets']} | {row['n_missing_dates']} | "
            f"{row['n_distinct_dates']} |\n"
        )

    report_path = REPORTS_EDA / "price_report.md"
    report_path.write_text("".join(lines), encoding="utf-8")
    print(f"Wrote report: {report_path}")


def audit_merged_coverage() -> None:
    if not PRICES_MONTHLY_PARQUET.exists():
        print(f"STOP: {PRICES_MONTHLY_PARQUET} not found -- run scripts/03_fetch_ceda_prices.py first.")
        sys.exit(1)

    monthly = pd.read_parquet(PRICES_MONTHLY_PARQUET)
    print(f"Loaded {PRICES_MONTHLY_PARQUET}: {len(monthly)} rows.")

    cov = compute_monthly_coverage(monthly, CROPS, min_months=MIN_MONTHS)
    low = cov[cov["low_coverage"]]["crop"].tolist()
    print(f"Crops below {MIN_MONTHS} months: {low if low else 'none'}")

    lines: list[str] = []
    lines.append("\n## Price coverage (CEDA primary + Kaggle secondary, merged)\n")
    lines.append(f"Source: `{PRICES_MONTHLY_PARQUET}` (built by `scripts/03_fetch_ceda_prices.py`).\n")
    lines.append(
        "\n| crop | min_month | max_month | n_months | n_missing_months | last_month | flag |\n"
        "|---|---|---|---|---|---|---|\n"
    )
    for _, row in cov.iterrows():
        if row["n_months"] == 0:
            note = "no mandi series (sugarcane: FRP admin price)" if row["crop"] == "sugarcane" else "NO DATA"
            lines.append(f"| {row['crop']} | - | - | 0 | - | - | **{note}** |\n")
            continue
        flag = f"< {MIN_MONTHS} months" if row["low_coverage"] else ""
        lines.append(
            f"| {row['crop']} | {row['min_month'].date()} | {row['max_month'].date()} | "
            f"{row['n_months']} | {row['n_missing_months']} | {row['last_month'].date()} | {flag} |\n"
        )

    eda_report_path = REPORTS_EDA / "eda_report.md"
    with open(eda_report_path, "a", encoding="utf-8") as f:
        f.write("".join(lines))
    print(f"Appended price coverage to: {eda_report_path}")

    # --- plot ----------------------------------------------------------------
    plotted = monthly[monthly["crop"].isin(CEDA_TRACKED_CROPS)]
    if not plotted.empty:
        fig, ax = plt.subplots(figsize=(10, 6))
        for crop, sub in plotted.groupby("crop"):
            sub = sub.sort_values("month")
            ax.plot(sub["month"], sub["modal_price_rs_per_qtl"], marker="o", markersize=3, label=crop)
        ax.set_title(f"{STATE} monthly modal price per crop (CEDA primary, Kaggle secondary)")
        ax.set_xlabel("month")
        ax.set_ylabel("Rs/quintal")
        ax.legend(fontsize=8)
        fig.autofmt_xdate()
        fig.tight_layout()
        fig.savefig(REPORTS_EDA / "prices_monthly.png", dpi=150)
        plt.close(fig)
        print(f"Wrote plot: {REPORTS_EDA / 'prices_monthly.png'}")
    else:
        print("No rows to plot for prices_monthly.png.")


def main() -> None:
    REPORTS_EDA.mkdir(parents=True, exist_ok=True)
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    audit_kaggle_secondary()
    audit_merged_coverage()


if __name__ == "__main__":
    sys.exit(main())
