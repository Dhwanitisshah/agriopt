import pandas as pd

from agriopt.config import (
    CROPS,
    CROP_NAME_MAP,
    CROP_REFERENCE_CSV,
    PRICES_MONTHLY_PARQUET,
    STATE,
    YIELD_CLEAN_PARQUET,
)
from agriopt.data import price_data, reference, yield_data  # noqa: F401


def test_imports():
    import agriopt  # noqa: F401
    import agriopt.data.price_data  # noqa: F401
    import agriopt.data.reference  # noqa: F401
    import agriopt.data.yield_data  # noqa: F401


def test_yield_clean_parquet():
    assert YIELD_CLEAN_PARQUET.exists(), f"missing {YIELD_CLEAN_PARQUET}"
    df = pd.read_parquet(YIELD_CLEAN_PARQUET)

    assert "Production" not in df.columns
    assert "fertilizer_per_ha" in df.columns

    yield_names_to_canon = {v["yield"]: k for k, v in CROP_NAME_MAP.items()}
    mh = df[df["state"] == STATE]
    covered_crops = {yield_names_to_canon[c] for c in mh["crop"].unique() if c in yield_names_to_canon}
    assert len(covered_crops) >= 6, (
        f"expected Maharashtra rows for >=6 of 8 crops, got {sorted(covered_crops)}"
    )


def test_prices_monthly_parquet():
    assert PRICES_MONTHLY_PARQUET.exists(), f"missing {PRICES_MONTHLY_PARQUET}"
    df = pd.read_parquet(PRICES_MONTHLY_PARQUET)
    assert len(df) > 0

    available_crops = {k for k, v in CROP_NAME_MAP.items() if v["price"] is not None}
    assert set(df["crop"].unique()).issubset(available_crops)
    assert set(df["crop"].unique()) == available_crops


def test_crop_reference_csv():
    df = pd.read_csv(CROP_REFERENCE_CSV)

    required_cols = {
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
    }
    assert required_cols.issubset(df.columns)
    assert set(df["crop"]) == set(CROPS)
