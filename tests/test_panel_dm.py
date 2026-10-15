"""Task 9: panel Diebold-Mariano with time-clustered variance + block bootstrap.
Data-free (synthetic loss differentials)."""
import numpy as np
import pandas as pd
import pytest

from agriopt.stats.dm_test import (
    block_bootstrap_pvalue,
    diebold_mariano,
    dm_from_loss_diff,
    panel_diebold_mariano,
)


def _panel(months=40, crops=7, effect=0.0, common_sd=1.0, idio_sd=0.2, seed=0):
    """d[t, c] = effect + common month shock + small idiosyncratic noise."""
    rng = np.random.default_rng(seed)
    common = rng.normal(0, common_sd, size=(months, 1))
    d = effect + common + rng.normal(0, idio_sd, size=(months, crops))
    return pd.DataFrame(d, index=pd.date_range("2021-01-01", periods=months, freq="MS"), columns=[f"c{i}" for i in range(crops)])


def test_a_single_crop_panel_is_the_plain_dm_test():
    panel = _panel(crops=1)
    d = panel["c0"].to_numpy()
    stat, p, n = panel_diebold_mariano(panel, h=3)
    assert n == 40
    assert (stat, p) == pytest.approx(dm_from_loss_diff(d, 3))
    # and dm_from_loss_diff is what diebold_mariano calls on |e1| - |e2|
    rng = np.random.default_rng(5)
    e1, e2 = rng.normal(size=60), rng.normal(size=60)
    assert diebold_mariano(e1, e2, 3) == pytest.approx(dm_from_loss_diff(np.abs(e1) - np.abs(e2), 3))


def test_stacking_crops_overstates_significance_when_they_move_together():
    """Crops share the month's shock, so 7 stacked crops carry about one crop's worth of
    information. The stacked test treats them as 280 independent points and calls a
    small effect significant far more often than the time-clustered panel test."""
    stacked_hits = panel_hits = 0
    runs = 60
    for seed in range(runs):
        panel = _panel(effect=0.0, seed=seed)  # NO true difference
        stacked = panel.to_numpy().T.reshape(-1)  # crop after crop, as the old pooled test did
        _, p_stacked = dm_from_loss_diff(stacked, 3)
        _, p_panel, _ = panel_diebold_mariano(panel, 3)
        stacked_hits += p_stacked < 0.05
        panel_hits += p_panel < 0.05
    assert panel_hits / runs < 0.15  # close to the nominal 5%
    assert stacked_hits / runs > 2 * (panel_hits / runs) + 0.1  # the stacked test over-rejects badly


def test_panel_test_still_detects_a_real_effect():
    _, p, _ = panel_diebold_mariano(_panel(effect=1.5), 3)
    assert p < 0.01


def test_months_with_missing_crops_are_averaged_over_available_crops():
    panel = _panel()
    panel.iloc[:5, 1:] = np.nan
    stat, p, n = panel_diebold_mariano(panel, 3)
    assert n == 40 and np.isfinite(stat) and 0 <= p <= 1


def test_block_bootstrap_agrees_with_the_panel_test_and_is_deterministic():
    null_panel, effect_panel = _panel(effect=0.0, seed=3), _panel(effect=1.5, seed=3)
    p_null, _ = block_bootstrap_pvalue(null_panel, block_len=6, n_boot=2000, seed=1)
    p_eff, _ = block_bootstrap_pvalue(effect_panel, block_len=6, n_boot=2000, seed=1)
    assert p_null > 0.05 and p_eff < 0.01
    assert block_bootstrap_pvalue(effect_panel, block_len=6, n_boot=500, seed=7) == block_bootstrap_pvalue(
        effect_panel, block_len=6, n_boot=500, seed=7
    )


def test_identical_forecasts_give_p_one_not_a_spurious_bootstrap_rejection():
    zero = pd.DataFrame(np.zeros((36, 7)), index=pd.date_range("2021-01-01", periods=36, freq="MS"))
    assert panel_diebold_mariano(zero, 12)[1] == 1.0
    assert block_bootstrap_pvalue(zero, block_len=12)[0] == 1.0
