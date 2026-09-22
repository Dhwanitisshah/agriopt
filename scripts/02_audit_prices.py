"""Phase 0 audit of the raw mandi price dataset: Maharashtra coverage for the
8 target crops, unit = Rs/quintal. Writes reports/eda/price_report.md and a
monthly price plot, and saves data/processed/prices_monthly.parquet.
"""
from __future__ import annotations

import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from agriopt.config import (
    CROP_NAME_MAP,
    DATA_PROCESSED,
    PRICES_MONTHLY_PARQUET,
    PRICE_RAW_CSV,
    REPORTS_EDA,
    STATE,
)
from agriopt.data.price_data import (
    TARGET_COMMODITIES,
    build_monthly_prices,
    coverage_report,
    filter_target,
    load_raw_prices,
)


def main() -> None:
    REPORTS_EDA.mkdir(parents=True, exist_ok=True)
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    print(f"Loading raw price data from {PRICE_RAW_CSV} ...")
    raw_cols = pd.read_csv(PRICE_RAW_CSV, nrows=0).columns.tolist()
    print(f"Actual columns: {raw_cols}")

    df = load_raw_prices()
    print(f"Loaded {len(df)} rows, {len(df.columns)} columns.")

    no_price_crops = sorted(k for k, v in CROP_NAME_MAP.items() if v["price"] is None)

    lines: list[str] = []
    lines.append("# Price dataset audit\n")
    lines.append(f"Source: `{PRICE_RAW_CSV}`\n")
    lines.append(f"\nActual raw columns: `{raw_cols}`\n")
    lines.append("\nUnit: Rs/quintal (Min_Price, Max_Price, Modal_Price).\n")

    all_commodities = sorted(df["Commodity"].unique())
    lines.append(f"\n## Commodity coverage\n")
    lines.append(f"- The entire dataset (all states) contains only {len(all_commodities)} "
                  f"distinct commodities: {all_commodities}\n")
    lines.append(f"- Of the 8 AgriOpt target crops, price data exists for: "
                  f"{sorted(TARGET_COMMODITIES)}\n")
    if no_price_crops:
        lines.append(
            f"- **No price coverage at all (any state) for**: {no_price_crops}. "
            "These crops cannot get a data-driven price model from this dataset; "
            "`CROP_NAME_MAP[...]['price']` is `None` for them.\n"
        )
        print(f"WARNING: no price data anywhere in dataset for: {no_price_crops}")

    mh_target = filter_target(df, state=STATE)
    print(f"{STATE} rows for target commodities: {len(mh_target)}")

    lines.append(f"\n## {STATE} coverage for available target commodities\n")
    cov = coverage_report(mh_target)
    lines.append("\n| commodity | n_rows | min_date | max_date | n_markets | n_missing_dates | n_distinct_dates |\n")
    lines.append("|---|---|---|---|---|---|---|\n")
    for _, row in cov.iterrows():
        lines.append(
            f"| {row['commodity']} | {row['n_rows']} | {row['min_date'].date()} | "
            f"{row['max_date'].date()} | {row['n_markets']} | {row['n_missing_dates']} | "
            f"{row['n_distinct_dates']} |\n"
        )

    # --- monthly state-level median modal price ---------------------------
    monthly = build_monthly_prices(mh_target)
    monthly.to_parquet(PRICES_MONTHLY_PARQUET, index=False)
    print(f"Wrote monthly price frame: {PRICES_MONTHLY_PARQUET} ({len(monthly)} rows)")
    lines.append(f"\n## Cleaned output\n- `{PRICES_MONTHLY_PARQUET}`: {len(monthly)} rows "
                  f"(crop, month, modal_price_rs_per_qtl = state-level MEDIAN, n_markets).\n")

    # --- plot ---------------------------------------------------------------
    if not monthly.empty:
        fig, ax = plt.subplots(figsize=(10, 6))
        for crop, sub in monthly.groupby("crop"):
            ax.plot(sub["month"], sub["modal_price_rs_per_qtl"], marker="o", label=crop)
        ax.set_title(f"{STATE} monthly median modal price per crop")
        ax.set_xlabel("month")
        ax.set_ylabel("Rs/quintal")
        ax.legend(fontsize=8)
        fig.autofmt_xdate()
        fig.tight_layout()
        fig.savefig(REPORTS_EDA / "monthly_price_by_crop.png", dpi=150)
        plt.close(fig)
        lines.append("\n## Plot\n- `monthly_price_by_crop.png`\n")
    else:
        lines.append("\n## Plot\n- Skipped: no rows to plot.\n")

    report_path = REPORTS_EDA / "price_report.md"
    report_path.write_text("".join(lines), encoding="utf-8")
    print(f"Wrote report: {report_path}")


if __name__ == "__main__":
    sys.exit(main())
