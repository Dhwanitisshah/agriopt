"""Per-crop economic/agronomic parameters for the optimizer.

Reuses the existing yield/price/reference inference APIs (Phase 1/2) --
no new modeling here, just assembly + unit conversion.

Water caveat (documented per the Phase 3 brief, see also docs/formulation.md):
water_m3_ha DEFAULTS to the FAO TM3 crop water NEED (total crop water
requirement over the growing season), not net irrigation requirement (which
would subtract effective rainfall). This overstates the irrigation water
actually drawn for rainfed/partially-rainfed crops -- treat WATER_BUDGET_M3
scenarios as a total-water-need budget, not a literal irrigation-supply
budget, UNLESS `water_basis="net_irrigation"` is passed (Phase 8 -- see
docs/water.md and agriopt.data.rainfall), in which case water_m3_ha instead
uses net irrigation requirement (need minus effective season rainfall).
"""
from __future__ import annotations

import pandas as pd

from agriopt.config import CROPS, MAIN_SEASON
from agriopt.data.rainfall import REGIONS, net_irrigation_mm
from agriopt.data.reference import cost_rs_per_ha, fert_total_kg_ha, load_reference, water_mm

# Phase 10 deploy-readiness: agriopt.models.price_model/yield_model both
# import xgboost/sklearn at module top. build_crop_params() (below) is the
# ONLY thing in this module that calls them, but it is itself imported (via
# agriopt.optim.solvers) by app/pipeline.py, which the Streamlit app DOES
# import at module level for its live NSGA-II/LP calls -- a module-level
# import here would transitively load xgboost/sklearn into the app's live
# process even though the app never calls build_crop_params itself (it only
# reads scripts/40_build_cache.py's precomputed cache). Deferred into the
# function body instead -- no logic change, import location only.

MM_TO_M3_PER_HA = 10.0  # 1mm over 1ha (10,000 m^2) = 10 m^3
PRICE_STD_LOOKBACK_MONTHS = 36

# Crops that occupy land through BOTH cropping seasons: sugarcane is a
# long-duration ("Whole Year") crop: MAIN_SEASON="Whole Year" isn't kharif or
# rabi, so it's handled here explicitly rather than via SEASON_MAP. Cotton
# and tur are also long-duration Kharif-sown crops that stay in the ground
# into the Rabi season in Maharashtra, so they're given the same treatment
# even though their MAIN_SEASON is "Kharif" -- this is a deliberate override
# of the MAIN_SEASON-based mapping below, not a data-driven one.
BOTH_SEASON_CROPS = {"sugarcane", "cotton", "tur"}

# MAIN_SEASON string -> optimizer season bucket. Every crop's MAIN_SEASON is
# either "Kharif", "Rabi", or (sugarcane) "Whole Year" -- "Whole Year" is
# handled via BOTH_SEASON_CROPS above, not this map, so this map only ever
# needs Kharif/Rabi. If a future crop's MAIN_SEASON were "Autumn" or
# "Summer", it would need an explicit decision added here (there isn't one
# today -- see the ValueError below).
SEASON_MAP = {"Kharif": "kharif", "Rabi": "rabi"}


def _ref_value(ref: pd.DataFrame, crop: str, col: str, default: float) -> float:
    """Optional crop_reference.csv column, with a default for older files."""
    if col not in ref.columns:
        return default
    v = ref.loc[ref["crop"] == crop, col]
    if v.empty or pd.isna(v.iloc[0]):
        return default
    return float(v.iloc[0])


def economic_row(
    crop: str,
    yield_per_cycle_qtl_ha: float,
    gross_price: float,
    cost_rs_per_qtl: float,
    water_m3_per_cycle: float,
    fert_kg_per_cycle: float,
    ref: pd.DataFrame,
) -> dict:
    """The ONE place per-hectare economics are assembled, so the live
    pipeline, the backtest and the cache patcher can't drift apart.

    Everything is returned per hectare per LAND-YEAR, which is what the
    optimizer's two-season land model actually allocates:

    * cost: cost_rs_per_qtl (Rs/quintal) x yield (qtl/ha) -> Rs/ha. Never pass
      a per-quintal cost in as a per-hectare one (the old backtest bug).
    * price: farm-gate price = gross (MSP/FRP/mandi) minus any per-quintal
      deduction the farmer never receives (sugarcane: harvesting & transport,
      `price_deduction_rs_per_qtl`).
    * cycle: crops whose cycle is longer than 12 months (sugarcane,
      `cycle_months`) tie the land up for longer than one land-year, so yield,
      water and fertilizer per cycle are scaled by 12/cycle_months. Cost is
      per quintal, so it scales with the annualized yield automatically.

    profit_ha == yield_qtl_ha * price - cost_ha holds exactly for the
    returned row, so downstream code (e.g. app price shocks) that recomputes
    profit from those three fields stays consistent."""
    cycle_months = _ref_value(ref, crop, "cycle_months", 12.0)
    deduction = _ref_value(ref, crop, "price_deduction_rs_per_qtl", 0.0)
    if cycle_months <= 0:
        raise ValueError(f"{crop}: cycle_months must be > 0, got {cycle_months}")
    per_year = 12.0 / cycle_months

    yield_qtl_ha = yield_per_cycle_qtl_ha * per_year
    price = gross_price - deduction
    cost_ha = cost_rs_per_qtl * yield_qtl_ha
    return {
        "crop": crop,
        "yield_qtl_ha": yield_qtl_ha,
        "price": price,
        "price_deduction_rs_per_qtl": deduction,
        "cycle_months": cycle_months,
        "cost_ha": cost_ha,
        "profit_ha": yield_qtl_ha * price - cost_ha,
        "water_m3_ha": water_m3_per_cycle * per_year,
        "fert_kg_ha": fert_kg_per_cycle * per_year,
    }


