import numpy as np
import pandas as pd
import pytest

pytestmark = pytest.mark.needs_data  # Phase 10: needs gitignored data/raw or models/*.joblib -- see pyproject.toml's marker registration

from agriopt.config import CROPS, YIELD_MODEL_METADATA_PATH
from agriopt.data.reference import load_reference
from agriopt.models.price_model import PRICE_CROPS, build_base_features, build_horizon_table
from agriopt.models.price_model import expected_price
from agriopt.models.yield_model import load_metadata


def test_load_reference_no_nans_in_cost_fert_water():
    df = load_reference()
    assert set(df["crop"]) == set(CROPS)

    required = ["water_mm_min", "water_mm_max", "cost_rs_per_qtl", "fert_n_kg_ha", "fert_p_kg_ha", "fert_k_kg_ha"]
    for col in required:
        assert df[col].notna().all(), f"{col} has NaN values"


def test_backtest_never_uses_data_at_or_after_origin():
    # Synthetic, strictly increasing series -- if a training row ever
    # includes information at/after the origin's target, this would be easy
    # to detect (values are just the row index).
    months = pd.date_range("2000-01-01", periods=48, freq="MS")
    wide = pd.DataFrame({"testcrop": np.arange(len(months), dtype=float)}, index=months)

    base = build_base_features(wide)
    horizon_table = build_horizon_table(base, wide, h=3)

    origin = pd.Timestamp("2002-06-01")
    train_rows = horizon_table[
        (horizon_table["target_month"] <= origin) & horizon_table["target_price"].notna()
    ]

    assert len(train_rows) > 0
    # every training example's own target must be realized on or before the
    # current origin -- never after it (no future leakage)
    assert (train_rows["target_month"] <= origin).all()
    # and its origin must be strictly earlier than the current origin
    assert (train_rows["origin_month"] < origin).all()


def test_expected_price_positive_for_all_crops_sugarcane_is_frp():
    for crop in CROPS:
        r = expected_price(crop, horizon=12)
        assert r["value_rs_per_qtl"] > 0
        assert np.isfinite(r["value_rs_per_qtl"])

    r = expected_price("sugarcane")
    assert r["value_rs_per_qtl"] == pytest.approx(355)
    assert r["method"] == "FRP"


def test_yield_inference_metadata_train_max_year():
    metadata = load_metadata(YIELD_MODEL_METADATA_PATH)
    assert metadata["train_max_year"] == 2020
