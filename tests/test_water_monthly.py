"""Task 10: net irrigation is a monthly water balance, 'dry' is a real year.
Synthetic cases patch the yearly effective-rainfall table; the data-backed
checks need the IMD rainfall file."""
import numpy as np
import pandas as pd
import pytest

from agriopt.config import CROPS
from agriopt.data import rainfall
from agriopt.data.reference import load_reference, water_mm

MONTHS = rainfall.MONTH_COLS


def _fake_yearly(rows: dict[int, dict[str, float]]) -> pd.DataFrame:
    return pd.DataFrame({y: {m: v.get(m, 0.0) for m in MONTHS} for y, v in rows.items()}).T[MONTHS]


@pytest.fixture
def synthetic(monkeypatch):
    # soybean: kharif window JUN-OCT (5 months), FAO need 575 mm -> 115 mm per month
    yearly = _fake_yearly(
        {
            2001: {"JUN": 0, "JUL": 300, "AUG": 115, "SEP": 0, "OCT": 0},  # July surplus, Jun/Sep/Oct empty
            2002: {"JUN": 115, "JUL": 115, "AUG": 115, "SEP": 115, "OCT": 115},  # exactly on need every month
        }
    )
    monkeypatch.setattr(rainfall, "_yearly_effective_rainfall", lambda region, n_years=30: yearly)
    monkeypatch.setattr(rainfall, "dry_year", lambda region="maharashtra", n_years=30: 2001)
    return yearly


def test_a_surplus_month_does_not_cover_a_later_deficit(synthetic):
    ref = load_reference()
    need = water_mm("soybean", ref)
    assert need == pytest.approx(575.0)
    # 2001 (the 'dry' year): deficits Jun 115 + Sep 115 + Oct 115 = 345. The old season-level form would
    # have said max(0, 575 - (0+300+115+0+0)) = 160, letting July's 185 mm surplus pay for September.
    assert rainfall.net_irrigation_mm("soybean", "dry", ref) == pytest.approx(345.0)
    old_form = max(0.0, need - float(synthetic.loc[2001, ["JUN", "JUL", "AUG", "SEP", "OCT"]].sum()))
    assert old_form == pytest.approx(160.0) and rainfall.net_irrigation_mm("soybean", "dry", ref) > old_form


def test_normal_is_the_average_of_the_yearly_balances(synthetic):
    ref = load_reference()
    # 2001 -> 345 ; 2002 -> 0 ; normal = their mean = 172.5. Balancing the smooth mean-rainfall year
    # at season level would give only 575 - 495 = 80: it hides the months that fall short.
    assert rainfall.net_irrigation_mm("soybean", "normal", ref) == pytest.approx(172.5)
    mean_year = synthetic.mean()
    assert max(0.0, 575.0 - float(mean_year[["JUN", "JUL", "AUG", "SEP", "OCT"]].sum())) == pytest.approx(80.0)


def test_rain_used_never_exceeds_the_monthly_need(synthetic):
    ref = load_reference()
    used = rainfall.season_rain_used_mm("soybean", "dry", ref)
    assert used == pytest.approx(115.0 + 115.0)  # Jul capped at 115 (not 300), Aug 115
    assert rainfall.net_irrigation_mm("soybean", "dry", ref) + used == pytest.approx(water_mm("soybean", ref))


needs_data = pytest.mark.needs_data


@needs_data
@pytest.mark.parametrize("region", rainfall.REGIONS)
def test_dry_scenario_is_an_observed_year_not_a_composite(region):
    df = rainfall.load_rainfall_raw()
    yearly = rainfall._regional_yearly(df, region)
    year = rainfall.dry_year(region)
    assert year in yearly.index
    pd.testing.assert_series_equal(rainfall.monthly_dry_year(region), yearly.loc[year], check_names=False)
    # the per-month 20th percentile composite is NOT any observed year
    composite = yearly.quantile(0.20, axis=0)
    assert not any(np.allclose(composite.to_numpy(), yearly.loc[y].to_numpy()) for y in yearly.index)


@needs_data
@pytest.mark.parametrize("region", rainfall.REGIONS)
def test_dry_year_sits_near_the_20th_percentile_of_usable_rain(region):
    usable = rainfall.usable_rain_by_year(region)
    rank = float((usable < usable[rainfall.dry_year(region)]).mean())  # share of years drier than the chosen one
    assert 0.10 <= rank <= 0.30, (region, rank)


@needs_data
@pytest.mark.parametrize("region", rainfall.REGIONS)
def test_dry_year_needs_more_irrigation_than_normal_across_the_crops(region):
    ref = load_reference()
    normal = sum(rainfall.net_irrigation_mm(c, "normal", ref, region) for c in CROPS)
    dry = sum(rainfall.net_irrigation_mm(c, "dry", ref, region) for c in CROPS)
    assert dry > normal
