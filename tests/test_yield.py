import numpy as np
import pandas as pd
import pytest

pytestmark = pytest.mark.needs_data  # Phase 10: needs gitignored data/raw or models/*.joblib -- see pyproject.toml's marker registration

from agriopt.config import (
    CROPS,
    STATE,
    TEST_START_YEAR,
    TRAIN_END_YEAR,
    YIELD_EVAL_METADATA_PATH,
    YIELD_EVAL_MODEL_PATH,
    YIELD_MODEL_METADATA_PATH,
    YIELD_MODEL_PATH,
)
from agriopt.models.yield_model import (
    BaselineLast,
    BaselineMean,
    expected_yield_saleable,
    load_metadata,
    load_model,
    load_model_frame,
    predict_yield,
    predict_yield_interval,
    train_test_split_by_year,
)


def test_no_production_or_area_in_main_features():
    metadata = load_metadata()
    assert "area_ha" not in metadata["num_cols"]
    assert "Production" not in metadata["num_cols"] and "Production" not in metadata["cat_cols"]


def test_train_test_split_years():
    df, _ = load_model_frame()
    train, test = train_test_split_by_year(df)
    assert train["year"].max() <= TRAIN_END_YEAR
    assert test["year"].min() >= TEST_START_YEAR
    assert train["year"].max() < test["year"].min()


def test_saved_model_loads_and_predicts_positive_for_all_crops():
    assert YIELD_MODEL_PATH.exists()
    assert YIELD_MODEL_METADATA_PATH.exists()
    load_model()  # just confirm it deserializes

    for crop in CROPS:
        pred = predict_yield(crop, season="Kharif", state=STATE, year=2018, rainfall_mm=1000.0)
        assert np.isfinite(pred)
        assert pred > 0


def test_expected_yield_saleable_positive_and_deterministic():
    for crop in CROPS:
        r1 = expected_yield_saleable(crop)
        r2 = expected_yield_saleable(crop)
        assert r1["value"] > 0
        assert np.isfinite(r1["value"])
        assert r1["value"] == pytest.approx(r2["value"])
        assert r1["year"] == r2["year"]
        assert r1["rainfall_mm"] == pytest.approx(r2["rainfall_mm"])


def test_eval_vs_inference_model_train_max_year():
    assert YIELD_EVAL_MODEL_PATH.exists()
    assert YIELD_EVAL_METADATA_PATH.exists()

    inference_meta = load_metadata(YIELD_MODEL_METADATA_PATH)
    eval_meta = load_metadata(YIELD_EVAL_METADATA_PATH)

    assert inference_meta["train_max_year"] == 2020
    assert eval_meta["train_max_year"] == TRAIN_END_YEAR == 2015


def test_baselines_predict_for_every_maharashtra_test_row():
    df, _ = load_model_frame()
    train, test = train_test_split_by_year(df)
    mh_test = test[test["state"] == STATE]
    assert len(mh_test) > 0

    for baseline_cls in (BaselineMean, BaselineLast):
        model = baseline_cls().fit(train)
        preds = model.predict(mh_test)
        assert len(preds) == len(mh_test)
        assert np.all(np.isfinite(preds))


def test_predict_yield_interval_brackets_the_point_prediction():
    """Phase 9: split-conformal interval must be finite, and must bracket
    the point prediction it's centered on (lower <= pred <= upper)."""
    for crop in CROPS:
        r = predict_yield_interval(crop, season="Kharif", state=STATE, year=2018, rainfall_mm=1000.0)
        assert np.isfinite(r["lower"]) and np.isfinite(r["upper"]) and np.isfinite(r["pred_yield"])
        assert r["lower"] <= r["pred_yield"] <= r["upper"]
        assert r["level"] == pytest.approx(0.9)


def test_predict_yield_interval_rejects_uncalibrated_alpha():
    with pytest.raises(NotImplementedError):
        predict_yield_interval("rice", season="Kharif", state=STATE, year=2018, rainfall_mm=1000.0, alpha=0.5)
