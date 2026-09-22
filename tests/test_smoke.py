from unittest.mock import MagicMock

import pandas as pd
import pytest

from agriopt.config import (
    CROPS,
    CROP_NAME_MAP,
    CROP_REFERENCE_CSV,
    PRICES_MONTHLY_PARQUET,
    STATE,
    YIELD_CLEAN_PARQUET,
    YIELD_TO_SALEABLE_QTL_PER_HA,
)
from agriopt.data import ceda_client, price_data, reference, yield_data  # noqa: F401

MIN_MONTHS = 60


def test_imports():
    import agriopt  # noqa: F401
    import agriopt.data.ceda_client  # noqa: F401
    import agriopt.data.price_data  # noqa: F401
    import agriopt.data.reference  # noqa: F401
    import agriopt.data.yield_data  # noqa: F401


def test_crops_list():
    assert len(CROPS) == 8
    assert "onion" not in CROPS
    assert "maize" in CROPS


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

    for crop in CROPS:
        if crop == "sugarcane":
            continue  # no mandi series -- FRP admin price instead
        n_months = df[df["crop"] == crop]["month"].nunique()
        assert n_months >= MIN_MONTHS, f"{crop}: only {n_months} months (< {MIN_MONTHS})"


def test_yield_to_saleable_qtl_per_ha_covers_all_crops():
    for crop in CROPS:
        assert crop in YIELD_TO_SALEABLE_QTL_PER_HA, f"missing conversion for {crop}"
        assert callable(YIELD_TO_SALEABLE_QTL_PER_HA[crop])


def test_crop_reference_csv():
    df = pd.read_csv(CROP_REFERENCE_CSV)

    required_cols = {
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
    }
    assert required_cols.issubset(df.columns)
    assert set(df["crop"]) == set(CROPS)


def test_ceda_client_never_leaks_api_key_on_failure(monkeypatch):
    monkeypatch.setattr(ceda_client, "RATE_LIMIT_SECONDS", 0.0)
    monkeypatch.setattr(ceda_client, "RETRY_BACKOFF_SECONDS", 0.0)

    secret_key = "SUPER_SECRET_TEST_KEY_4f8c2a"
    client = ceda_client.CedaClient(api_key=secret_key)

    fake_response = MagicMock()
    fake_response.status_code = 500
    fake_response.ok = False
    fake_response.text = "internal server error"
    monkeypatch.setattr(client._session, "request", MagicMock(return_value=fake_response))

    with pytest.raises(ceda_client.CedaApiError) as excinfo:
        client.get_commodities()

    message = str(excinfo.value)
    assert secret_key not in message
