"""Phase 8: effective rainfall and net irrigation requirement.

Source: IMD sub-divisional monthly rainfall, 1901-2015 (Kaggle
"rajanand/rainfall-in-india", data/raw/rainfall/rainfall in india 1901-2015.csv).
Verified to contain all 4 of Maharashtra's IMD meteorological subdivisions
(SUBDIVISION column values, monthly granularity, JAN..DEC columns):
KONKAN & GOA, MADHYA MAHARASHTRA, MATATHWADA (IMD's own spelling in this
dataset -- it means Marathwada; kept verbatim here as an ASSUMPTION so the
filter matches the raw data, and documented in docs/water.md), VIDARBHA.

See docs/water.md for the full write-up (methodology, citations, all
ASSUMPTIONs) -- this module is deliberately thin, following the same
loader-then-pure-function pattern as agriopt.data.reference.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd

from agriopt.config import RAINFALL_RAW_CSV
from agriopt.data.reference import load_reference, water_mm

MONTH_COLS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# IMD subdivision names exactly as they appear in this dataset's SUBDIVISION
# column ("MATATHWADA" is the dataset's own spelling of Marathwada).
MAHARASHTRA_SUBDIVISIONS = ["KONKAN & GOA", "MADHYA MAHARASHTRA", "MATATHWADA", "VIDARBHA"]

N_RECENT_YEARS = 30

# Season windows for net-irrigation purposes (ASSUMPTION, documented in
# docs/water.md): kharif = Jun-Oct, rabi = Nov-Mar, sugarcane = whole year
# (12 months), cotton/tur = Jun-Jan (long-duration Kharif-sown crops that
# stay in the ground into the Rabi season -- the SAME special-casing
# agriopt.optim.params.BOTH_SEASON_CROPS already applies for land-occupancy
# purposes, applied here in parallel for water-season purposes).
SEASON_WINDOW_MONTHS = {
    "kharif": ["JUN", "JUL", "AUG", "SEP", "OCT"],
    "rabi": ["NOV", "DEC", "JAN", "FEB", "MAR"],
    "whole_year": MONTH_COLS,
    "long_kharif": ["JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC", "JAN"],
}

# crop -> season window key. Mirrors agriopt.optim.params.seasons_occupied's
# MAIN_SEASON-based mapping, with the same BOTH_SEASON_CROPS-style override
# for sugarcane/cotton/tur.
CROP_SEASON_WINDOW = {
    "rice": "kharif",
    "wheat": "rabi",
    "jowar": "rabi",
    "soybean": "kharif",
    "cotton": "long_kharif",
    "sugarcane": "whole_year",
    "tur": "long_kharif",
    "maize": "kharif",
}


def load_rainfall_raw(path=RAINFALL_RAW_CSV) -> pd.DataFrame:
    """Raw IMD monthly rainfall rows for Maharashtra's 4 subdivisions only."""
    df = pd.read_csv(path)
    df = df[df["SUBDIVISION"].isin(MAHARASHTRA_SUBDIVISIONS)].copy()
    missing = set(MAHARASHTRA_SUBDIVISIONS) - set(df["SUBDIVISION"].unique())
    if missing:
        raise ValueError(f"rainfall data missing Maharashtra subdivisions: {missing}")
    return df


def _maharashtra_yearly(df: pd.DataFrame, n_years: int = N_RECENT_YEARS) -> pd.DataFrame:
    """Per-year Maharashtra monthly rainfall (mm), averaged UNWEIGHTED across
    the 4 subdivisions (per-subdivision area weights are not readily
    available in this dataset or its metadata, so an unweighted mean is used
    -- ASSUMPTION, documented in docs/water.md), restricted to the most
    recent `n_years` years present in the data. Returns a (year x month)
    DataFrame, index=year, columns=MONTH_COLS."""
    max_year = int(df["YEAR"].max())
    recent = df[df["YEAR"] > max_year - n_years]
    state_by_year = recent.groupby("YEAR")[MONTH_COLS].mean()
    return state_by_year


