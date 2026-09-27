"""Farmer-profile presets + app-wide scenario defaults -- centralized here
(no Streamlit import) so both app/components/sidebar.py (UI) and
scripts/40_build_cache.py (offline precompute) use the exact same
definitions. Demo-hardening Item 4: presets are precomputed into the cache
at these default settings; the app shows the cached result instantly when
the user's inputs exactly match one.
"""
from __future__ import annotations

PRESETS = {
    "Small rainfed (2 ha, tight water)": {
        "land_ha": 2,
        "water_mult": 0.7,
        "region": "maharashtra",
        "water_basis": "net_irrigation",
        "rainfall_scenario": "normal",
    },
    "Medium mixed (5 ha, current water)": {
        "land_ha": 5,
        "water_mult": 1.0,
        "region": "maharashtra",
        "water_basis": "net_irrigation",
        "rainfall_scenario": "normal",
    },
    "Large irrigated (15 ha, relaxed water)": {
        "land_ha": 15,
        "water_mult": 1.3,
        "region": "maharashtra",
        "water_basis": "net_irrigation",
        "rainfall_scenario": "normal",
    },
    "Drought year (current land, water x0.6)": {
        "land_ha": None,
        "water_mult": 0.6,
        "region": "maharashtra",
        "water_basis": "net_irrigation",
        "rainfall_scenario": "normal",
    },
    # Phase 10: 5th preset -- a Marathwada drought-farmer profile exercising
    # the Phase 8/8.1 region + water_basis + rainfall_scenario axes together
    # (region="marathwada", water_basis="net_irrigation",
    # rainfall_scenario="dry"), precomputed into scripts/40_build_cache.py's
    # preset_results the same way as the other 4.
    "Marathwada drought farmer (net irrigation, dry year)": {
        "land_ha": 5,
        "water_mult": 1.0,
        "region": "marathwada",
        "water_basis": "net_irrigation",
        "rainfall_scenario": "dry",
    },
}

DEFAULT_LAND_HA = 10.0  # used for the "Drought year" preset's land (no fixed land of its own)
DEFAULT_FOOD_SHARE_MIN = 0.3
DEFAULT_MAX_SHARE = 0.5
DEFAULT_PRICE_MODE = "market"
DEFAULT_PRIORITY = 0.5
DEFAULT_RISK_AVERSION = 0.5
DEFAULT_SUGARCANE_RISK_MODE = "conservative"
# Phase 10: the APP's own default water basis is "net_irrigation" (a
# deliberate change from Scenario.water_basis's own class-level default of
# "total_need", which exists only for backward-compatible reproducibility of
# pre-Phase-8 scripts/results -- see src/agriopt/optim/problem.py). Every
# sidebar control and preset in the APP defaults to net_irrigation from here
# on; scripts that construct Scenario() directly and don't pass water_basis
# are unaffected (they still get "total_need").
DEFAULT_WATER_BASIS = "net_irrigation"
DEFAULT_REGION = "maharashtra"
DEFAULT_RAINFALL_SCENARIO = "normal"

REGION_LABELS = {
    "maharashtra": "Maharashtra (area-weighted, state-wide)",
    "konkan": "Konkan",
    "madhya_maharashtra": "Madhya Maharashtra",
    "marathwada": "Marathwada",
    "vidarbha": "Vidarbha",
}
WATER_BASIS_LABELS = {
    "net_irrigation": "Net irrigation (need minus effective rainfall) — default",
    "total_need": "Total crop water need (FAO TM3, no rainfall offset)",
}
