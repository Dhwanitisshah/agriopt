"""Phase 10: schema/keys-presence tests on the committed
data/processed/crop_params_cache.json -- these do NOT need gitignored
data/models (the cache itself is a committed file, see .gitignore's
negation for it), so this file carries no `needs_data` marker and always
runs in CI."""
from __future__ import annotations

from app import data as appdata
from agriopt.data.rainfall import REGIONS
from app.presets import PRESETS

REQUIRED_TOP_KEYS = {
    "built_at",
    "crops",
    "regions",
    "yield_model_metadata",
    "price_model_metadata",
    "params",
    "price_modes",
    "risk",
    "conformal",
    "backtest",
    "region_comparison",
    "preset_results",
}


def test_cache_exists():
    assert appdata.cache_exists(), f"missing {appdata.CACHE_PATH} -- run `python scripts\\40_build_cache.py`"


def test_cache_has_all_top_level_keys():
    raw = appdata.load_cache_raw()
    missing = REQUIRED_TOP_KEYS - set(raw.keys())
    assert not missing, f"cache missing top-level keys: {missing}"


def test_cache_params_covers_every_region_and_water_basis():
    raw = appdata.load_cache_raw()
    for region in REGIONS:
        assert region in raw["params"], f"missing region={region!r} in cache['params']"
        block = raw["params"][region]
        assert "total_need" in block and "net_irrigation" in block
        for mode in ("market", "msp_floor"):
            assert mode in block["total_need"], f"{region}/total_need missing price_mode={mode}"
            for scenario in ("normal", "dry"):
                assert scenario in block["net_irrigation"], f"{region}/net_irrigation missing scenario={scenario}"
                assert mode in block["net_irrigation"][scenario], f"{region}/net_irrigation/{scenario} missing {mode}"


def test_cache_params_df_loadable_for_every_combo():
    raw = appdata.load_cache_raw()
    for region in REGIONS:
        for water_basis, rainfall_scenario in [("total_need", "normal"), ("net_irrigation", "normal"), ("net_irrigation", "dry")]:
            df = appdata.params_df_for(raw, region, water_basis, rainfall_scenario, "market")
            assert len(df) == len(raw["crops"])
            assert (df["water_m3_ha"] >= 0).all()


def test_cache_conformal_has_expected_shape():
    raw = appdata.load_cache_raw()
    conformal = raw["conformal"]
    assert "q_overall" in conformal and "q_per_crop" in conformal and "alpha" in conformal
    assert conformal["alpha"] == 0.10
    for crop in raw["crops"]:
        assert crop in conformal["q_per_crop"] or conformal["q_overall"] is not None


def test_cache_backtest_and_region_comparison_nonempty():
    raw = appdata.load_cache_raw()
    assert len(raw["backtest"]["fairness"]) > 0
    assert len(raw["region_comparison"]["konkan_strategies"]) > 0
    assert len(raw["region_comparison"]["marathwada_strategies"]) > 0


def test_cache_has_all_presets():
    raw = appdata.load_cache_raw()
    for name in PRESETS:
        assert name in raw["preset_results"], f"missing preset {name!r} in cache['preset_results']"
        assert "normal" in raw["preset_results"][name] and "risk_aware" in raw["preset_results"][name]
