"""Phase 4/6/10: precompute crop params (all region x water_basis x
price_mode combinations) AND risk/conformal/backtest/region-comparison data
for the Streamlit app.

The app must never load models/yield_best.joblib (~528 MB) at request time --
build_crop_params() calls the yield model here, offline, and the result
(plus price/water/fert/cost derived figures) is written to
data/processed/crop_params_cache.json. The app and scripts/smoke_e2e.py read
ONLY this cache.

Phase 6 addition: also precompute the risk inputs (agriopt.optim.risk) --
the deviation matrix D, the per-crop CV table, and TWO Sigma variants
("frp_based": as measured, sugarcane's low FRP-driven std as-is;
"conservative": sugarcane's std replaced by the median of the other crops',
correlations unchanged -- see Phase 5.1's sugarcane sensitivity analysis)
-- so the app's risk-aware mode and Risk tab never recompute this from raw
data either.

Demo-hardening Item 4: also precomputes NSGA-II (Model A) and NSGA-III
(Model B, conservative-sugarcane-risk Sigma) results for the 5 farmer-
profile presets (app/presets.py) at the app's default settings -- the app
shows these instantly (labeled "cached") when the user's inputs exactly
match a preset, instead of re-running the optimizer.

Phase 10 additions (cache schema, all NEW top-level keys):

  cache["params"][region][water_basis][price_mode] -> records, for
      water_basis="total_need" (region-independent water need, per
      agriopt.data.reference.water_mm -- see docs/water.md; so this block is
      IDENTICAL across all 5 regions, kept per-region anyway for a
      consistent, uniform lookup shape rather than a special-cased branch in
      app/data.py).
  cache["params"][region]["net_irrigation"][rainfall_scenario][price_mode]
      -> records, for rainfall_scenario in {"normal","dry"} (this basis DOES
      vary by region -- agriopt.data.rainfall.net_irrigation_mm).

  Efficiency note: yield/price/cost/profit/fert (everything build_crop_params
  computes EXCEPT water_m3_ha) do not depend on water_basis/region/
  rainfall_scenario at all -- only water_m3_ha does. So build_crop_params()
  (which loads the ~528MB yield model) is called only ONCE PER PRICE MODE
  (2 calls total, same as before Phase 10), and all 5(region) x 2(basis
  variants: total_need is one water_m3_ha value, net_irrigation normal/dry
  are two more) x 2(price_mode) = 20 param-record variants are assembled by
  copying that single base row per price_mode and overriding only
  water_m3_ha (via agriopt.data.rainfall.net_irrigation_mm /
  agriopt.data.reference.water_mm directly) -- NOT by calling
  build_crop_params 20 times. This keeps the cache-build fast and the yield
  model loaded exactly twice, same as pre-Phase-10.

  cache["conformal"] = {"alpha": .., "q_overall": .., "q_per_crop": {...}}
      -- Phase 9's calibrated split-conformal quantiles (log1p-yield space),
      read directly from the committed reports/results/yield_conformal.csv
      (NOT from models/yield_conformal.json, which is gitignored and would
      break a fresh clone -- see item 2's deploy-readiness requirement).
      Consumed by app/components/recommendation.py to show per-crop 90%
      intervals without ever calling predict_yield_interval()/loading the
      conformal model live.

  cache["backtest"] = {"fairness": [...], "realized_profit_by_year": [...],
      "findings_bullets": [...]} -- Phase 7.1's backtest_fairness_v2.csv +
      a findings summary, read from the committed reports/results/*.csv/.md,
      for the new "Backtest (2016-2019)" tab.

  cache["region_comparison"] = {"konkan_strategies": [...],
      "marathwada_strategies": [...], "ours_summary": [...],
      "findings_bullets": [...]} -- Phase 8.1's region comparison, read from
      the committed reports/results/optim_strategies_{konkan,marathwada}.csv
      + region_comparison.md, for the new "Regional view" tab.

Run this any time crop_reference.csv, the yield model, the price model, or
any of the above committed reports/results/*.csv/.md files change.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Demo-hardening Item 1: see app/streamlit_app.py's matching block -- this
# script runs many repeated NSGA-II/NSGA-III optimizations in one process
# (4 presets x 2 models) to precompute the cache, same rationale applies.
for _env_var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ.setdefault(_env_var, "1")

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd

from agriopt.config import CROPS, DATA_PROCESSED, PRICE_MODEL_METADATA_PATH, REPORTS_RESULTS, YIELD_MODEL_METADATA_PATH
from agriopt.data.rainfall import REGIONS, net_irrigation_mm
from agriopt.data.reference import load_reference
from agriopt.models.price_model import load_price_metadata
from agriopt.models.yield_model import load_metadata
from agriopt.optim.baselines import historical_area_share
from agriopt.optim.params import MM_TO_M3_PER_HA, build_crop_params
from agriopt.optim.risk import build_risk_inputs, sigma_with_overridden_std
from app.pipeline import current_mix_water, run_pipeline, weights4_from_priority_and_risk_aversion, weights_from_priority
from app.presets import DEFAULT_FOOD_SHARE_MIN, DEFAULT_MAX_SHARE, DEFAULT_PRICE_MODE, DEFAULT_PRIORITY, DEFAULT_RISK_AVERSION, PRESETS
from agriopt.optim.problem import Scenario

CACHE_PATH = DATA_PROCESSED / "crop_params_cache.json"
PRICE_MODES = ["market", "msp_floor"]
RAINFALL_SCENARIOS = ["normal", "dry"]
RISK_PARAMS_MODE = "market"  # risk R_i (current expected revenue/ha) is computed from this price mode's params


def _records_from_df(df: pd.DataFrame) -> list[dict]:
    records = []
    for crop, row in df.iterrows():
        rec = row.to_dict()
        rec["crop"] = crop
        rec["seasons_occupied"] = sorted(rec["seasons_occupied"])
        records.append(rec)
    return records


def _build_params_block(base_df_by_mode: dict[str, pd.DataFrame]) -> dict:
    """See this script's module docstring for the full schema. Only
    water_m3_ha varies across region/water_basis/rainfall_scenario --
    yield/price/cost/profit/fert come from `base_df_by_mode` (already
    computed once per price mode with the default total_need/maharashtra
    basis, via build_crop_params) and are copied unchanged."""
    ref = load_reference()
    out: dict = {}
    for region in REGIONS:
        out[region] = {"total_need": {}, "net_irrigation": {s: {} for s in RAINFALL_SCENARIOS}}
        for mode, base_df in base_df_by_mode.items():
            # total_need: region-independent (agriopt.data.reference.water_mm
            # takes no region argument) -- identical to the base df.
            out[region]["total_need"][mode] = _records_from_df(base_df)

            for scenario in RAINFALL_SCENARIOS:
                df = base_df.copy()
                for crop in df.index:
                    df.loc[crop, "water_m3_ha"] = net_irrigation_mm(crop, scenario, ref, region) * MM_TO_M3_PER_HA
                out[region]["net_irrigation"][scenario][mode] = _records_from_df(df)
    return out


def _build_conformal_block() -> dict:
    """Reads the committed reports/results/yield_conformal.csv (Phase 9's
    per-crop split-conformal quantiles, log1p-yield space) -- NOT
    models/yield_conformal.json, which is gitignored (models/ is not
    committed) and would break a fresh clone. See scripts/92_conformal.py
    for how this CSV was produced."""
    path = REPORTS_RESULTS / "yield_conformal.csv"
    df = pd.read_csv(path)
    # Columns: crop, q_used (label: "overall" or "per_crop"), q_log1p (the
    # actual numeric log1p-space quantile), coverage, mean_width_orig, n.
    overall_row = df[df["crop"] == "ALL"].iloc[0]
    per_crop = {row["crop"]: float(row["q_log1p"]) for _, row in df.iterrows() if row["crop"] != "ALL"}
    return {
        "alpha": 0.10,
        "q_overall": float(overall_row["q_log1p"]),
        "q_per_crop": per_crop,
        "overall_coverage": float(overall_row["coverage"]),
        "note": "Phase 9 split-conformal (fit<=2012, calibrate 2013-2015); see RESULTS_INDEX.md E1.5.",
    }


def _build_backtest_block() -> dict:
    """Reads the committed Phase 7.1 backtest_fairness_v2.csv +
    backtest_summary_v2.md's realized-profit table + backtest_findings_v2.md
    -- see app/components/backtest_tab.py, which renders this block."""
    fairness_df = pd.read_csv(REPORTS_RESULTS / "backtest_fairness_v2.csv")
    fairness_records = fairness_df.to_dict(orient="records")

    b2_oracle_path = REPORTS_RESULTS / "backtest_b2_oracle_v2.csv"
    realized_records: list[dict] = []
    if b2_oracle_path.exists():
        realized_df = pd.read_csv(b2_oracle_path)
        realized_records = realized_df.to_dict(orient="records")

    findings_path = REPORTS_RESULTS / "backtest_findings_v2.md"
    findings_bullets = []
    if findings_path.exists():
        for line in findings_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("- **") or (line.startswith("- ") and "capture_ratio" in line):
                findings_bullets.append(line[2:])

    return {
        "fairness": fairness_records,
        "realized_profit_by_year": realized_records,
        "findings_bullets": findings_bullets,
    }


def _build_region_comparison_block() -> dict:
    """Reads the committed Phase 8.1 optim_strategies_{konkan,marathwada}.csv
    + region_comparison.md -- see app/components/regional_tab.py."""
    konkan_df = pd.read_csv(REPORTS_RESULTS / "optim_strategies_konkan.csv")
    marathwada_df = pd.read_csv(REPORTS_RESULTS / "optim_strategies_marathwada.csv")

    md_path = REPORTS_RESULTS / "region_comparison.md"
    findings_bullets = []
    ours_summary = []
    if md_path.exists():
        for line in md_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("- **") and "OURS profit=" in line:
                ours_summary.append({"line": line[2:]})
            elif line.startswith("- ") and not line.startswith("- **"):
                findings_bullets.append(line[2:])

    return {
        "konkan_strategies": konkan_df.to_dict(orient="records"),
        "marathwada_strategies": marathwada_df.to_dict(orient="records"),
        "ours_summary": ours_summary,
        "findings_bullets": findings_bullets,
    }


def _build_risk_block(params_market) -> dict:
    ri = build_risk_inputs(params_market, crops=CROPS)
    crops = ri.crops
    R = (params_market.loc[crops, "yield_qtl_ha"] * params_market.loc[crops, "price"]).to_numpy(dtype=float)

    other_stds = [float(ri.deviation_matrix[c].std()) for c in crops if c != "sugarcane"]
    median_other_std = float(np.median(other_stds))
    sugarcane_std_measured = float(ri.deviation_matrix["sugarcane"].std())
    Sigma_conservative, _ = sigma_with_overridden_std(ri, R, {"sugarcane": median_other_std})

    deviation_records = []
    for year, row in ri.deviation_matrix.iterrows():
        rec = {"year": int(year)}
        for crop in crops:
            v = row[crop]
            rec[crop] = None if (v is None or (isinstance(v, float) and np.isnan(v))) else float(v)
        deviation_records.append(rec)

    return {
        "crops": crops,
        "R": R.tolist(),
        "deviation_matrix": deviation_records,
        "cv_table": ri.cv_table.reset_index().rename(columns={"index": "crop"}).to_dict(orient="records"),
        "min_eigenvalue_raw": ri.min_eigenvalue_raw,
        "sugarcane_std_measured": sugarcane_std_measured,
        "median_other_std": median_other_std,
        "Sigma": {
            "frp_based": ri.Sigma.tolist(),
            "conservative": Sigma_conservative.tolist(),
        },
    }


def _serialize_result(result) -> dict:
    if not result.feasible:
        return {"feasible": False, "message": result.message}
    return {
        "feasible": True,
        "x": {k: v.tolist() for k, v in result.x.items() if v is not None},
        "evals": {k: v for k, v in result.evals.items() if v is not None},
        "X_front": result.X_front.tolist() if result.X_front is not None else [],
        "F_front": result.F_front.tolist() if result.F_front is not None else [],
        "nsga_runtime": result.nsga_runtime,
        "risk_aware_failed": result.risk_aware_failed,
    }


def _params_df_for_preset(params_block: dict, preset: dict, mode: str) -> pd.DataFrame:
    """Looks up the params variant matching one preset's own
    region/water_basis/rainfall_scenario (Phase 10 -- each preset can now
    request a different region/water_basis, not just Maharashtra/
    total_need) from `params_block` (== cache["params"], already built by
    _build_params_block)."""
    region = preset.get("region", "maharashtra")
    water_basis = preset.get("water_basis", "net_irrigation")
    rainfall_scenario = preset.get("rainfall_scenario", "normal")
    records = params_block[region][water_basis]
    if water_basis == "net_irrigation":
        records = records[rainfall_scenario]
    records = records[mode]
    df = pd.DataFrame(records).set_index("crop")
    df["seasons_occupied"] = df["seasons_occupied"].apply(set)
    return df


def _build_preset_results(params_block: dict, Sigma_conservative: np.ndarray, current_mix_share: dict[str, float]) -> dict:
    """DEFAULT_LAND_HA import kept local to avoid an unused-import lint hit
    when this function is the only caller."""
    from app.presets import DEFAULT_LAND_HA

    weights = weights_from_priority(DEFAULT_PRIORITY)
    weights4 = weights4_from_priority_and_risk_aversion(DEFAULT_PRIORITY, DEFAULT_RISK_AVERSION)

    preset_results = {}
    for name, preset in PRESETS.items():
        params_df = _params_df_for_preset(params_block, preset, DEFAULT_PRICE_MODE)
        land_ha = float(preset["land_ha"]) if preset["land_ha"] is not None else DEFAULT_LAND_HA
        water_budget = preset["water_mult"] * current_mix_water(params_df, land_ha, current_mix_share=current_mix_share)
        scenario = Scenario(
            water_budget_m3=water_budget,
            land_ha=land_ha,
            food_share_min=DEFAULT_FOOD_SHARE_MIN,
            max_share=DEFAULT_MAX_SHARE,
            price_mode=DEFAULT_PRICE_MODE,
            water_basis=preset.get("water_basis", "net_irrigation"),
            rainfall_scenario=preset.get("rainfall_scenario", "normal"),
            region=preset.get("region", "maharashtra"),
        )
        print(f"  preset={name!r}: land={land_ha} water_budget={water_budget:.1f} region={scenario.region} basis={scenario.water_basis}")

        result_normal = run_pipeline(params_df, scenario, weights, seed=42, current_mix_share=current_mix_share)
        result_risk_aware = run_pipeline(
            params_df, scenario, weights, risk_aware=True, weights4=weights4, Sigma=Sigma_conservative, seed=42,
            current_mix_share=current_mix_share,
        )

        preset_results[name] = {
            "land_ha": land_ha,
            "water_budget_m3": water_budget,
            "normal": _serialize_result(result_normal),
            "risk_aware": _serialize_result(result_risk_aware),
        }

    return preset_results


def main() -> None:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    print(f"Loading yield model metadata from {YIELD_MODEL_METADATA_PATH} ...")
    yield_meta = load_metadata()
    print(f"Loading price model metadata from {PRICE_MODEL_METADATA_PATH} ...")
    price_meta = load_price_metadata()

    cache = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "crops": CROPS,
        "regions": list(REGIONS),
        "yield_model_metadata": yield_meta,
        "price_model_metadata": price_meta,
    }

    # Base params (yield/price/cost/profit/fert), computed ONCE per price
    # mode with the default total_need/maharashtra basis -- the yield model
    # (~528MB) is loaded exactly twice total, same as pre-Phase-10. Every
    # region x water_basis x rainfall_scenario variant below reuses these
    # rows, only overriding water_m3_ha (see _build_params_block's docstring).
    params_by_mode = {}
    for mode in PRICE_MODES:
        print(f"\n-- building base crop params for price_mode={mode} --")
        params_by_mode[mode] = build_crop_params(mode, crops=CROPS, verbose=True)

    print("\n-- assembling region x water_basis x price_mode params variants --")
    cache["params"] = _build_params_block(params_by_mode)
    # Backward-compatible flat alias, at Scenario's own class-level DEFAULT
    # basis (total_need/maharashtra, NOT the app's own net_irrigation
    # default -- see agriopt.optim.problem.Scenario's docstring) -- kept so
    # every pre-Phase-10 script/test that reads raw["price_modes"][mode] and
    # constructs a bare Scenario(...) (which defaults to water_basis=
    # "total_need") keeps seeing byte-for-byte the same params_df it always
    # has (tests/test_app_smoke.py's infeasibility checks specifically
    # depend on total_need's much larger per-ha water figures).
    cache["price_modes"] = cache["params"]["maharashtra"]["total_need"]

    print(f"\n-- building risk inputs (Sigma, deviation matrix) from price_mode={RISK_PARAMS_MODE} params --")
    cache["risk"] = _build_risk_block(params_by_mode[RISK_PARAMS_MODE])

    print("\n-- building conformal, backtest, region-comparison blocks from committed reports/results/*.csv/.md --")
    cache["conformal"] = _build_conformal_block()
    cache["backtest"] = _build_backtest_block()
    cache["region_comparison"] = _build_region_comparison_block()

    # Phase 10 deploy-readiness: agriopt.optim.baselines.current_mix() (the
    # B1 baseline, ALWAYS computed by app/pipeline.py's run_pipeline) reads
    # data/processed/yield_clean.parquet directly -- gitignored, not part of
    # this cache otherwise, and NOT present in a fresh clone (verified: a
    # fresh-clone + fresh-venv smoke test failed on exactly this before this
    # block was added). Precomputed here, once, from the full dataset this
    # script has access to; the app always passes it through to current_mix()
    # instead of ever reading the parquet itself.
    print("\n-- precomputing current-mix (B1) historical area shares --")
    cache["current_mix_shares"] = historical_area_share(CROPS)

    print(f"\n-- precomputing preset results (NSGA-II + NSGA-III, {len(PRESETS)} presets) --")
    Sigma_conservative = np.array(cache["risk"]["Sigma"]["conservative"], dtype=float)
    cache["preset_results"] = _build_preset_results(cache["params"], Sigma_conservative, cache["current_mix_shares"])

    CACHE_PATH.write_text(json.dumps(cache, indent=2, default=str), encoding="utf-8")
    size_mb = CACHE_PATH.stat().st_size / 1e6
    print(f"\nWrote {CACHE_PATH} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    sys.exit(main())
