"""Re-derive the committed cache's per-crop economics with
agriopt.optim.params.economic_row() WITHOUT the gitignored yield/price
models, then re-solve the cached farmer presets.

Why this exists: crop_params_cache.json is normally built by
scripts/40_build_cache.py, which needs the ~528 MB yield model. The
economics fixes (sugarcane annualized over its ~15-month cycle, FRP net of
harvesting & transport, non-zero sugarcane profit risk) only change how
cached yield/price/cost/water/fert are combined -- not the model outputs --
so they can be applied to the cached rows directly.

Idempotent: rows already carrying `cycle_months` are treated as already
converted and are left alone, so running this twice changes nothing.

Run:  python scripts/42_patch_cache_economics.py
A full `python scripts/40_build_cache.py` (with models present) produces the
same economics, because both paths go through economic_row().
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

for _env_var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ.setdefault(_env_var, "1")

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np

from agriopt.config import DATA_PROCESSED
from agriopt.data.reference import load_reference
from agriopt.optim.params import economic_row, profit_std_for

CACHE_PATH = DATA_PROCESSED / "crop_params_cache.json"

STALE_NOTE = (
    "NOTE (cache patched {date}): these figures were produced before two fixes -- the backtest "
    "subtracted cost in Rs/quintal as if it were Rs/ha (so 'profit' was ~revenue), and sugarcane "
    "was not annualized / not net of harvesting & transport. Treat them as superseded until "
    "scripts/60_backtest.py, 61_backtest_v2.py, 70/71_water_*.py are re-run with the full dataset."
)


def _load_build_cache_module():
    spec = importlib.util.spec_from_file_location("build_cache", REPO_ROOT / "scripts" / "40_build_cache.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def convert_record(rec: dict, ref) -> dict:
    """One cached (per-cycle, gross-price) record -> economic_row() record."""
    if "cycle_months" in rec:
        return rec
    crop = rec["crop"]
    y = float(rec["yield_qtl_ha"])
    new = economic_row(
        crop,
        yield_per_cycle_qtl_ha=y,
        gross_price=float(rec["price"]),
        cost_rs_per_qtl=float(rec["cost_ha"]) / y if y else 0.0,
        water_m3_per_cycle=float(rec["water_m3_ha"]),
        fert_kg_per_cycle=float(rec["fert_kg_ha"]),
        ref=ref,
    )
    new["seasons_occupied"] = rec["seasons_occupied"]
    if crop == "sugarcane":
        new["profit_std_ha"] = profit_std_for(crop, new, None)
    else:
        # unchanged crops (cycle 12, no deduction): price std already in the record
        new["profit_std_ha"] = float(rec["profit_std_ha"])
    return new


def _walk_records(node, ref):
    if isinstance(node, list):
        return [convert_record(r, ref) for r in node]
    return {k: _walk_records(v, ref) for k, v in node.items()}


def rescale_risk(cache: dict) -> None:
    """Sigma_ij = cov(dev_i, dev_j) * R_i * R_j, with R_i the expected
    revenue/ha. Sugarcane's R changed, so rescale its row/column."""
    risk = cache["risk"]
    crops = risk["crops"]
    market = {r["crop"]: r for r in cache["price_modes"]["market"]}
    R_old = np.array(risk["R"], dtype=float)
    R_new = R_old.copy()
    for i, c in enumerate(crops):
        if c == "sugarcane":
            R_new[i] = market[c]["yield_qtl_ha"] * market[c]["price"]
    if np.allclose(R_old, R_new):
        return
    s = R_new / R_old
    for key, S in risk["Sigma"].items():
        S = np.array(S, dtype=float) * np.outer(s, s)
        risk["Sigma"][key] = S.tolist()
    risk["R"] = R_new.tolist()


def main() -> None:
    cache = json.loads(CACHE_PATH.read_text())
    ref = load_reference()
    date = datetime.now(timezone.utc).date().isoformat()

    cache["price_modes"] = _walk_records(cache["price_modes"], ref)
    cache["params"] = _walk_records(cache["params"], ref)
    rescale_risk(cache)

    for block in ("backtest", "region_comparison"):
        bullets = cache.get(block, {}).get("findings_bullets")
        if isinstance(bullets, list) and not (bullets and str(bullets[0]).startswith("NOTE (cache patched")):
            bullets.insert(0, STALE_NOTE.format(date=date))

    print("-- re-solving presets with the patched economics --")
    bc = _load_build_cache_module()
    cache["preset_results"] = bc._build_preset_results(cache["params"], cache["risk"], cache["current_mix_shares"])
    cache["economics_patched_at"] = datetime.now(timezone.utc).isoformat()

    CACHE_PATH.write_text(json.dumps(cache, indent=2, default=str), encoding="utf-8")
    print(f"wrote {CACHE_PATH}")


if __name__ == "__main__":
    main()