@lru_cache(maxsize=1)
def monthly_normals(n_years: int = N_RECENT_YEARS) -> pd.Series:
    """Maharashtra monthly rainfall normal (mm), mean over the most recent
    `n_years` years, index=MONTH_COLS."""
    df = load_rainfall_raw()
    yearly = _maharashtra_yearly(df, n_years)
    return yearly.mean(axis=0)


@lru_cache(maxsize=1)
def monthly_dry_year(n_years: int = N_RECENT_YEARS) -> pd.Series:
    """Maharashtra monthly rainfall at the 20th percentile across years (a
    drought-scenario proxy), over the same most-recent `n_years` years,
    index=MONTH_COLS."""
    df = load_rainfall_raw()
    yearly = _maharashtra_yearly(df, n_years)
    return yearly.quantile(0.20, axis=0)


def effective_rainfall_mm(p_mm: float | np.ndarray) -> float | np.ndarray:
    """USDA-SCS effective rainfall formula, as used in FAO CROPWAT (FAO
    Irrigation and Drainage Paper 56 / CROPWAT methodology; also FAO Irrigation
    and Drainage Paper 25, "Effective Rainfall in Irrigated Agriculture"):

        Peff = P * (125 - 0.2*P) / 125   for P <= 250 mm
        Peff = 125 + 0.1*P               for P > 250 mm

    where P is monthly rainfall (mm). Vectorized over arrays or scalars."""
    p = np.asarray(p_mm, dtype=float)
    peff = np.where(p <= 250.0, p * (125.0 - 0.2 * p) / 125.0, 125.0 + 0.1 * p)
    return float(peff) if np.isscalar(p_mm) or np.ndim(p_mm) == 0 else peff


def effective_rainfall_monthly(scenario: str = "normal") -> pd.Series:
    """Effective rainfall (mm) per month, index=MONTH_COLS, for
    scenario="normal" (30-year mean) or "dry" (20th-percentile year)."""
    assert scenario in ("normal", "dry"), scenario
    monthly = monthly_normals() if scenario == "normal" else monthly_dry_year()
    return monthly.apply(effective_rainfall_mm)


def season_effective_rainfall_mm(crop: str, scenario: str = "normal") -> float:
    """Sum of effective rainfall (mm) over `crop`'s season window months
    (see CROP_SEASON_WINDOW), for the given rainfall scenario."""
    peff = effective_rainfall_monthly(scenario)
    window_key = CROP_SEASON_WINDOW[crop]
    months = SEASON_WINDOW_MONTHS[window_key]
    return float(peff.loc[months].sum())


def net_irrigation_mm(crop: str, scenario: str = "normal", ref: pd.DataFrame | None = None) -> float:
    """Net irrigation requirement (mm) = max(0, water_need_mm - Peff_season_mm),
    where water_need_mm is the FAO TM3 total crop water need midpoint
    (agriopt.data.reference.water_mm) and Peff_season_mm is the sum of
    effective rainfall over the crop's season window (normal or dry-year
    monthly values, per `scenario`)."""
    if ref is None:
        ref = load_reference()
    need = water_mm(crop, ref)
    peff_season = season_effective_rainfall_mm(crop, scenario)
    return max(0.0, need - peff_season)


def rainfall_water_table(crops: list[str], ref: pd.DataFrame | None = None) -> pd.DataFrame:
    """crop, water need (mm), Peff normal (mm), net irrigation normal (mm),
    net irrigation dry (mm) -- the Phase 8 step-1 summary table."""
    if ref is None:
        ref = load_reference()
    rows = []
    for crop in crops:
        need = water_mm(crop, ref)
        peff_normal = season_effective_rainfall_mm(crop, "normal")
        net_normal = max(0.0, need - peff_normal)
        net_dry = net_irrigation_mm(crop, "dry", ref)
        rows.append(
            {
                "crop": crop,
                "water_need_mm": need,
                "peff_normal_mm": peff_normal,
                "net_irrigation_normal_mm": net_normal,
                "net_irrigation_dry_mm": net_dry,
            }
        )
    return pd.DataFrame(rows).set_index("crop")
