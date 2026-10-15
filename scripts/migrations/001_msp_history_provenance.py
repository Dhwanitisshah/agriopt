"""ONE-OFF migration 001: add a `provenance` column to data/reference/msp_history.csv.

This is the code that used to live in scripts/61_backtest_v2.py and ran (and rewrote the
reference file) on every backtest run. It has already been applied to the committed CSV; it
is kept here, idempotent, as the record of how the column was produced. Run it only if you
are rebuilding msp_history.csv from scratch:

    python scripts/migrations/001_msp_history_provenance.py

Adds `provenance` (primary / secondary / blank) to EVERY row and, for jowar/soybean/maize
2017 only, replaces source_url with the verified primary PIB citation and marks
provenance='primary_verified_v2'. Existing crop/year/msp/cost values are never modified.

Verification note: jowar/soybean/maize 2017 were flagged secondary in Phase 7 (sourced from a
business-standard comparison table because agricoop.gov.in returned a DNS failure). A primary
government source was found instead: a PIB press release (03-Aug-2018, Rajya Sabha Unstarred
Question No. 1934, Ministry of Agriculture & Farmers Welfare) whose Annexure gives 2017-18
Cost/MSP for every kharif crop, including JOWAR (Hybrid)=1700, MAIZE=1425, SOYABEEN=3050 --
exactly the values already in msp_history.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from agriopt.config import MSP_HISTORY_CSV

VERIFIED_2017_PRIMARY_URL = "https://pib.gov.in/newsite/PrintRelease.aspx?relid=181467"
VERIFIED_2017_CROPS = {"jowar", "soybean", "maize"}

# domain -> provenance classification for every OTHER row's existing source_url.
_PRIMARY_DOMAINS = ("desagri.gov.in", "static.pib.gov.in", "pib.gov.in", "www.pib.gov.in", "cacp.dacnet.nic.in")
_SECONDARY_DOMAINS = ("business-standard.com", "agriculturepost.com", "onmanorama.com", "tribuneindia.com")


def classify_provenance(source_url: str) -> str:
    if not isinstance(source_url, str) or not source_url.strip():
        return ""
    if source_url.startswith("http"):
        if any(d in source_url for d in _PRIMARY_DOMAINS):
            return "primary"
        if any(d in source_url for d in _SECONDARY_DOMAINS):
            return "secondary"
        return "secondary"  # unknown http domain -- default to the more conservative label
    # plain-text citations (year=2025 rows) do name a specific PIB release; treat as primary.
    if "pib" in source_url.lower():
        return "primary"
    return "secondary"


def main() -> None:
    df = pd.read_csv(MSP_HISTORY_CSV)
    df["provenance"] = df["source_url"].apply(classify_provenance)

    mask = (df["year"] == 2017) & (df["crop"].isin(VERIFIED_2017_CROPS))
    if mask.sum() != 3:
        raise ValueError(f"expected exactly 3 rows (jowar/soybean/maize, 2017), found {mask.sum()}")
    df.loc[mask, "source_url"] = VERIFIED_2017_PRIMARY_URL
    df.loc[mask, "provenance"] = "primary_verified_v2"

    df.to_csv(MSP_HISTORY_CSV, index=False)
    print(f"Updated {MSP_HISTORY_CSV} ({mask.sum()} rows verified primary).")


if __name__ == "__main__":
    main()
