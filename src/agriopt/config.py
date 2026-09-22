"""Single source of truth for AgriOpt: state, crops, name mappings, paths, constants.

CROP_NAME_MAP was filled by inspecting the raw datasets directly (df["Crop"].unique()
for yield, df["Commodity"].unique() for price) -- see reports/eda/eda_report.md and
reports/eda/price_report.md for the audit that produced these values. Do not edit
without re-running that inspection.
"""
from __future__ import annotations

from pathlib import Path

# --- Paths -------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = REPO_ROOT / "data" / "raw"
DATA_PROCESSED = REPO_ROOT / "data" / "processed"
DATA_REFERENCE = REPO_ROOT / "data" / "reference"
REPORTS_EDA = REPO_ROOT / "reports" / "eda"

YIELD_RAW_CSV = DATA_RAW / "yield" / "crop_yield.csv"
PRICE_RAW_CSV = DATA_RAW / "prices" / "Agriculture_price_dataset.csv"

YIELD_CLEAN_PARQUET = DATA_PROCESSED / "yield_clean.parquet"
PRICES_MONTHLY_PARQUET = DATA_PROCESSED / "prices_monthly.parquet"

CROP_REFERENCE_CSV = DATA_REFERENCE / "crop_reference.csv"

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
    "onion",
]

# canonical crop -> exact name in each raw dataset.
# yield: exact value of df["Crop"] in data/raw/yield/crop_yield.csv (Kaggle
#        "crop-yield-in-indian-states-dataset").
# price: exact value of df["Commodity"] in data/raw/prices/Agriculture_price_dataset.csv
#        (Kaggle "indian-agricultural-mandi-prices-20232025"), or None if the crop is
#        not present in that dataset for any state.
#
# NOTE: the price dataset, despite its name, contains only 5 commodities total
# (Onion, Potato, Rice, Tomato, Wheat) across the entire file -- not just for
# Maharashtra. jowar, soybean, cotton, sugarcane, and tur have NO price coverage
# in this dataset. See reports/eda/price_report.md.
CROP_NAME_MAP = {
    "rice": {"yield": "Rice", "price": "Rice"},
    "wheat": {"yield": "Wheat", "price": "Wheat"},
    "jowar": {"yield": "Jowar", "price": None},
    "soybean": {"yield": "Soyabean", "price": None},
    "cotton": {"yield": "Cotton(lint)", "price": None},
    "sugarcane": {"yield": "Sugarcane", "price": None},
    "tur": {"yield": "Arhar/Tur", "price": None},
    "onion": {"yield": "Onion", "price": "Onion"},
}

# --- Train/test split + reproducibility ----------------------------------
TRAIN_END_YEAR = 2015
TEST_START_YEAR = 2016
RANDOM_SEED = 42
