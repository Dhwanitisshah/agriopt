"""Phase 8: effective rainfall / net irrigation tests."""
from __future__ import annotations

import numpy as np
import pytest

from agriopt.config import CROPS
from agriopt.data.rainfall import (
    CROP_SEASON_WINDOW,
    effective_rainfall_mm,
    net_irrigation_mm,
    rainfall_water_table,
)
from agriopt.data.reference import load_reference, water_mm
from agriopt.optim.params import build_crop_params

KHARIF_LIKE_CROPS = ["rice", "soybean", "maize", "cotton", "tur"]  # kharif + long_kharif (Jun-Jan)


def _hand_peff(p: float) -> float:
    if p <= 250:
        return p * (125 - 0.2 * p) / 125
    return 125 + 0.1 * p


@pytest.mark.parametrize("p", [0, 100, 250, 400])
def test_effective_rainfall_matches_hand_computation(p):
    assert effective_rainfall_mm(p) == pytest.approx(_hand_peff(p), abs=1e-9)


def test_effective_rainfall_vectorized():
    ps = np.array([0, 100, 250, 400], dtype=float)
    expected = np.array([_hand_peff(p) for p in ps])
    np.testing.assert_allclose(effective_rainfall_mm(ps), expected, atol=1e-9)


@pytest.mark.parametrize("scenario", ["normal", "dry"])
def test_net_irrigation_nonnegative_for_every_crop(scenario):
    ref = load_reference()
    for crop in CROPS:
        val = net_irrigation_mm(crop, scenario, ref)
        assert val >= 0.0, f"{crop}/{scenario}: net irrigation {val} < 0"


def test_kharif_crops_net_irrigation_below_total_need():
    ref = load_reference()
    for crop in KHARIF_LIKE_CROPS:
        need = water_mm(crop, ref)
        net = net_irrigation_mm(crop, "normal", ref)
        assert net < need, f"{crop}: net irrigation {net} not below total need {need} (monsoon should reduce it)"


def test_rainfall_water_table_columns():
    df = rainfall_water_table(CROPS)
    for col in ["water_need_mm", "peff_normal_mm", "net_irrigation_normal_mm", "net_irrigation_dry_mm"]:
        assert col in df.columns
    assert set(df.index) == set(CROPS)
    # dry-year net irrigation should never be LESS than normal-year net irrigation
    # (a drier year has less rain to offset the same crop water need)
    assert (df["net_irrigation_dry_mm"] >= df["net_irrigation_normal_mm"] - 1e-9).all()


def test_all_crops_have_a_season_window():
    for crop in CROPS:
        assert crop in CROP_SEASON_WINDOW


# --- Phase 8 regression: total_need basis must reproduce byte-for-byte -----


def test_default_water_basis_reproduces_total_need():
    """water_basis defaults to "total_need" -- build_crop_params with no
    water_basis argument (as every pre-Phase-8 caller does) must reproduce
    the exact pre-Phase-8 water_m3_ha values. rice: water_mm_min=450,
    water_mm_max=700 (data/reference/crop_reference.csv) -> midpoint 575mm
    -> 5750 m3/ha (MM_TO_M3_PER_HA=10), unaffected by any Phase 8 change --
    pure arithmetic, no model involved."""
    df = build_crop_params("market", verbose=False)
    assert df.loc["rice", "water_m3_ha"] == pytest.approx(5750.0, abs=1e-9)

    df_explicit = build_crop_params("market", verbose=False, water_basis="total_need")
    np.testing.assert_allclose(
        df["water_m3_ha"].to_numpy(), df_explicit["water_m3_ha"].to_numpy(), atol=1e-9
    )


def test_net_irrigation_basis_differs_from_total_need():
    df_total = build_crop_params("market", verbose=False, water_basis="total_need")
    df_net = build_crop_params("market", verbose=False, water_basis="net_irrigation")
    # at least one crop's water_m3_ha must differ once net irrigation is used
    assert not np.allclose(df_total["water_m3_ha"].to_numpy(), df_net["water_m3_ha"].to_numpy())
    # net irrigation must never exceed total need
    assert (df_net["water_m3_ha"].to_numpy() <= df_total["water_m3_ha"].to_numpy() + 1e-6).all()
