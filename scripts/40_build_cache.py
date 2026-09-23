"""Phase 4/6: precompute crop params (both price modes) AND risk data for
the Streamlit app.

The app must never load models/yield_best.joblib (~528 MB) at request time --
build_crop_params() calls the yield model once per crop here, offline, and
the result (plus price/water/fert/cost derived figures) is written to
data/processed/crop_params_cache.json. The app and scripts/smoke_e2e.py read
ONLY this cache.

Phase 6 addition: also precompute the risk inputs (agriopt.optim.risk) --
the deviation matrix D, the per-crop CV table, and TWO Sigma variants
("frp_based": as measured, sugarcane's low FRP-driven std as-is;
"conservative": sugarcane's std replaced by the median of the other crops',
correlations unchanged -- see Phase 5.1's sugarcane sensitivity analysis)
-- so the app's risk-aware mode and Risk tab never recompute this from raw
data either.

Run this any time crop_reference.csv, the yield model, or the price model
changes.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

import numpy as np

from agriopt.config import CROPS, DATA_PROCESSED, PRICE_MODEL_METADATA_PATH, YIELD_MODEL_METADATA_PATH
from agriopt.models.price_model import load_price_metadata
from agriopt.models.yield_model import load_metadata
from agriopt.optim.params import build_crop_params
from agriopt.optim.risk import build_risk_inputs, sigma_with_overridden_std

CACHE_PATH = DATA_PROCESSED / "crop_params_cache.json"
PRICE_MODES = ["market", "msp_floor"]
RISK_PARAMS_MODE = "market"  # risk R_i (current expected revenue/ha) is computed from this price mode's params


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


def main() -> None:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    print(f"Loading yield model metadata from {YIELD_MODEL_METADATA_PATH} ...")
    yield_meta = load_metadata()
    print(f"Loading price model metadata from {PRICE_MODEL_METADATA_PATH} ...")
    price_meta = load_price_metadata()

    cache = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "crops": CROPS,
        "yield_model_metadata": yield_meta,
        "price_model_metadata": price_meta,
        "price_modes": {},
    }

    params_by_mode = {}
    for mode in PRICE_MODES:
        print(f"\n-- building crop params for price_mode={mode} --")
        df = build_crop_params(mode, crops=CROPS, verbose=True)
        params_by_mode[mode] = df
        records = []
        for crop, row in df.iterrows():
            rec = row.to_dict()
            rec["crop"] = crop
            rec["seasons_occupied"] = sorted(rec["seasons_occupied"])
            records.append(rec)
        cache["price_modes"][mode] = records

    print(f"\n-- building risk inputs (Sigma, deviation matrix) from price_mode={RISK_PARAMS_MODE} params --")
    cache["risk"] = _build_risk_block(params_by_mode[RISK_PARAMS_MODE])

    CACHE_PATH.write_text(json.dumps(cache, indent=2, default=str), encoding="utf-8")
    print(f"\nWrote {CACHE_PATH}")


if __name__ == "__main__":
    sys.exit(main())
