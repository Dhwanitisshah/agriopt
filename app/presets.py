"""Farmer-profile presets + app-wide scenario defaults -- centralized here
(no Streamlit import) so both app/components/sidebar.py (UI) and
scripts/40_build_cache.py (offline precompute) use the exact same
definitions. Demo-hardening Item 4: presets are precomputed into the cache
at these default settings; the app shows the cached result instantly when
the user's inputs exactly match one.
"""
from __future__ import annotations

PRESETS = {
    "Small rainfed (2 ha, tight water)": {"land_ha": 2, "water_mult": 0.7},
    "Medium mixed (5 ha, current water)": {"land_ha": 5, "water_mult": 1.0},
    "Large irrigated (15 ha, relaxed water)": {"land_ha": 15, "water_mult": 1.3},
    "Drought year (current land, water x0.6)": {"land_ha": None, "water_mult": 0.6},
}

DEFAULT_LAND_HA = 10.0  # used for the "Drought year" preset's land (no fixed land of its own)
DEFAULT_FOOD_SHARE_MIN = 0.3
DEFAULT_MAX_SHARE = 0.5
DEFAULT_PRICE_MODE = "market"
DEFAULT_PRIORITY = 0.5
DEFAULT_RISK_AVERSION = 0.5
DEFAULT_SUGARCANE_RISK_MODE = "conservative"
