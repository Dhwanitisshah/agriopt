"""Single source of truth for AgriOpt: state, crops, name mappings, paths, constants.

CROP_NAME_MAP was filled by inspecting the raw datasets directly (df["Crop"].unique()
for yield, df["Commodity"].unique() for the Kaggle price dataset, and the CEDA
/agmarknet/commodities response for the CEDA price source) -- see
reports/eda/eda_report.md and reports/eda/price_report.md for the audit that
produced these values. Do not edit without re-running that inspection.

Phase 0.5 note: onion was dropped (1 Maharashtra yield row total) and replaced
with maize, which had the most Maharashtra rows and year coverage among the
candidates (Maize, Groundnut, Bajra, Gram) -- see eda_report.md "8th crop
selection".
"""
from __future__ import annotations

from pathlib import Path

# --- Paths -------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = REPO_ROOT / "data" / "raw"
DATA_PROCESSED = REPO_ROOT / "data" / "processed"
DATA_REFERENCE = REPO_ROOT / "data" / "reference"
REPORTS_EDA = REPO_ROOT / "reports" / "eda"
REPORTS_RESULTS = REPO_ROOT / "reports" / "results"
MODELS_DIR = REPO_ROOT / "models"

YIELD_RAW_CSV = DATA_RAW / "yield" / "crop_yield.csv"
PRICE_RAW_CSV = DATA_RAW / "prices" / "Agriculture_price_dataset.csv"
CEDA_RAW_DIR = DATA_RAW / "prices_ceda"

YIELD_CLEAN_PARQUET = DATA_PROCESSED / "yield_clean.parquet"
PRICES_MONTHLY_PARQUET = DATA_PROCESSED / "prices_monthly.parquet"

CROP_REFERENCE_CSV = DATA_REFERENCE / "crop_reference.csv"

YIELD_MODEL_PATH = MODELS_DIR / "yield_best.joblib"
YIELD_MODEL_METADATA_PATH = MODELS_DIR / "yield_best.json"
# yield_best is refit on ALL years (1997-2020) for inference; yield_eval is
# the <=2015 model the Phase 1 metrics were computed on, kept for reference.
YIELD_EVAL_MODEL_PATH = MODELS_DIR / "yield_eval.joblib"
YIELD_EVAL_METADATA_PATH = MODELS_DIR / "yield_eval.json"

PRICE_MODEL_PATH = MODELS_DIR / "price_best_h12.joblib"
PRICE_MODEL_METADATA_PATH = MODELS_DIR / "price_best_h12.json"

ENV_FILE = REPO_ROOT / ".env"

# --- Domain scope --------------------------------------------------------
STATE = "Maharashtra"

CROPS = [
    "rice",
    "wheat",
    "jowar",
    "soybean",
    "cotton",
    "sugarcane",
    "tur",
    "maize",
]

# Food crops for the "food security" optimization constraint (>= 30% of land).
# Cereals/pulses among the 8 target crops: rice, wheat, jowar, tur are the
# original set; maize (a cereal) joins them after the onion -> maize swap.
FOOD_CROPS = ["rice", "wheat", "jowar", "tur", "maize"]

# canonical crop -> season with the most Maharashtra rows in yield_clean.parquet
# (ties broken by mean area_ha, i.e. the season where more land is actually
# under that crop -- row count alone ties rice Kharif/Summer 23-23 and jowar
# Kharif/Rabi 23-23; area breaks both decisively, and confirms Maharashtra's
# well-known rabi-jowar dominance rather than defaulting to kharif for every
# crop). Used by yield_model.expected_yield_saleable().
MAIN_SEASON = {
    "rice": "Kharif",
    "wheat": "Rabi",
    "jowar": "Rabi",
    "soybean": "Kharif",
    "cotton": "Kharif",
    "sugarcane": "Whole Year",
    "tur": "Kharif",
    "maize": "Kharif",
}

# canonical crop -> exact name in each raw/external dataset.
#
# yield: exact value of df["Crop"] in data/raw/yield/crop_yield.csv (Kaggle
#        "crop-yield-in-indian-states-dataset").
# kaggle_price: exact value of df["Commodity"] in
#        data/raw/prices/Agriculture_price_dataset.csv (Kaggle
#        "indian-agricultural-mandi-prices-20232025"), or None if the crop is
#        not present in that dataset for any state. This is a SECONDARY price
#        source (see price_data.py) -- the dataset only has 5 commodities
#        total (Onion, Potato, Rice, Tomato, Wheat), so most target crops get
#        None here.
# ceda_commodity: exact value of commodity_name from the CEDA Agmarknet
#        /agmarknet/commodities endpoint (https://api.ceda.ashoka.edu.in/v1),
#        the PRIMARY price source (see ceda_client.py, scripts/03_fetch_ceda_prices.py).
#        None for sugarcane, which has no mandi series -- see "SUGARCANE" note
#        in crop_reference.csv (admin/FRP price instead).
CROP_NAME_MAP = {
    "rice": {"yield": "Rice", "kaggle_price": "Rice", "ceda_commodity": "Paddy(Dhan)(Common)"},
    "wheat": {"yield": "Wheat", "kaggle_price": "Wheat", "ceda_commodity": "Wheat"},
    "jowar": {"yield": "Jowar", "kaggle_price": None, "ceda_commodity": "Jowar(Sorghum)"},
    "soybean": {"yield": "Soyabean", "kaggle_price": None, "ceda_commodity": "Soyabean"},
    "cotton": {"yield": "Cotton(lint)", "kaggle_price": None, "ceda_commodity": "Cotton"},
    "sugarcane": {"yield": "Sugarcane", "kaggle_price": None, "ceda_commodity": None},
    "tur": {"yield": "Arhar/Tur", "kaggle_price": None, "ceda_commodity": "Arhar (Tur/Red Gram)(Whole)"},
    "maize": {"yield": "Maize", "kaggle_price": None, "ceda_commodity": "Maize"},
}

