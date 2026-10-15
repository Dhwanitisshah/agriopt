"""Phase 8 (+ Phase 8.1): effective rainfall and net irrigation requirement.

Source: IMD sub-divisional monthly rainfall, 1901-2015 (Kaggle
"rajanand/rainfall-in-india", data/raw/rainfall/rainfall in india 1901-2015.csv).
Verified to contain all 4 of Maharashtra's IMD meteorological subdivisions
(SUBDIVISION column values, monthly granularity, JAN..DEC columns):
KONKAN & GOA, MADHYA MAHARASHTRA, MATATHWADA (IMD's own spelling in this
dataset -- it means Marathwada; kept verbatim here as an ASSUMPTION so the
filter matches the raw data, and documented in docs/water.md), VIDARBHA.

Phase 8.1 additions (see docs/water.md section "Phase 8.1" for the full
write-up, citations, and ASSUMPTIONs):
  - The Maharashtra state-wide rainfall average is now AREA-WEIGHTED across
    the 4 subdivisions (SUBDIVISION_AREA_SQKM), using official subdivision
    areas sourced from IITM (Indian Institute of Tropical Meteorology, Pune
    -- primary data source IMD), not the Phase 8 unweighted mean.
  - `region` parameter (REGIONS) added throughout: every rainfall/net
    irrigation function can now be computed for a single subdivision
    ("konkan", "madhya_maharashtra", "marathwada", "vidarbha") instead of
    always defaulting to the state-wide "maharashtra" average.
  - RICE_EXTRA_MM: a citable FAO figure for puddled-rice land
    preparation/saturation water, applied ONLY inside net_irrigation_mm (not
    to water_mm()/the "total_need" basis).

Economics-review revision (Task 10):
  - NET IRRIGATION IS A MONTHLY BALANCE. It used to be max(0, season need -
    sum of the season's monthly effective rain), which lets a July surplus
    "cover" a September deficit. Rain that exceeds a month's crop need runs
    off or drains; it cannot be spent later. Net irrigation is now the sum
    over the season's months of max(0, monthly need - monthly effective
    rain). The FAO TM3 seasonal need has no monthly profile in this repo, so it
    is spread UNIFORMLY over the season window's months (an ASSUMPTION; no
    crop-coefficient staging data is invented).
  - THE "DRY" SCENARIO IS A REAL YEAR. It used to take the 20th percentile of
    each month independently, a composite in which every month is
    simultaneously unusually dry -- drier than almost any real year. It is now
    the observed year whose usable rain (summed over the 8 decision crops'
    season windows) is nearest the 20th percentile of the 30 years, with that
    year's own monthly values.

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

# Phase 8.1: official subdivision areas (sq km), CITED (not guessed/estimated
# -- see docs/water.md "Phase 8.1" section 1 for the full citation and the
# verbatim source lines this was read from):
#
# Source: IITM (Indian Institute of Tropical Meteorology, Pune -- an
# autonomous institute under India's Ministry of Earth Sciences; primary data
# source IMD) "IITM Indian regional/subdivisional Monthly Rainfall data set"
# metadata file iitm-subdivrf.txt, https://www.tropmet.res.in/data/data-archival/rain/iitm-subdivrf.txt
# (documented at https://www.tropmet.res.in/data/data-archival/rain/Readme.pdf,
# landing page https://www.tropmet.res.in/static_pages.php?page_id=53), which
# states its own header format is "Numerical Code of the subdivision; Name of
# the subdivision; Area of the subdivision in sq.km.; Percentage of the area
# out of the total area of the country; ...". Fetched header lines (verbatim):
#   "146 23.KONKAN AND GOA         SUBDIVISION  Area   34095 SQ.KM 1.18 PER   5 STN"
#   "146 24.MADHYA MAHARASHTRA     SUBDIVISION  Area  115306 SQ.KM 4.00 PER   9 STN"
#   "146 25.MARATHWADA             SUBDIVISION  Area   64525 SQ.KM 2.24 PER   5 STN"
#   "146 26.VIDARBHA               SUBDIVISION  Area   97536 SQ.KM 3.39 PER   8 STN"
# ("MARATHWADA" is this source's spelling; mapped here to the Kaggle
# dataset's "MATATHWADA" key, which the docstring above already documents as
# the same subdivision under a dataset typo.) Sum = 311,462 sq km, close to
# (slightly above, since Konkan & Goa includes Goa state's ~3,702 sq km)
# Maharashtra's actual state area of ~307,713 sq km -- consistent with these
# being genuine subdivision-boundary areas, not an independent/incompatible
# figure.
SUBDIVISION_AREA_SQKM = {
    "KONKAN & GOA": 34095.0,
    "MADHYA MAHARASHTRA": 115306.0,
    "MATATHWADA": 64525.0,
    "VIDARBHA": 97536.0,
}

# Phase 8.1: region key (as used by agriopt.optim.problem.Scenario.region and
# threaded through agriopt.optim.params.build_crop_params) -> this module's
# internal SUBDIVISION name. "maharashtra" is not a single subdivision -- it's
# the area-weighted combination of all 4 (see _regional_yearly).
REGION_TO_SUBDIVISION = {
    "konkan": "KONKAN & GOA",
    "madhya_maharashtra": "MADHYA MAHARASHTRA",
    "marathwada": "MATATHWADA",
    "vidarbha": "VIDARBHA",
}
REGIONS = ("maharashtra",) + tuple(REGION_TO_SUBDIVISION.keys())

# Phase 8.1c: FAO Irrigation Water Management Training Manual No. 3, Chapter
# 4 "Determination of the Irrigation Schedule for Paddy Rice"
# (https://www.fao.org/4/t7202e/t7202e07.htm) gives the standing-water-layer
# irrigation balance for puddled/transplanted rice as
#   IN = ET_crop + SAT + PERC + WL - Peff
# where SAT ("the amount of water needed to saturate the root zone") = 200mm
# (a single pre-season land-preparation/puddling requirement, roughly
# soil-independent) and PERC (percolation/seepage) = 2-8 mm/day depending on
# soil type (60-240 mm/month) -- i.e. NOT a single point figure, since it is
# highly soil-type dependent and this repo has no per-field soil data.
# water_mm()/FAO TM3's total-need figure (agriopt.data.reference.water_mm)
# already covers ET_crop; it does NOT cover SAT, PERC, or WL (standard FAO
# TM3 caveat for puddled paddy). This constant adds ONLY the citable,
# (relatively) soil-independent SAT figure to rice's NET IRRIGATION
# requirement (not to water_mm()/the "total_need" basis, and not to any
# other crop) -- see net_irrigation_mm() below. PERC/WL are explicitly NOT
# added: no single citable figure exists for them without inventing a soil
# assumption this repo has no data to support -- documented LIMITATION, not
# a blocker (see docs/water.md "Phase 8.1" section 3).
RICE_EXTRA_MM = 200.0

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


def area_weights() -> dict[str, float]:
    """Phase 8.1: SUBDIVISION_AREA_SQKM normalized to sum to 1.0 -- the
    weights used to combine the 4 subdivisions into the "maharashtra"
    state-wide average (see SUBDIVISION_AREA_SQKM's citation above)."""
    total = sum(SUBDIVISION_AREA_SQKM.values())
    return {name: area / total for name, area in SUBDIVISION_AREA_SQKM.items()}


def _regional_yearly(df: pd.DataFrame, region: str, n_years: int = N_RECENT_YEARS) -> pd.DataFrame:
    """Per-year monthly rainfall (mm) for `region`, restricted to the most
    recent `n_years` years present in the data. Returns a (year x month)
    DataFrame, index=year, columns=MONTH_COLS.

    region="maharashtra" (Phase 8.1): AREA-WEIGHTED combination of the 4
    subdivisions (weights = area_weights()), replacing Phase 8's unweighted
    mean now that official subdivision areas have been found (see
    SUBDIVISION_AREA_SQKM). Any other region key is a single IMD subdivision
    (REGION_TO_SUBDIVISION), used as-is (no weighting needed -- it already
    is that subdivision's own reported rainfall)."""
    assert region in REGIONS, region
    max_year = int(df["YEAR"].max())
    recent = df[df["YEAR"] > max_year - n_years]

    if region != "maharashtra":
        subdivision = REGION_TO_SUBDIVISION[region]
        return recent[recent["SUBDIVISION"] == subdivision].set_index("YEAR")[MONTH_COLS]

    weighted_sum = None
    for subdivision, weight in area_weights().items():
        sub_yearly = recent[recent["SUBDIVISION"] == subdivision].set_index("YEAR")[MONTH_COLS]
        term = sub_yearly * weight
        weighted_sum = term if weighted_sum is None else weighted_sum.add(term, fill_value=0.0)
    return weighted_sum


@lru_cache(maxsize=None)
def monthly_normals(region: str = "maharashtra", n_years: int = N_RECENT_YEARS) -> pd.Series:
    """Monthly rainfall normal (mm) for `region` (REGIONS; default
    "maharashtra", area-weighted -- see _regional_yearly), mean over the most
    recent `n_years` years, index=MONTH_COLS."""
    df = load_rainfall_raw()
    yearly = _regional_yearly(df, region, n_years)
    return yearly.mean(axis=0)


DRY_YEAR_QUANTILE = 0.20


def usable_rain_by_year(region: str = "maharashtra", n_years: int = N_RECENT_YEARS) -> pd.Series:
    """Per observed year, the effective rain the 8 decision crops could actually
    use, summed over crops: per crop and season month, min(monthly need, that
    month's effective rain). Uses each crop's own season window and the uniform
    monthly-need assumption of net_irrigation_mm. Because summed deficit + summed
    usable rain = summed need (a constant), ranking years by usable rain is
    exactly the reverse of ranking them by total irrigation shortfall."""
    ref = load_reference()
    yearly = _yearly_effective_rainfall(region, n_years)
    total = pd.Series(0.0, index=yearly.index)
    for crop, window_key in CROP_SEASON_WINDOW.items():
        months = SEASON_WINDOW_MONTHS[window_key]
        need_month = water_mm(crop, ref) / len(months)
        total = total + np.minimum(need_month, yearly[months]).sum(axis=1)
    return total


@lru_cache(maxsize=None)
def dry_year(region: str = "maharashtra", n_years: int = N_RECENT_YEARS) -> int:
    """The observed year that stands for a "dry" year in `region`: of the most
    recent `n_years` years, the one whose usable rain (see usable_rain_by_year)
    is nearest the 20th percentile. A REAL year, so its months are mutually
    consistent (a poor July is not paired with a 20th-percentile September),
    unlike the per-month percentile composite this replaces.

    Why usable rain and not the June-September total: under a monthly balance
    the shortfall of kharif crops sits in the shoulder months (June, October),
    so the monsoon total is a poor guide to which year is thirsty -- a year
    ranked dry on the JJAS total can need LESS irrigation than the average
    year."""
    usable = usable_rain_by_year(region, n_years)
    target = float(usable.quantile(DRY_YEAR_QUANTILE))
    return int((usable - target).abs().idxmin())


@lru_cache(maxsize=None)
def monthly_dry_year(region: str = "maharashtra", n_years: int = N_RECENT_YEARS) -> pd.Series:
    """Monthly rainfall (mm) of the real "dry" year (see dry_year) for `region`
    (REGIONS), index=MONTH_COLS."""
    df = load_rainfall_raw()
    yearly = _regional_yearly(df, region, n_years)
    year = dry_year(region, n_years)
    out = yearly.loc[year].copy()
    out.name = year
    return out


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


def effective_rainfall_monthly(scenario: str = "normal", region: str = "maharashtra") -> pd.Series:
    """Effective rainfall (mm) per month, index=MONTH_COLS, for
    scenario="normal" (30-year mean) or "dry" (20th-percentile year), for
    `region` (REGIONS; default "maharashtra", area-weighted)."""
    assert scenario in ("normal", "dry"), scenario
    monthly = monthly_normals(region) if scenario == "normal" else monthly_dry_year(region)
    return monthly.apply(effective_rainfall_mm)


def season_effective_rainfall_mm(crop: str, scenario: str = "normal", region: str = "maharashtra") -> float:
    """Sum of effective rainfall (mm) over `crop`'s season window months
    (see CROP_SEASON_WINDOW), for the given rainfall scenario and region. This
    is the rain that FALLS and counts as effective -- not necessarily the rain
    the crop can use (see season_rain_used_mm)."""
    peff = effective_rainfall_monthly(scenario, region)
    window_key = CROP_SEASON_WINDOW[crop]
    months = SEASON_WINDOW_MONTHS[window_key]
    return float(peff.loc[months].sum())


@lru_cache(maxsize=None)
def _yearly_effective_rainfall(region: str, n_years: int = N_RECENT_YEARS) -> pd.DataFrame:
    """Effective rainfall (mm), year x month, from each observed year's own monthly rain."""
    yearly = _regional_yearly(load_rainfall_raw(), region, n_years)
    return pd.DataFrame(effective_rainfall_mm(yearly.to_numpy(dtype=float)), index=yearly.index, columns=yearly.columns)


def _monthly_balance(crop: str, scenario: str, ref: pd.DataFrame, region: str) -> tuple[float, float]:
    """(total deficit, total effective rain actually used) over the season, in mm.

    The FAO TM3 seasonal need is spread uniformly over the window's months;
    each month's deficit is max(0, need_m - Peff_m) and the rain used is
    min(need_m, Peff_m). A surplus in one month is lost, not carried forward.

    scenario="dry": the balance of the one real dry year (see dry_year).
    scenario="normal": the AVERAGE of the balance over the 30 observed years.
    Averaging the yearly balances, rather than balancing the 30-year monthly
    mean rainfall, matters: the deficit is convex in rainfall, so the smooth
    mean year hides the months that fall short and would understate irrigation
    need (and could even make a real dry year look no thirstier than normal)."""
    months = SEASON_WINDOW_MONTHS[CROP_SEASON_WINDOW[crop]]
    need_month = water_mm(crop, ref) / len(months)
    yearly = _yearly_effective_rainfall(region)
    peff = yearly.loc[[dry_year(region)], months] if scenario == "dry" else yearly[months]
    peff = peff.to_numpy(dtype=float)
    deficit = np.maximum(need_month - peff, 0.0).sum(axis=1).mean()
    used = np.minimum(need_month, peff).sum(axis=1).mean()
    return float(deficit), float(used)


def season_rain_used_mm(crop: str, scenario: str = "normal", ref: pd.DataFrame | None = None, region: str = "maharashtra") -> float:
    """Effective rainfall (mm) the crop can actually use under the monthly
    balance: per month, at most that month's share of the seasonal need."""
    return _monthly_balance(crop, scenario, load_reference() if ref is None else ref, region)[1]


def net_irrigation_mm(
    crop: str,
    scenario: str = "normal",
    ref: pd.DataFrame | None = None,
    region: str = "maharashtra",
) -> float:
    """Net irrigation requirement (mm) = sum over the crop's season months of
    max(0, monthly_need - monthly_effective_rain), where monthly_need is the
    FAO TM3 total crop water need midpoint (agriopt.data.reference.water_mm)
    spread uniformly over the season window (ASSUMPTION -- no crop-coefficient
    profile is available), and effective rain is that month's USDA-SCS
    effective rainfall in `region` for `scenario` ("normal" = 30-year monthly
    mean, applied year by year and averaged; "dry" = the real year nearest the
    20th percentile of monsoon rainfall, see dry_year).

    Why a monthly balance: the earlier season-level form,
    max(0, need - sum of monthly Peff), let a July surplus cover a September
    deficit. Rain beyond a month's need runs off or drains, so it cannot.

    Phase 8.1c: for crop="rice" only, adds RICE_EXTRA_MM -- the FAO-cited
    puddled-rice land-preparation/saturation water requirement, which
    water_mm()/the base "need" figure does NOT cover (standard FAO TM3
    caveat for paddy) and which is NOT offset by season rainfall (it is a
    pre-season requirement, applied regardless of `scenario`). This does
    NOT change water_mm() or the "total_need" water_basis anywhere -- only
    net_irrigation_mm's own return value."""
    if ref is None:
        ref = load_reference()
    net, _ = _monthly_balance(crop, scenario, ref, region)
    if crop == "rice":
        net += RICE_EXTRA_MM
    return net


def rainfall_water_table(
    crops: list[str], ref: pd.DataFrame | None = None, region: str = "maharashtra"
) -> pd.DataFrame:
    """crop, water need (mm), Peff normal (mm), rain actually usable under the
    monthly balance (mm), net irrigation normal (mm), net irrigation dry (mm)
    -- the Phase 8 step-1 summary table, for `region` (REGIONS; default
    "maharashtra")."""
    if ref is None:
        ref = load_reference()
    rows = []
    for crop in crops:
        need = water_mm(crop, ref)
        peff_normal = season_effective_rainfall_mm(crop, "normal", region)
        net_normal = net_irrigation_mm(crop, "normal", ref, region)
        net_dry = net_irrigation_mm(crop, "dry", ref, region)
        rows.append(
            {
                "crop": crop,
                "water_need_mm": need,
                "peff_normal_mm": peff_normal,
                "rain_used_normal_mm": season_rain_used_mm(crop, "normal", ref, region),
                "net_irrigation_normal_mm": net_normal,
                "net_irrigation_dry_mm": net_dry,
            }
        )
    return pd.DataFrame(rows).set_index("crop")
