"""Loading and cleaning logic for the mandi price dataset (Kaggle
"indian-agricultural-mandi-prices-20232025"). Reusable functions only --
reporting and plotting live in scripts/02_audit_prices.py.

Prices in the source data are Rs/quintal (mandi modal price convention).
"""
from __future__ import annotations

import pandas as pd

from agriopt.config import CROP_NAME_MAP, PRICE_RAW_CSV, STATE

# canonical crop -> commodity name in the price dataset, target crops only
PRICE_NAME_TO_CANON = {
    v["price"]: k for k, v in CROP_NAME_MAP.items() if v["price"] is not None
}
TARGET_COMMODITIES = set(PRICE_NAME_TO_CANON)

RAW_STRING_COLUMNS = ["STATE", "District Name", "Market Name", "Commodity", "Variety", "Grade"]


def load_raw_prices(path=PRICE_RAW_CSV) -> pd.DataFrame:
    """Load the raw price CSV, stripping whitespace from column names and
    string-typed values, and parsing Price Date."""
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    for col in RAW_STRING_COLUMNS:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    df["Price Date"] = pd.to_datetime(df["Price Date"], errors="coerce")
    return df


def filter_target(df: pd.DataFrame, state: str = STATE) -> pd.DataFrame:
    """Filter to the given state and the target commodities that actually
    have price coverage (CROP_NAME_MAP price != None)."""
    return df[(df["STATE"] == state) & (df["Commodity"].isin(TARGET_COMMODITIES))].copy()


def coverage_report(df: pd.DataFrame) -> pd.DataFrame:
    """Per-commodity coverage: row count, date range, #markets, #missing (NaT) dates."""
    rows = []
    for commodity, sub in df.groupby("Commodity"):
        rows.append(
            {
                "commodity": commodity,
                "n_rows": len(sub),
                "min_date": sub["Price Date"].min(),
                "max_date": sub["Price Date"].max(),
                "n_markets": sub["Market Name"].nunique(),
                "n_missing_dates": sub["Price Date"].isna().sum(),
                "n_distinct_dates": sub["Price Date"].nunique(),
            }
        )
    return pd.DataFrame(rows).sort_values("n_rows", ascending=False).reset_index(drop=True)


def build_monthly_prices(df: pd.DataFrame) -> pd.DataFrame:
    """State-level monthly MEDIAN modal price per (canonical) crop.

    Output columns: crop, month, modal_price_rs_per_qtl, n_markets.
    """
    work = df.dropna(subset=["Price Date"]).copy()
    work["crop"] = work["Commodity"].map(PRICE_NAME_TO_CANON)
    work["month"] = work["Price Date"].dt.to_period("M").dt.to_timestamp()

    grouped = work.groupby(["crop", "month"]).agg(
        modal_price_rs_per_qtl=("Modal_Price", "median"),
        n_markets=("Market Name", "nunique"),
    )
    return grouped.reset_index().sort_values(["crop", "month"]).reset_index(drop=True)
