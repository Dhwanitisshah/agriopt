"""Per-crop economic/agronomic parameters for the optimizer.

Reuses the existing yield/price/reference inference APIs (Phase 1/2) --
no new modeling here, just assembly + unit conversion.

Water caveat (documented per the Phase 3 brief, see also docs/formulation.md):
water_m3_ha uses the FAO TM3 crop water NEED (total crop water requirement
over the growing season), not net irrigation requirement (which would
subtract effective rainfall). This overstates the irrigation water actually
drawn for rainfed/partially-rainfed crops -- treat WATER_BUDGET_M3 scenarios
as a total-water-need budget, not a literal irrigation-supply budget.
"""
from __future__ import annotations

import pandas as pd

from agriopt.config import CROPS, MAIN_SEASON
from agriopt.data.reference import cost_rs_per_ha, fert_total_kg_ha, load_reference, water_mm
from agriopt.models.price_model import expected_price, load_price_frame
from agriopt.models.yield_model import expected_yield_saleable

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


def build_crop_params(price_mode: str = "market", crops: list[str] = CROPS, verbose: bool = True) -> pd.DataFrame:
    """One row per crop: yield_qtl_ha, price, cost_ha, profit_ha,
    water_m3_ha, fert_kg_ha, seasons_occupied (set of {"kharif","rabi"}),
    profit_std_ha. Indexed by crop."""
    assert price_mode in ("market", "msp_floor"), price_mode

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

        cost_ha = cost_rs_per_ha(crop, yield_qtl_ha, ref)
        profit_ha = yield_qtl_ha * price - cost_ha

        water_m3_ha = water_mm(crop, ref) * MM_TO_M3_PER_HA
        fert_kg_ha = fert_total_kg_ha(crop, ref)

        if crop == "sugarcane":
            # no mandi series -- FRP is a fixed administered price, no
            # month-to-month price variance to speak of for this metric.
            profit_std_ha = 0.0
        else:
            sub = price_frame[price_frame["crop"] == crop].sort_values("month").tail(PRICE_STD_LOOKBACK_MONTHS)
            price_std = float(sub["modal_price_rs_per_qtl"].std())
            profit_std_ha = yield_qtl_ha * price_std

        rows.append(
            {
                "crop": crop,
                "yield_qtl_ha": yield_qtl_ha,
                "price": price,
                "cost_ha": cost_ha,
                "profit_ha": profit_ha,
                "water_m3_ha": water_m3_ha,
                "fert_kg_ha": fert_kg_ha,
                "seasons_occupied": occ,
                "profit_std_ha": profit_std_ha,
            }
        )

    return pd.DataFrame(rows).set_index("crop")
