# AgriOpt

Multi-objective crop planning for Maharashtra.

Pipeline: yield model + price model -> NSGA-II (pymoo) allocates hectares across crops -> Streamlit UI.

## Phase 0 status

Scaffold, data acquisition, and leakage audit only. No models, no UI logic yet.

## Setup (Windows / PowerShell, Python 3.11)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
```

## Data

Kaggle auth is required before downloading data. Create `$HOME\.kaggle\access_token`
(or `access_token.txt`, or `kaggle.json`, or set `$env:KAGGLE_API_TOKEN`), then run:

```powershell
.\scripts\00_download.ps1
python scripts\01_audit_yield.py
python scripts\02_audit_prices.py
```

Audit reports and plots land in `reports/eda/`.

## Tests

```powershell
pytest -q
```

## Layout

- `src/agriopt/` — importable package (config, data loaders/cleaners)
- `scripts/` — one-off download/audit scripts
- `data/raw/` — downloaded, gitignored
- `data/processed/` — cleaned parquet, gitignored
- `data/reference/` — hand-curated reference tables, committed
- `docs/formulation.md` — optimization problem formulation
- `app/streamlit_app.py` — UI placeholder
