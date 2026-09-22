"""Price data: CEDA Agmarknet API (primary) + Kaggle mandi CSV (secondary,
used only to fill months CEDA doesn't have). Reusable functions only --
fetching/orchestration lives in scripts/02_audit_prices.py and
scripts/03_fetch_ceda_prices.py.

Prices are Rs/quintal throughout. Sugarcane has no mandi series (sold to
mills at the government-set FRP) -- see get_price_series().
"""
from __future__ import annotations

import pandas as pd

from agriopt.config import CROP_NAME_MAP, CROP_REFERENCE_CSV, PRICE_RAW_CSV, PRICES_MONTHLY_PARQUET, STATE

# canonical crop -> commodity name in the Kaggle price dataset, target crops only
KAGGLE_PRICE_NAME_TO_CANON = {
    v["kaggle_price"]: k for k, v in CROP_NAME_MAP.items() if v["kaggle_price"] is not None
}
TARGET_COMMODITIES = set(KAGGLE_PRICE_NAME_TO_CANON)

# canonical crop -> CEDA commodity name, target crops only (None for sugarcane)
CEDA_COMMODITY_NAME = {k: v["ceda_commodity"] for k, v in CROP_NAME_MAP.items()}
CEDA_TRACKED_CROPS = [k for k, v in CEDA_COMMODITY_NAME.items() if v is not None]

RAW_STRING_COLUMNS = ["STATE", "District Name", "Market Name", "Commodity", "Variety", "Grade"]

MONTHLY_COLUMNS = ["crop", "month", "modal_price_rs_per_qtl", "min_price", "max_price", "source"]


# --- Kaggle mandi CSV (secondary source) -----------------------------------


def load_raw_prices(path=PRICE_RAW_CSV) -> pd.DataFrame:
    """Load the raw Kaggle price CSV, stripping whitespace and parsing dates."""
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    for col in RAW_STRING_COLUMNS:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    df["Price Date"] = pd.to_datetime(df["Price Date"], errors="coerce")
    return df


def filter_target(df: pd.DataFrame, state: str = STATE) -> pd.DataFrame:
    """Filter to the given state and the target commodities that have Kaggle coverage."""
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


def build_monthly_prices_kaggle(df: pd.DataFrame) -> pd.DataFrame:
    """State-level monthly MEDIAN modal/min/max price per crop, from Kaggle rows.

    Output columns match MONTHLY_COLUMNS, source="kaggle_mandi".
    """
    work = df.dropna(subset=["Price Date"]).copy()
    work["crop"] = work["Commodity"].map(KAGGLE_PRICE_NAME_TO_CANON)
    work["month"] = work["Price Date"].dt.to_period("M").dt.to_timestamp()

    grouped = work.groupby(["crop", "month"]).agg(
        modal_price_rs_per_qtl=("Modal_Price", "median"),
        min_price=("Min_Price", "median"),
        max_price=("Max_Price", "median"),
    )
    out = grouped.reset_index()
    out["source"] = "kaggle_mandi"
    return out[MONTHLY_COLUMNS].sort_values(["crop", "month"]).reset_index(drop=True)


# --- CEDA Agmarknet API (primary source) ------------------------------------


def build_monthly_prices_ceda(records: list[dict], crop: str) -> pd.DataFrame:
    """Aggregate CEDA daily state-level records (as returned by
    CedaClient.get_prices) into monthly MEDIAN modal/min/max price for one crop.

    Output columns match MONTHLY_COLUMNS, source="ceda_api".
    """
    if not records:
        return pd.DataFrame(columns=MONTHLY_COLUMNS)

    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()

    grouped = df.groupby("month").agg(
        modal_price_rs_per_qtl=("modal_price", "median"),
        min_price=("min_price", "median"),
        max_price=("max_price", "median"),
    )
    out = grouped.reset_index()
    out["crop"] = crop
    out["source"] = "ceda_api"
    return out[MONTHLY_COLUMNS].sort_values("month").reset_index(drop=True)


# --- Merge -------------------------------------------------------------------


def merge_price_sources(ceda_monthly: pd.DataFrame, kaggle_monthly: pd.DataFrame) -> pd.DataFrame:
    """Combine CEDA (primary) and Kaggle (secondary) monthly frames. CEDA wins
    for any (crop, month) present in both; Kaggle only fills months CEDA lacks."""
    ceda_keys = set(zip(ceda_monthly["crop"], ceda_monthly["month"]))
    kaggle_only = kaggle_monthly[
        ~kaggle_monthly.apply(lambda r: (r["crop"], r["month"]) in ceda_keys, axis=1)
    ]
    combined = pd.concat([ceda_monthly, kaggle_only], ignore_index=True)
    return combined.sort_values(["crop", "month"]).reset_index(drop=True)


# --- Coverage --------------------------------------------------------------


def compute_monthly_coverage(monthly: pd.DataFrame, crops: list[str], min_months: int = 60) -> pd.DataFrame:
    """Per-crop coverage over the combined monthly frame: date range, #months,
    #missing months (gaps within the observed range), last available month,
    and a low-coverage flag (n_months < min_months)."""
    rows = []
    for crop in crops:
        sub = monthly[monthly["crop"] == crop]
        if sub.empty:
            rows.append(
                {
                    "crop": crop,
                    "min_month": None,
                    "max_month": None,
                    "n_months": 0,
                    "n_missing_months": None,
                    "last_month": None,
                    "low_coverage": True,
                }
            )
            continue
        months = sub["month"].sort_values()
        full_range = pd.period_range(months.min(), months.max(), freq="M")
        n_months = months.nunique()
        n_missing = len(full_range) - n_months
        rows.append(
            {
                "crop": crop,
                "min_month": months.min(),
                "max_month": months.max(),
                "n_months": n_months,
                "n_missing_months": n_missing,
                "last_month": months.max(),
                "low_coverage": n_months < min_months,
            }
        )
    return pd.DataFrame(rows)


# --- Access ------------------------------------------------------------------


def get_price_series(crop: str, monthly_path=PRICES_MONTHLY_PARQUET, reference_path=CROP_REFERENCE_CSV) -> pd.DataFrame:
    """Return the monthly price series for a crop.

    Sugarcane has no mandi series -- it returns a flat series built from
    crop_reference.csv's admin_price_rs_per_qtl (the government FRP) once
    that column is filled in, and raises a clear error while it's still
    empty (it ships as a TODO placeholder; we do not invent a number).
    """
    if crop == "sugarcane":
        ref = pd.read_csv(reference_path)
        row = ref[ref["crop"] == "sugarcane"]
        if row.empty or pd.isna(row.iloc[0]["admin_price_rs_per_qtl"]) or row.iloc[0]["admin_price_rs_per_qtl"] == "":
            raise ValueError(
                "sugarcane has no mandi price series and crop_reference.csv's "
                "admin_price_rs_per_qtl (FRP) is still empty -- fill it in "
                "(see admin_price_source) before calling get_price_series('sugarcane')."
            )
        price = float(row.iloc[0]["admin_price_rs_per_qtl"])
        return pd.DataFrame(
            {
                "crop": ["sugarcane"],
                "modal_price_rs_per_qtl": [price],
                "min_price": [price],
                "max_price": [price],
                "source": [row.iloc[0]["admin_price_type"]],
            }
        )

    monthly = pd.read_parquet(monthly_path)
    sub = monthly[monthly["crop"] == crop]
    if sub.empty:
        raise ValueError(f"No price data for crop={crop!r} in {monthly_path}")
    return sub.reset_index(drop=True)