# --- Train/test split + reproducibility ----------------------------------
TRAIN_END_YEAR = 2015
TEST_START_YEAR = 2016
RANDOM_SEED = 42

# --- CEDA Agmarknet API (primary price source) ----------------------------
CEDA_BASE_URL = "https://api.ceda.ashoka.edu.in/v1"
# census_state_id for Maharashtra, resolved from GET /agmarknet/geographies
# (census_state_name == "Maharashtra") -- see scripts/03_fetch_ceda_prices.py,
# which re-resolves this dynamically rather than trusting this constant blindly.
CEDA_MAHARASHTRA_STATE_ID = 27
# Earliest observed data point (Wheat, Maharashtra) is 2001-03-30; 2000 is used
# as a safe floor so no crop's early history is missed.
CEDA_START_YEAR = 2000
CEDA_END_DATE = "2026-08-31"
# The live API enforces 40 requests/rolling-hour (RateLimit-Policy response
# header) -- NOT a requests/sec figure, and NOT a 1-year request-window limit
# (verified: single requests spanning multiple years succeed). Chunking by
# calendar year (27 requests/crop) blows the hourly budget; multi-year chunks
# keep the 7-crop full-history fetch to ~4 requests/crop (~28 total).
CEDA_CHUNK_YEARS = 7

# --- Unit conversion: dataset Yield -> quintals of MARKETED product per ha ---
# See docs/units.md for the full reasoning and reports/eda/eda_report.md
# "Unit audit" for the empirical ratio = Yield / (Production/Area) check that
# this is based on. All factors below are flagged ASSUMPTION because the
# Kaggle yield dataset does not document its units, and the audit (ratio ~1
# for every target crop) can only confirm internal Yield/Production/Area
# self-consistency -- it cannot independently prove which real-world quantity
# (paddy vs milled rice, lint bales vs tonnes) "Yield" represents.

# ASSUMPTION -- verify before paper: dataset Yield for rice is MILLED RICE
# (t/ha), not paddy. Standard Indian milling outturn ratio: paddy * 0.67 = rice.
RICE_OUTTURN = 0.67

# ASSUMPTION -- verify before paper: dataset Yield for cotton is LINT COTTON
# expressed in BALES/ha (not tonnes/ha) -- the Production magnitude (median
# ~4.6M for Maharashtra alone) is only plausible as bales, not tonnes, given
# India's total national lint production is on the order of 30-34M bales/yr.
# Standard bale weight and ginning (lint:kapas) outturn ratio:
GINNING_OUTTURN = 0.34
BALE_KG = 170


def _rice_to_qtl_paddy(yield_t_ha: float) -> float:
    """Milled rice t/ha -> paddy quintal/ha (marketed product = paddy)."""
    paddy_t_ha = yield_t_ha / RICE_OUTTURN
    return paddy_t_ha * 10


def _cotton_to_qtl_kapas(yield_bales_ha: float) -> float:
    """Lint cotton bales/ha -> kapas (raw seed cotton) quintal/ha (marketed product = kapas)."""
    lint_kg_ha = yield_bales_ha * BALE_KG
    kapas_kg_ha = lint_kg_ha / GINNING_OUTTURN
    return kapas_kg_ha / 100


def _tonnes_to_qtl(yield_t_ha: float) -> float:
    """tonnes/ha -> quintal/ha, no product-form conversion."""
    return yield_t_ha * 10


# canonical crop -> callable(dataset Yield value) -> quintals of marketed
# product per ha. Every crop in CROPS must have an entry (enforced by
# tests/test_smoke.py).
YIELD_TO_SALEABLE_QTL_PER_HA = {
    "rice": _rice_to_qtl_paddy,
    "wheat": _tonnes_to_qtl,
    "jowar": _tonnes_to_qtl,
    "soybean": _tonnes_to_qtl,
    "cotton": _cotton_to_qtl_kapas,
    "sugarcane": _tonnes_to_qtl,
    "tur": _tonnes_to_qtl,
    "maize": _tonnes_to_qtl,
}
