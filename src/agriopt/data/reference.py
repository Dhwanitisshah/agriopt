"""Loader for the hand-curated crop reference table (water need, cost of
cultivation, fertilizer dose). See data/reference/crop_reference.csv.
"""
from __future__ import annotations

import pandas as pd

from agriopt.config import CROP_REFERENCE_CSV

REQUIRED_COLUMNS = [
    "crop",
    "water_mm_min",
    "water_mm_max",
    "water_source",
    "cost_rs_per_ha",
    "cost_source",
    "fert_n_kg_ha",
    "fert_p_kg_ha",
    "fert_k_kg_ha",
    "fert_source",
    "verified",
]

# columns that must be populated (non-null) for a crop to be usable in the
# optimization -- cost of cultivation and fertilizer dose currently ship as
# TODO placeholders (see crop_reference.csv) since we do not invent numbers.
REQUIRED_POPULATED_COLUMNS = ["cost_rs_per_ha", "fert_n_kg_ha", "fert_p_kg_ha", "fert_k_kg_ha"]


def load_reference(path=CROP_REFERENCE_CSV) -> pd.DataFrame:
    """Load crop_reference.csv and raise if any crop is missing required
    cost/fertilizer figures.

    Water need may legitimately be blank for crops not covered by FAO TM3
    (e.g. tur); cost and fertilizer figures may not, since the optimization's
    objective and constraint functions depend on them directly.
    """
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
            "crop_reference.csv has unpopulated cost/fertilizer fields "
            "(see TODO sources in the CSV):\n" + "\n".join(lines)
        )

    return df
