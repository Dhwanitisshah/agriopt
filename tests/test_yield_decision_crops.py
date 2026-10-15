"""Task 8: the yield model is judged on the 8 decision crops, against a
last-3-year state-mean baseline, with losers flagged."""
import numpy as np
import pandas as pd
import pytest

from agriopt.config import CROPS, REPORTS_RESULTS
from agriopt.models.yield_model import BaselineRecentMean


def _toy_train():
    rows = []
    for year, y in zip(range(2010, 2016), [1.0, 2.0, 3.0, 4.0, 5.0, 9.0]):
        rows.append({"state": "MH", "crop": "Rice", "season": "Kharif", "year": year, "yield": y})
    rows.append({"state": "MH", "crop": "Wheat", "season": "Rabi", "year": 2015, "yield": 7.0})  # a single year
    rows.append({"state": "UP", "crop": "Rice", "season": "Kharif", "year": 2015, "yield": 3.0})
    return pd.DataFrame(rows)


def test_recent_mean_baseline_averages_the_last_three_years_of_the_same_group():
    model = BaselineRecentMean(3).fit(_toy_train())
    test = pd.DataFrame(
        [
            {"state": "MH", "crop": "Rice", "season": "Kharif"},
            {"state": "MH", "crop": "Wheat", "season": "Rabi"},  # only one year of history: uses it
            {"state": "KA", "crop": "Rice", "season": "Kharif"},  # unseen state: falls back to (crop, season)
        ]
    )
    pred = model.predict(test)
    assert pred[0] == pytest.approx((4.0 + 5.0 + 9.0) / 3)  # 2013-2015, not the all-years mean 4.0
    assert pred[1] == pytest.approx(7.0)
    # (crop, season) fallback = mean over the last 3 *years* of per-year cross-section means:
    # 2013: 4 ; 2014: 5 ; 2015: mean(9, 3) = 6  ->  5.0
    assert pred[2] == pytest.approx(5.0)


def test_committed_decision_crop_table_is_complete_and_flags_are_consistent():
    v = pd.read_csv(REPORTS_RESULTS / "yield_decision_crops_verdicts.csv")
    assert set(v["design"]) == {"one-step-ahead (refit each year)", "fixed origin (trained <= 2015)"}
    for design, g in v.groupby("design"):
        assert sorted(g["crop"]) == sorted(CROPS), design
        assert (g["n"] == 4).all()  # 2016-2019
        np.testing.assert_array_equal(g["rf_loses_to_last3"].to_numpy(), (g["rf_MAE"] > g["last3_MAE"]).to_numpy())
        np.testing.assert_allclose(g["rf_skill_vs_last3"], 1 - g["rf_MAE"] / g["last3_MAE"])
        # a crop that loses to the best baseline can still beat last-3, never the reverse
        assert (g["rf_loses_to_best_baseline"] | ~g["rf_loses_to_last3"]).all()


def test_pooled_r2_is_not_in_the_committed_results_table():
    text = (REPORTS_RESULTS / "yield_results.md").read_text(encoding="utf-8")
    assert "_R2" not in text
    assert "yield_decision_crops" in text
