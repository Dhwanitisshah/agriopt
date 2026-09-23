"""Phase 4: precompute crop params (both price modes) for the Streamlit app.

The app must never load models/yield_best.joblib (~528 MB) at request time --
build_crop_params() calls the yield model once per crop here, offline, and
the result (plus price/water/fert/cost derived figures) is written to
data/processed/crop_params_cache.json. The app and scripts/smoke_e2e.py read
ONLY this cache.

Run this any time crop_reference.csv, the yield model, or the price model
changes.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

from agriopt.config import CROPS, DATA_PROCESSED, PRICE_MODEL_METADATA_PATH, YIELD_MODEL_METADATA_PATH
from agriopt.models.price_model import load_price_metadata
from agriopt.models.yield_model import load_metadata
from agriopt.optim.params import build_crop_params

CACHE_PATH = DATA_PROCESSED / "crop_params_cache.json"
PRICE_MODES = ["market", "msp_floor"]


def _records(price_mode: str) -> list[dict]:
    df = build_crop_params(price_mode, crops=CROPS, verbose=True)
    records = []
    for crop, row in df.iterrows():
        rec = row.to_dict()
        rec["crop"] = crop
        rec["seasons_occupied"] = sorted(rec["seasons_occupied"])
        records.append(rec)
    return records


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

    for mode in PRICE_MODES:
        print(f"\n-- building crop params for price_mode={mode} --")
        cache["price_modes"][mode] = _records(mode)

    CACHE_PATH.write_text(json.dumps(cache, indent=2, default=str), encoding="utf-8")
    print(f"\nWrote {CACHE_PATH}")


if __name__ == "__main__":
    sys.exit(main())
