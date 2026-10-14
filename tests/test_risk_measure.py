"""Task 5: risk mode must not reward fallow land, and the reported profit risk
must count crop co-movement. Data-free: toy parameters and a hand-made Sigma."""
import numpy as np
import pandas as pd
import pytest

from agriopt.optim.baselines import evaluate
from agriopt.optim.problem import Scenario
from agriopt.optim.risk import RISK_CV_CAP, portfolio_risk_vectorized, risk_per_profit_vectorized

PROFIT_HA = np.array([20000.0, 10000.0])
SIGMA = np.array([[4.0e6, 1.0e6], [1.0e6, 9.0e6]])  # Rs^2 per ha^2, positively correlated


def test_absolute_risk_rewards_fallow_but_risk_per_profit_does_not():
    x = np.array([[4.0, 3.0]])
    half = x / 2.0  # leave half of every crop's land fallow
    assert portfolio_risk_vectorized(half, SIGMA)[0] == pytest.approx(portfolio_risk_vectorized(x, SIGMA)[0] / 2)
    assert risk_per_profit_vectorized(half, SIGMA, PROFIT_HA)[0] == pytest.approx(
        risk_per_profit_vectorized(x, SIGMA, PROFIT_HA)[0]
    )


def test_risk_per_profit_is_the_cv_and_empty_or_loss_plans_get_the_worst_value():
    x = np.array([[4.0, 3.0], [0.0, 0.0], [1.0, 1.0]])
    r = risk_per_profit_vectorized(x, SIGMA, PROFIT_HA)
    sd = np.sqrt(4.0**2 * 4.0e6 + 3.0**2 * 9.0e6 + 2 * 4.0 * 3.0 * 1.0e6)
    assert r[0] == pytest.approx(sd / (4 * 20000.0 + 3 * 10000.0))
    assert r[1] == RISK_CV_CAP  # nothing planted: no meaningful ratio, never "safe"
    losing = risk_per_profit_vectorized(np.array([[1.0, 1.0]]), SIGMA, np.array([-5000.0, 1000.0]))
    assert losing[0] == RISK_CV_CAP


def _toy():
    return pd.DataFrame(
        {
            "profit_ha": PROFIT_HA,
            "water_m3_ha": [1.0, 1.0],
            "fert_kg_ha": [1.0, 1.0],
            "profit_std_ha": [2000.0, 3000.0],
            "seasons_occupied": [{"kharif"}, {"kharif"}],
        },
        index=["a", "b"],
    )


def test_evaluate_profit_risk_uses_sigma_and_counts_correlation():
    scen = Scenario(water_budget_m3=1e6, land_ha=10.0, food_share_min=0.0, max_share=1.0)
    x = np.array([4.0, 3.0])
    independent = evaluate(x, _toy(), scen)["profit_risk"]
    with_sigma = evaluate(x, _toy(), scen, Sigma=SIGMA)["profit_risk"]
    assert independent == pytest.approx(np.sqrt((4 * 2000.0) ** 2 + (3 * 3000.0) ** 2))
    assert with_sigma == pytest.approx(float(np.sqrt(x @ SIGMA @ x)))
    # off-diagonal covariance is positive, so ignoring it understates the risk of this plan
    uncorrelated = np.diag(np.diag(SIGMA))
    assert with_sigma > evaluate(x, _toy(), scen, Sigma=uncorrelated)["profit_risk"]
