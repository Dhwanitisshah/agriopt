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
    # "dry" is a REAL observed year, so an individual crop can need a little less than normal (rabi
    # crops in a year with good winter rain); across the crops it must need more.
    assert df["net_irrigation_dry_mm"].sum() > df["net_irrigation_normal_mm"].sum()


def test_marathwada_dry_at_least_as_demanding_as_maharashtra_normal():
    """Marathwada (drought-prone, semi-arid) is the driest-normal-rainfall IMD subdivision
    among the 4. Its real dry year should need at least as much irrigation as the milder
    Maharashtra STATE-WIDE NORMAL year -- for every kharif-window crop and in total. Rabi
    crops (wheat, jowar; Nov-Mar) are excluded from the per-crop check: they live on
    post-monsoon rain, and the dry year is chosen on usable rain over all 8 crops, so a
    year can be dry for the monsoon yet slightly wetter than normal in winter (wheat:
    508 vs 516 mm, a 1.5% reversal)."""
    ref = load_reference()
    rabi = {"wheat", "jowar"}
    total_dry = total_normal = 0.0
    for crop in CROPS:
        mh_normal = net_irrigation_mm(crop, "normal", ref, region="maharashtra")
        mw_dry = net_irrigation_mm(crop, "dry", ref, region="marathwada")
        total_dry += mw_dry
        total_normal += mh_normal
        if crop not in rabi:
            assert mw_dry >= mh_normal - 1e-6, f"{crop}: marathwada dry ({mw_dry}) < maharashtra normal ({mh_normal})"
    assert total_dry > total_normal


def test_rice_extra_mm_applied_only_to_rice_net_irrigation():
    """RICE_EXTRA_MM (puddling/saturation water) is added to rice's monthly-balance deficit
    and to no other crop's; removing it must leave the pure monthly deficit."""
    from agriopt.data.rainfall import _monthly_balance

    ref = load_reference()
    for crop in CROPS:
        net = net_irrigation_mm(crop, "normal", ref, region="maharashtra")
        deficit, _ = _monthly_balance(crop, "normal", ref, "maharashtra")
        assert net == pytest.approx(deficit + (RICE_EXTRA_MM if crop == "rice" else 0.0), abs=1e-6)


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
    with pytest.raises(ValueError, match="region"):  # a real exception (an assert would vanish under python -O)
        build_crop_params("market", verbose=False, water_basis="net_irrigation", region="nonexistent")
