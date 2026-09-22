"""Loader for the hand-curated crop reference table (water need, cost of
cultivation, MSP, fertilizer dose). See data/reference/crop_reference.csv and
docs/reference_data.md for sources and limitations.
"""
from __future__ import annotations

import pandas as pd

from agriopt.config import CROP_REFERENCE_CSV

REQUIRED_COLUMNS = [
    "crop",
    "water_mm_min",
    "water_mm_max",
    "water_source",
    "cost_rs_per_qtl",
    "cost_source",
    "msp_rs_per_qtl",
    "msp_source",
    "fert_n_kg_ha",
    "fert_p_kg_ha",
    "fert_k_kg_ha",
    "fert_source",
    "fert_basis",
    "admin_price_rs_per_qtl",
    "verified",
    "notes",
]

# Columns that must be populated (non-null) for every crop -- cost of
# cultivation, fertilizer dose, and water need, all needed by the
# optimizer's objective/constraint functions. msp_rs_per_qtl and
# admin_price_rs_per_qtl are intentionally NOT required for every row:
# sugarcane has no MSP (sold at the government FRP instead, see
# admin_price_rs_per_qtl), and only sugarcane has an admin_price.
REQUIRED_POPULATED_COLUMNS = [
    "water_mm_min",
    "water_mm_max",
    "cost_rs_per_qtl",
    "fert_n_kg_ha",
    "fert_p_kg_ha",
    "fert_k_kg_ha",
]


def load_reference(path=CROP_REFERENCE_CSV) -> pd.DataFrame:
    """Load crop_reference.csv and raise if any crop is missing a required
    water/cost/fertilizer figure."""
    df = pd.read_csv(path)

    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValueError(f"crop_reference.csv is missing columns: {missing_cols}")

    problems: dict[str, list[str]] = {}
    for _, row in df.iterrows():
        gaps = [c for c in REQUIRED_POPULATED_COLUMNS if pd.isna(row[c]) or row[c] == ""]
        if gaps:
            problems[row["crop"]] = gaps

    if problems:
        lines = [f"  - {crop}: missing {fields}" for crop, fields in problems.items()]
        raise ValueError(
            "crop_reference.csv has unpopulated required fields:\n" + "\n".join(lines)
        )

    return df


def _row(crop: str, df: pd.DataFrame | None) -> pd.Series:
    df = df if df is not None else load_reference()
    match = df[df["crop"] == crop]
    if match.empty:
        raise ValueError(f"No crop_reference.csv row for crop={crop!r}")
    return match.iloc[0]


def cost_rs_per_ha(crop: str, saleable_qtl_per_ha: float, df: pd.DataFrame | None = None) -> float:
    """Cost of cultivation, Rs/ha = cost_rs_per_qtl (all-India, A2+FL, per
    quintal of marketed product) * saleable yield (quintal/ha). Costs in
    crop_reference.csv are per-quintal; per-ha cost depends on the crop's
    (predicted) yield, so it's derived here rather than stored statically."""
    row = _row(crop, df)
    return float(row["cost_rs_per_qtl"]) * saleable_qtl_per_ha


def water_mm(crop: str, df: pd.DataFrame | None = None) -> float:
    """Crop water need, mm: midpoint of water_mm_min/water_mm_max (FAO TM3 range)."""
    row = _row(crop, df)
    return (float(row["water_mm_min"]) + float(row["water_mm_max"])) / 2


def fert_total_kg_ha(crop: str, df: pd.DataFrame | None = None) -> float:
    """Total NPK fertilizer dose, kg/ha = N + P2O5 + K2O."""
    row = _row(crop, df)
    return float(row["fert_n_kg_ha"]) + float(row["fert_p_kg_ha"]) + float(row["fert_k_kg_ha"])
