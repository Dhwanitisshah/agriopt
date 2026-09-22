# AgriOpt

Multi-objective crop planning for Maharashtra.

Pipeline: yield model + price model -> NSGA-II (pymoo) allocates hectares across crops -> Streamlit UI.

## Phase 0 / 0.5 status

Scaffold, data acquisition, unit/leakage audit, and price sourcing only. No models, no UI logic yet.

## Setup (Windows / PowerShell)

Python 3.11 was requested but is not installed on this machine; the venv was
built on **Python 3.13** instead (only version available). Install worked
without issues.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
```

## Data

### Yield (Kaggle)

Kaggle auth is required before downloading data. Create `$HOME\.kaggle\access_token`
(or `access_token.txt`, or `kaggle.json`, or set `$env:KAGGLE_API_TOKEN`), then run:

```powershell
.\scripts\00_download.ps1
python scripts\01_audit_yield.py
```

### Prices (CEDA Agmarknet API, primary; Kaggle mandi CSV, secondary)

Primary price source is the [CEDA Agmarknet API](https://api.ceda.ashoka.edu.in/documentation/).
Requires `CEDA_API_KEY` in `.env` (copy `.env.example`; get a key from CEDA).
The key is loaded via `python-dotenv` and is never printed, logged, or
included in exception messages.

```powershell
python scripts\03_fetch_ceda_prices.py
python scripts\02_audit_prices.py
```

`03_fetch_ceda_prices.py` resolves commodity/state IDs against the live API
(never hardcoded), does one test call first and prints its shape, then fetches
full history in yearly chunks per crop, caching raw JSON in
`data/raw/prices_ceda/` (chunks already on disk are skipped on rerun), rate
limited to 1 request/sec with retry-with-backoff on 429/5xx. It merges in the
Kaggle mandi CSV as a secondary source (CEDA wins where both have data) and
writes `data/processed/prices_monthly.parquet`.

Sugarcane has no mandi series (sold to mills at the government-set FRP) --
see `admin_price_rs_per_qtl` in `data/reference/crop_reference.csv`.

Audit reports and plots land in `reports/eda/`.

## Tests

```powershell
pytest -q
```

## Layout

- `src/agriopt/` — importable package (config, data loaders/cleaners, CEDA client)
- `scripts/` — one-off download/fetch/audit scripts
- `data/raw/` — downloaded, gitignored
- `data/raw/prices_ceda/` — cached raw CEDA API responses, gitignored
- `data/processed/` — cleaned parquet, gitignored
- `data/reference/` — hand-curated reference tables, committed
- `docs/formulation.md` — optimization problem formulation
- `docs/units.md` — Yield -> quintals-of-marketed-product unit conversions
- `app/streamlit_app.py` — UI placeholder
