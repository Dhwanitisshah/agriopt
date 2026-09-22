"""Fetch Maharashtra state-level monthly mandi prices from the CEDA Agmarknet
API (primary price source) for the 7 target crops that have a mandi series
(sugarcane is excluded -- FRP admin price instead, see crop_reference.csv).

Resolves commodity/state IDs dynamically against the live API (never
hardcoded/guessed), does one test call first and prints its shape, then runs
the full fetch loop with on-disk caching. Merges in the Kaggle mandi CSV as a
secondary source (CEDA wins on overlap) and writes
data/processed/prices_monthly.parquet.

Rate limiting: the live API enforces 40 requests/rolling-hour
(`RateLimit-Policy: 40;w=3600` response header) -- NOT the 1 req/sec
originally assumed. It also does NOT enforce a 1-year request-window limit
(verified: multi-year single requests succeed). So instead of one request per
crop-year (189 requests, ~5x the hourly budget), this fetches CEDA_CHUNK_YEARS
(7) at a time -- ~4 requests/crop, ~28 total, comfortably under budget. Raw
JSON is cached per (crop, chunk) in data/raw/prices_ceda/ and skipped on
rerun. On a 429, the client raises CedaRateLimitError with the server's own
Retry-After; this script waits that long and resumes the same chunk rather
than treating it as fatal.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date

import pandas as pd

from agriopt.config import (
    CEDA_CHUNK_YEARS,
    CEDA_END_DATE,
    CEDA_MAHARASHTRA_STATE_ID,
    CEDA_RAW_DIR,
    CEDA_START_YEAR,
    DATA_PROCESSED,
    PRICES_MONTHLY_PARQUET,
    STATE,
)
from agriopt.data.ceda_client import (
    CedaApiError,
    CedaAuthError,
    CedaClient,
    CedaRateLimitError,
    resolve_commodity_id,
    resolve_state_id,
)
from agriopt.data.price_data import (
    CEDA_COMMODITY_NAME,
    CEDA_TRACKED_CROPS,
    build_monthly_prices_ceda,
    build_monthly_prices_kaggle,
    filter_target,
    load_raw_prices,
    merge_price_sources,
)

CEDA_END_YEAR = int(CEDA_END_DATE[:4])
RATE_LIMIT_WAIT_BUFFER_SECONDS = 15
MAX_RATE_LIMIT_WAITS = 5


def year_chunks(start_year: int, end_year: int, chunk_years: int) -> list[tuple[str, str]]:
    """[(from_date, to_date), ...] covering start_year..end_year in
    chunk_years-sized calendar-year windows, last window clipped to CEDA_END_DATE."""
    chunks = []
    year = start_year
    while year <= end_year:
        chunk_end_year = min(year + chunk_years - 1, end_year)
        from_date = f"{year}-01-01"
        to_date = f"{chunk_end_year}-12-31" if chunk_end_year < end_year else CEDA_END_DATE
        chunks.append((from_date, to_date))
        year = chunk_end_year + 1
    return chunks


def fetch_with_rate_limit_retry(fn, *args, **kwargs):
    """Call fn(*args, **kwargs); on CedaRateLimitError, sleep for the server's
    Retry-After (+ buffer) and retry, up to MAX_RATE_LIMIT_WAITS times."""
    for attempt in range(1, MAX_RATE_LIMIT_WAITS + 1):
        try:
            return fn(*args, **kwargs)
        except CedaRateLimitError as exc:
            wait_s = (exc.retry_after_seconds or 3600) + RATE_LIMIT_WAIT_BUFFER_SECONDS
            print(f"  Rate limited (attempt {attempt}/{MAX_RATE_LIMIT_WAITS}): "
                  f"waiting {wait_s}s for the CEDA quota window to reset ...")
            time.sleep(wait_s)
    raise CedaApiError(f"Still rate limited after {MAX_RATE_LIMIT_WAITS} waits -- giving up.")


def fetch_chunk(client: CedaClient, crop: str, commodity_id: int, state_id: int, from_date: str, to_date: str) -> list[dict]:
    """Fetch (or load from cache) one crop's daily state-level records for one
    date chunk."""
    cache_path = CEDA_RAW_DIR / f"{crop}_{from_date}_{to_date}.json"
    if cache_path.exists():
        with open(cache_path, encoding="utf-8") as f:
            return json.load(f)

    records = fetch_with_rate_limit_retry(
        client.get_prices, commodity_id, state_id, from_date=from_date, to_date=to_date
    )

    CEDA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(records, f)

    return records


def main() -> None:
    CEDA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    try:
        client = CedaClient()
    except CedaAuthError as exc:
        print(f"STOP: {exc}")
        sys.exit(1)

    print("Fetching commodity list ...")
    try:
        commodities = fetch_with_rate_limit_retry(client.get_commodities)
    except (CedaAuthError, CedaApiError) as exc:
        print(f"STOP: CEDA API unusable -- {exc}")
        print("Fallback: the unofficial `agmarknet` PyPI package.")
        sys.exit(1)
    print(f"  {len(commodities)} commodities available.")

    print("Fetching geographies ...")
    geographies = fetch_with_rate_limit_retry(client.get_geographies)
    try:
        state_id = resolve_state_id(STATE, geographies)
    except ValueError as exc:
        print(f"STOP: {exc}")
        sys.exit(1)
    print(f"  {STATE} state_id = {state_id}")
    if state_id != CEDA_MAHARASHTRA_STATE_ID:
        print(f"  NOTE: differs from config.CEDA_MAHARASHTRA_STATE_ID={CEDA_MAHARASHTRA_STATE_ID}; using resolved value.")

    print(f"\nResolving commodity IDs for {len(CEDA_TRACKED_CROPS)} crops ...")
    commodity_ids: dict[str, int] = {}
    unresolved = []
    for crop in CEDA_TRACKED_CROPS:
        query = CEDA_COMMODITY_NAME[crop]
        try:
            cid = resolve_commodity_id(query, commodities)
            commodity_ids[crop] = cid
            print(f"  {crop:10s} -> {query!r:35s} commodity_id={cid}")
        except ValueError as exc:
            unresolved.append(crop)
            print(f"  {crop:10s} -> AMBIGUOUS/MISSING: {exc}")

    if unresolved:
        print(f"\nSTOP: could not resolve CEDA commodity IDs for: {unresolved}. "
              "Fix CROP_NAME_MAP['<crop>']['ceda_commodity'] in config.py against the "
              "printed matches above, then rerun.")
        sys.exit(1)

    # --- test ONE call first (Wheat, 1 year) --------------------------------
    test_year = date.today().year - 1
    print(f"\nTest call: Wheat, {STATE}, {test_year} ...")
    test_records = fetch_chunk(
        client, "wheat", commodity_ids["wheat"], state_id, f"{test_year}-01-01", f"{test_year}-12-31"
    )
    print(f"  n_records={len(test_records)}")
    if test_records:
        print(f"  fields: {sorted(test_records[0].keys())}")
        print(f"  first: {test_records[0]}")
        print(f"  last:  {test_records[-1]}")
    else:
        print("  WARNING: test call returned 0 records.")

    # --- full fetch loop, chunked by CEDA_CHUNK_YEARS, cached per crop-chunk ---
    chunks = year_chunks(CEDA_START_YEAR, CEDA_END_YEAR, CEDA_CHUNK_YEARS)
    print(f"\nFull fetch loop: {len(CEDA_TRACKED_CROPS)} crops x {len(chunks)} chunks "
          f"({CEDA_START_YEAR}-{CEDA_END_YEAR}, {CEDA_CHUNK_YEARS}-year windows) "
          f"= {len(CEDA_TRACKED_CROPS) * len(chunks)} requests max ...")
    ceda_frames = []
    for crop in CEDA_TRACKED_CROPS:
        crop_records: list[dict] = []
        n_fetched = 0
        n_cached = 0
        for from_date, to_date in chunks:
            cache_path = CEDA_RAW_DIR / f"{crop}_{from_date}_{to_date}.json"
            was_cached = cache_path.exists()
            records = fetch_chunk(client, crop, commodity_ids[crop], state_id, from_date, to_date)
            crop_records.extend(records)
            if was_cached:
                n_cached += 1
            else:
                n_fetched += 1
        print(f"  {crop:10s} {len(crop_records):6d} daily records "
              f"({n_fetched} chunks fetched, {n_cached} cached)")
        ceda_frames.append(build_monthly_prices_ceda(crop_records, crop))

    ceda_monthly = pd.concat(ceda_frames, ignore_index=True) if ceda_frames else pd.DataFrame()

    # --- secondary: Kaggle mandi CSV ----------------------------------------
    print("\nLoading Kaggle mandi CSV as secondary source ...")
    kaggle_raw = load_raw_prices()
    kaggle_target = filter_target(kaggle_raw, state=STATE)
    kaggle_monthly = build_monthly_prices_kaggle(kaggle_target)
    print(f"  Kaggle secondary: {len(kaggle_monthly)} crop-month rows "
          f"across {sorted(kaggle_monthly['crop'].unique())}")

    combined = merge_price_sources(ceda_monthly, kaggle_monthly)
    combined.to_parquet(PRICES_MONTHLY_PARQUET, index=False)
    print(f"\nWrote {PRICES_MONTHLY_PARQUET} ({len(combined)} rows).")

    for crop in CEDA_TRACKED_CROPS:
        sub = combined[combined["crop"] == crop]
        sources = sub["source"].value_counts().to_dict()
        print(f"  {crop:10s} {len(sub):4d} months  sources={sources}")


if __name__ == "__main__":
    sys.exit(main())
