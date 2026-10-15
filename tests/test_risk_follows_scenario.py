"""Task 6: the app's risk inputs follow the user's scenario. Sigma =
dev_cov * outer(R, R) is re-scaled from the ACTIVE params_df (price mode,
what-if price shocks, FRP override), not the cache's market-price R. Data-free:
uses only the committed cache."""
import numpy as np
import pytest

import app.data as appdata
from app.pipeline import apply_price_shocks
from app.presets import PRESETS


@pytest.fixture(scope="module")
def raw():
    return appdata.load_cache_raw()


@pytest.fixture(scope="module")
def market(raw):
    return appdata.params_df_for(raw, "maharashtra", "net_irrigation", "normal", "market")


@pytest.mark.parametrize("mode", ["conservative", "frp_based"])
def test_default_inputs_reproduce_the_cached_sigma(raw, market, mode):
    ri = appdata.risk_inputs_for_params(raw, market, sugarcane_mode=mode)
    np.testing.assert_allclose(ri.Sigma, appdata.risk_inputs_from_cache(raw, mode).Sigma, rtol=1e-9)


def test_a_price_shock_rescales_the_covariance_of_that_crop(raw, market):
    crops = appdata.risk_inputs_from_cache(raw).crops
    i = crops.index("rice")
    base = appdata.risk_inputs_for_params(raw, market).Sigma
    shocked_params = apply_price_shocks(market, {"rice": 1.2})
    shocked = appdata.risk_inputs_for_params(raw, shocked_params).Sigma

    d = np.ones(len(crops))
    d[i] = 1.2
    np.testing.assert_allclose(shocked, base * np.outer(d, d), rtol=1e-6)
    assert shocked[i, i] == pytest.approx(1.44 * base[i, i], rel=1e-6)  # rice variance +44%
    others = [j for j in range(len(crops)) if j != i]
    np.testing.assert_allclose(shocked[np.ix_(others, others)], base[np.ix_(others, others)], rtol=1e-9)


def test_sugarcane_frp_override_rescales_sugarcane_risk(raw, market):
    crops = appdata.risk_inputs_from_cache(raw).crops
    i = crops.index("sugarcane")
    gross = float(market.loc["sugarcane", "price"]) + float(market.loc["sugarcane", "price_deduction_rs_per_qtl"])
    raised = apply_price_shocks(market, sugarcane_frp_override=gross + 100.0)
    base = appdata.risk_inputs_for_params(raw, market).Sigma
    new = appdata.risk_inputs_for_params(raw, raised).Sigma
    ratio = float(raised.loc["sugarcane", "price"]) / float(market.loc["sugarcane", "price"])
    assert new[i, i] == pytest.approx(ratio**2 * base[i, i], rel=1e-6)


def test_msp_floor_price_mode_gets_its_own_sigma(raw, market):
    msp = appdata.params_df_for(raw, "maharashtra", "net_irrigation", "normal", "msp_floor")
    s_market = appdata.risk_inputs_for_params(raw, market).Sigma
    s_msp = appdata.risk_inputs_for_params(raw, msp).Sigma
    assert not np.allclose(s_market, s_msp)  # the floor raises some crops' expected revenue
    assert np.linalg.eigvalsh(s_msp).min() >= -1e-6  # still PSD


def test_cached_preset_risk_matches_request_time_sigma(raw):
    """The presets are precomputed offline; the profit risk stored with them must
    equal what the app would compute live for the same inputs."""
    for name, preset in PRESETS.items():
        params_df = appdata.params_df_for(
            raw, preset.get("region", "maharashtra"), preset.get("water_basis", "net_irrigation"),
            preset.get("rainfall_scenario", "normal"), "market",
        )
        ri = appdata.risk_inputs_for_params(raw, params_df, sugarcane_mode="conservative")
        cached = raw["preset_results"][name]["normal"]
        assert cached["feasible"], name
        x = np.array(cached["x"]["OURS"], dtype=float)
        assert cached["evals"]["OURS"]["profit_risk"] == pytest.approx(float(np.sqrt(x @ ri.Sigma @ x)), rel=1e-6), name
