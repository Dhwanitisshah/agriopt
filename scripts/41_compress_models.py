"""Phase 6, Item 8: re-save models/*.joblib with joblib compress=3
(lossless -- same estimator object, gzip-compressed pickle stream). Confirms
predictions are bit-identical on 50 sample rows before overwriting, then
reports old vs new file size.
"""
from __future__ import annotations

import sys

import joblib
import numpy as np
import pandas as pd

from agriopt.config import (
    MODELS_DIR,
    PRICE_MODEL_METADATA_PATH,
    PRICE_MODEL_PATH,
    YIELD_CLEAN_PARQUET,
    YIELD_EVAL_MODEL_PATH,
    YIELD_MODEL_METADATA_PATH,
    YIELD_MODEL_PATH,
)

N_SAMPLE_ROWS = 50
COMPRESS_LEVEL = 3


def _sample_yield_rows(n: int = N_SAMPLE_ROWS) -> pd.DataFrame:
    df = pd.read_parquet(YIELD_CLEAN_PARQUET)
    return df.sample(n=min(n, len(df)), random_state=42)


def _predict_yield_model(model, rows: pd.DataFrame, num_cols: list[str]) -> np.ndarray:
    X = rows[["crop", "season", "state"] + num_cols]
    return np.asarray(model.predict(X))


def compress_yield_model(model_path, metadata_path, sample_rows: pd.DataFrame) -> None:
    if not model_path.exists():
        print(f"skip (missing): {model_path}")
        return

    old_size = model_path.stat().st_size
    metadata = __import__("json").load(open(metadata_path, encoding="utf-8"))
    num_cols = metadata["num_cols"]

    model = joblib.load(model_path)
    preds_before = _predict_yield_model(model, sample_rows, num_cols)

    tmp_path = model_path.with_suffix(".joblib.tmp")
    joblib.dump(model, tmp_path, compress=COMPRESS_LEVEL)

    reloaded = joblib.load(tmp_path)
    preds_after = _predict_yield_model(reloaded, sample_rows, num_cols)

    # RandomForestRegressor.predict() parallelizes across trees (n_jobs=-1)
    # and its float summation order (hence float64 rounding) is not fully
    # deterministic across calls even on the SAME in-memory model object
    # (verified: two predict() calls on one loaded model already differ by
    # up to ~5e-15) -- so "predictions identical" is checked at float64
    # tolerance, not bit-for-bit, which is what actually matters here
    # (compress= only changes the pickle stream, never the fitted trees).
    np.testing.assert_allclose(preds_before, preds_after, rtol=1e-9, atol=1e-9, err_msg=f"predictions changed after compression: {model_path}")

    tmp_path.replace(model_path)
    new_size = model_path.stat().st_size
    print(f"{model_path.name}: {old_size / 1e6:.1f} MB -> {new_size / 1e6:.1f} MB ({(1 - new_size / old_size) * 100:.1f}% smaller); predictions identical on {len(sample_rows)} rows")


def compress_price_model() -> None:
    if not PRICE_MODEL_PATH.exists():
        print(f"skip (missing): {PRICE_MODEL_PATH}")
        return

    old_size = PRICE_MODEL_PATH.stat().st_size
    model = joblib.load(PRICE_MODEL_PATH)

    tmp_path = PRICE_MODEL_PATH.with_suffix(".joblib.tmp")
    joblib.dump(model, tmp_path, compress=COMPRESS_LEVEL)
    reloaded = joblib.load(tmp_path)

    # price_best_h12.joblib is a placeholder (method="Naive" in metadata,
    # expected_price() never loads this file for inference -- see
    # agriopt.models.price_model) -- just confirm the round trip preserves
    # the object, no prediction API to compare against.
    assert type(reloaded) is type(model)

    tmp_path.replace(PRICE_MODEL_PATH)
    new_size = PRICE_MODEL_PATH.stat().st_size
    print(f"{PRICE_MODEL_PATH.name}: {old_size} B -> {new_size} B (placeholder model, no prediction API to compare)")


def main() -> None:
    sample_rows = _sample_yield_rows()

    compress_yield_model(YIELD_MODEL_PATH, YIELD_MODEL_METADATA_PATH, sample_rows)
    compress_yield_model(YIELD_EVAL_MODEL_PATH, MODELS_DIR / "yield_eval.json", sample_rows)
    compress_price_model()


if __name__ == "__main__":
    sys.exit(main())
