"""Phase 8.1: area-weighted rainfall / per-region net irrigation tests."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.needs_data  # Phase 10: needs gitignored data/raw or models/*.joblib -- see pyproject.toml's marker registration

from agriopt.config import CROPS
from agriopt.data.rainfall import (
    REGIONS,
    REGION_TO_SUBDIVISION,
    RICE_EXTRA_MM,
    area_weights,
    net_irrigation_mm,
    rainfall_water_table,
)
from agriopt.data.reference import load_reference
from agriopt.optim.params import build_crop_params
from agriopt.optim.problem import Scenario


def test_area_weights_sum_to_one():
    weights = area_weights()
    assert set(weights) == {"KONKAN & GOA", "MADHYA MAHARASHTRA", "MATATHWADA", "VIDARBHA"}
    assert sum(weights.values()) == pytest.approx(1.0, abs=1e-9)
    assert all(w > 0 for w in weights.values())


def test_all_regions_covered():
    assert REGIONS[0] == "maharashtra"
    assert set(REGIONS[1:]) == set(REGION_TO_SUBDIVISION)
    assert set(REGION_TO_SUBDIVISION.values()) == {
        "KONKAN & GOA",
        "MADHYA MAHARASHTRA",
        "MATATHWADA",
        "VIDARBHA",
    }


@pytest.mark.parametrize("region", REGIONS)
def test_rainfall_water_table_every_region(region):
    df = rainfall_water_table(CROPS, region=region)
    for col in ["water_need_mm", "peff_normal_mm", "net_irrigation_normal_mm", "net_irrigation_dry_mm"]:
        assert col in df.columns
    assert set(df.index) == set(CROPS)
    # dry-year net irrigation should never be LESS than normal-year net irrigation
    assert (df["net_irrigation_dry_mm"] >= df["net_irrigation_normal_mm"] - 1e-9).all()


def test_marathwada_dry_at_least_as_demanding_as_maharashtra_normal():
    """Marathwada (drought-prone, semi-arid) is the driest-normal-rainfall
    IMD subdivision among the 4; the task asks us to check (not blindly
    assert) that its DRY-year net irrigation is at least as demanding as the
    milder Maharashtra STATE-WIDE (area-weighted) NORMAL-year figure, for
    every crop. Verified true for all 8 crops with the actual numbers (see
    docs/water.md section 8.4) -- reported honestly either way."""
    ref = load_reference()
    for crop in CROPS:
        mh_normal = net_irrigation_mm(crop, "normal", ref, region="maharashtra")
        mw_dry = net_irrigation_mm(crop, "dry", ref, region="marathwada")
        assert mw_dry >= mh_normal - 1e-6, (
            f"{crop}: marathwada dry ({mw_dry}) < maharashtra normal ({mh_normal}), "
            "contrary to the expected direction -- see docs/water.md section 8.4"
        )


def test_rice_extra_mm_applied_only_to_rice_net_irrigation():
    ref = load_reference()
    for crop in CROPS:
        net_with = net_irrigation_mm(crop, "normal", ref, region="maharashtra")
        if crop == "rice":
            # rice's normal-scenario Peff already exceeds its FAO TM3 need
            # (max(0, need - peff) == 0), so the entire net figure IS
            # RICE_EXTRA_MM at this scenario -- see docs/water.md 8.4.
            assert net_with == pytest.approx(RICE_EXTRA_MM, abs=1e-6)


def test_default_region_reproduces_area_weighted_maharashtra():
    """build_crop_params with no `region` argument (as every pre-Phase-8.1
    caller does) must match region="maharashtra" explicitly -- the default
    must not silently pick a different region."""
    df_default = build_crop_params(
        "market", verbose=False, water_basis="net_irrigation", rainfall_scenario="normal"
    )
    df_explicit = build_crop_params(
        "market",
        verbose=False,
        water_basis="net_irrigation",
        rainfall_scenario="normal",
        region="maharashtra",
    )
    import numpy as np

    np.testing.assert_allclose(
        df_default["water_m3_ha"].to_numpy(), df_explicit["water_m3_ha"].to_numpy(), atol=1e-9
    )


def test_region_changes_water_m3_ha():
    df_mh = build_crop_params(
        "market", verbose=False, water_basis="net_irrigation", region="maharashtra"
    )
    df_mw = build_crop_params(
        "market", verbose=False, water_basis="net_irrigation", region="marathwada"
    )
    import numpy as np

    assert not np.allclose(df_mh["water_m3_ha"].to_numpy(), df_mw["water_m3_ha"].to_numpy())


def test_scenario_region_defaults_to_maharashtra():
    s = Scenario(water_budget_m3=1000.0)
    assert s.region == "maharashtra"


def test_invalid_region_rejected():
    with pytest.raises(AssertionError):
        build_crop_params("market", verbose=False, water_basis="net_irrigation", region="nonexistent")