# Sugarcane has no mandi price series (FRP is administered), so its risk
# cannot come from price variance. It is NOT riskless though: its revenue
# still varies with yield. 0.097 is the coefficient of variation of
# Maharashtra sugarcane revenue (yield x FRP, 21 years, detrended) measured
# by agriopt.optim.risk.build_risk_inputs -- cache["risk"]["cv_table"].
# Previously profit_std_ha was hard-coded to 0, which made any shift into
# sugarcane look like de-risking in the app's "Profit risk" metric.
SUGARCANE_REVENUE_CV = 0.097


def profit_std_for(crop: str, row: dict, price_frame: pd.DataFrame | None) -> float:
    """Per-ha profit standard deviation (Rs/ha/yr) for one economic_row."""
    if crop == "sugarcane":
        return row["yield_qtl_ha"] * row["price"] * SUGARCANE_REVENUE_CV
    if price_frame is None:
        raise ValueError(f"{crop}: price_frame is required for non-sugarcane price std")
    sub = price_frame[price_frame["crop"] == crop].sort_values("month").tail(PRICE_STD_LOOKBACK_MONTHS)
    return row["yield_qtl_ha"] * float(sub["modal_price_rs_per_qtl"].std())


def seasons_occupied(crop: str) -> set[str]:
    """Which optimizer season bucket(s) ({"kharif", "rabi"}) a crop's
    hectares count against, for the land constraints."""
    if crop in BOTH_SEASON_CROPS:
        return {"kharif", "rabi"}
    main = MAIN_SEASON[crop]
    if main not in SEASON_MAP:
        raise ValueError(
            f"{crop}: MAIN_SEASON={main!r} is not Kharif/Rabi and {crop} is not in "
            f"BOTH_SEASON_CROPS -- add an explicit mapping in agriopt.optim.params."
        )
    return {SEASON_MAP[main]}


def build_crop_params(
    price_mode: str = "market",
    crops: list[str] = CROPS,
    verbose: bool = True,
    water_basis: str = "total_need",
    rainfall_scenario: str = "normal",
    region: str = "maharashtra",
) -> pd.DataFrame:
    """One row per crop: yield_qtl_ha, price, cost_ha, profit_ha,
    water_m3_ha, fert_kg_ha, seasons_occupied (set of {"kharif","rabi"}),
    profit_std_ha. Indexed by crop.

    water_basis="total_need" (default) uses the FAO TM3 total crop water
    requirement (water_mm(), unchanged from Phase 1-7 -- every existing
    caller reproduces byte-for-byte). water_basis="net_irrigation" (Phase 8)
    instead uses agriopt.data.rainfall.net_irrigation_mm(crop,
    rainfall_scenario, region=region), i.e. total need minus effective
    season rainfall -- see docs/water.md. `region` (Phase 8.1,
    agriopt.data.rainfall.REGIONS) selects WHICH region's own rainfall is
    used, when water_basis="net_irrigation" -- default "maharashtra" (the
    area-weighted state-wide average) reproduces every existing caller's
    behavior unchanged."""
    # Input validation must run BEFORE the model imports below: those need joblib/xgboost,
    # which the deployed (requirements-app.txt) stack does not have, so a bad argument must
    # raise ValueError there rather than ModuleNotFoundError. (Not asserts: they must also
    # survive `python -O`.)
    if price_mode not in ("market", "msp_floor"):
        raise ValueError(f"price_mode must be 'market' or 'msp_floor', got {price_mode!r}")
    if water_basis not in ("total_need", "net_irrigation"):
        raise ValueError(f"water_basis must be 'total_need' or 'net_irrigation', got {water_basis!r}")
    if region not in REGIONS:
        raise ValueError(f"region must be one of {REGIONS}, got {region!r}")

    from agriopt.models.price_model import expected_price, load_price_frame
    from agriopt.models.yield_model import expected_yield_saleable

    ref = load_reference()
    price_frame = load_price_frame()

    if verbose:
        print("Season occupancy:")

    rows = []
    for crop in crops:
        occ = seasons_occupied(crop)
        if verbose:
            print(f"  {crop:10s} MAIN_SEASON={MAIN_SEASON[crop]:11s} -> {sorted(occ)}")

        y = expected_yield_saleable(crop)
        yield_qtl_ha = y["value"]

        p = expected_price(crop, horizon=12, msp_floor=(price_mode == "msp_floor"))
        price = p["value_rs_per_qtl"]

        if water_basis == "net_irrigation":
            water_m3_cycle = net_irrigation_mm(crop, rainfall_scenario, ref, region) * MM_TO_M3_PER_HA
        else:
            water_m3_cycle = water_mm(crop, ref) * MM_TO_M3_PER_HA

        row = economic_row(
            crop,
            yield_per_cycle_qtl_ha=yield_qtl_ha,
            gross_price=price,
            cost_rs_per_qtl=cost_rs_per_ha(crop, 1.0, ref),
            water_m3_per_cycle=water_m3_cycle,
            fert_kg_per_cycle=fert_total_kg_ha(crop, ref),
            ref=ref,
        )
        row["seasons_occupied"] = occ
        row["profit_std_ha"] = profit_std_for(crop, row, price_frame)
        rows.append(row)

    return pd.DataFrame(rows).set_index("crop")
