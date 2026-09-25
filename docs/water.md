# Effective rainfall and net irrigation requirement (Phase 8)

Phases 1-7 used `agriopt.data.reference.water_mm()` -- the FAO TM3 **total
crop water requirement** (crop evapotranspiration over the growing season) --
as `water_m3_ha` throughout the optimizer, backtest, and risk pipeline. As
`agriopt.optim.params`'s module docstring already flagged, this **overstates
the irrigation water actually drawn** for rainfed/partially-rainfed crops:
during the Kharif (monsoon) season Maharashtra typically receives most of a
crop's total water need as rainfall, so treating the whole FAO TM3 figure as
an "irrigation budget" penalizes rainfed kharif crops unfairly relative to
irrigation-dependent Rabi crops or a 12-month crop like sugarcane.

This document covers the Phase 8 fix: computing a **net irrigation
requirement** (water need minus effective rainfall the crop's own growing
season actually receives) as an alternative `water_m3_ha` basis, selectable
via `Scenario.water_basis` (`agriopt.optim.problem.Scenario`), without
changing any existing (`"total_need"`) result.

## 1. Rainfall data source

**Source**: IMD (India Meteorological Department) sub-divisional monthly
rainfall, 1901-2015, via Kaggle dataset `rajanand/rainfall-in-india`
(`data/raw/rainfall/rainfall in india 1901-2015.csv`). Columns: `SUBDIVISION`,
`YEAR`, `JAN`..`DEC` (mm), plus seasonal aggregate columns not used here.

**Verified** to contain all 4 of Maharashtra's IMD meteorological
subdivisions, with complete (no missing years/months) monthly data
1901-2015 for each:

- `KONKAN & GOA`
- `MADHYA MAHARASHTRA`
- `MATATHWADA` -- this is the dataset's OWN spelling (it means Marathwada;
  kept verbatim in `agriopt.data.rainfall.MAHARASHTRA_SUBDIVISIONS` so the
  filter matches the raw `SUBDIVISION` column exactly -- ASSUMPTION: this is
  a dataset typo, not a distinct subdivision, confirmed by there being no
  separately-spelled "Marathwada" row and by IMD's well-known 4-subdivision
  breakdown of Maharashtra).
- `VIDARBHA`

## 2. Maharashtra monthly rainfall (ASSUMPTION: unweighted mean)

Maharashtra's monthly rainfall = the **unweighted arithmetic mean** across
the 4 subdivisions, computed per year first (so each year's Maharashtra
value is itself an average of that year's 4 subdivision values), then
averaged/percentiled across years. Area-weighting the 4 subdivisions (by
their true geographic or agricultural area) would be more precise, but
per-subdivision areas are **not** included in this dataset or any
accompanying metadata -- rather than guess or hardcode areas from an outside
memory, this uses the plain unweighted mean and flags it here as an
ASSUMPTION. (Maharashtra's 4 IMD subdivisions are, in fact, roughly
comparable in area, so this is not expected to be a large source of error,
but it has not been checked against an authoritative area source.)

## 3. Monthly normals and dry-year values

- **Most recent 30 available years** in the dataset = 1986-2015 (dataset's
  last year is 2015; `agriopt.data.rainfall.N_RECENT_YEARS = 30`).
- **Monthly normal** = mean, across those 30 years, of the (already
  per-year, subdivision-averaged) Maharashtra monthly rainfall.
- **Dry-year value** (drought scenario) = the **20th percentile**, across
  those same 30 years, of the same per-year Maharashtra monthly series
  (`monthly_dry_year()`).

See `agriopt.data.rainfall.monthly_normals()` / `monthly_dry_year()`.

## 4. Effective rainfall (USDA-SCS method, as used in FAO CROPWAT)

Effective rainfall `Peff` (mm) is computed per month from monthly rainfall
`P` (mm) via the USDA Soil Conservation Service formula, as documented and
used in **FAO CROPWAT** (FAO Irrigation and Drainage Paper 56, and FAO
Irrigation and Drainage Paper 25 "Effective Rainfall in Irrigated
Agriculture"):

```
Peff = P * (125 - 0.2*P) / 125     for P <= 250 mm
Peff = 125 + 0.1*P                  for P > 250 mm
```

Implemented in `agriopt.data.rainfall.effective_rainfall_mm()` (vectorized,
works on scalars or arrays). This formula is a widely-used empirical
approximation of the fraction of gross rainfall that is actually retained in
the root zone (versus lost to runoff/deep percolation) -- it saturates
(sub-linear then linear-with-small-slope) at high monthly rainfall, since a
single very wet month cannot usefully "store" all of its rain for crop use.

## 5. Season windows (ASSUMPTION)

Net irrigation is computed by summing effective rainfall over each crop's
growing-season months, not the whole year. Season windows (see
`agriopt.data.rainfall.SEASON_WINDOW_MONTHS` / `CROP_SEASON_WINDOW`):

| window | months |
|---|---|
| kharif | Jun, Jul, Aug, Sep, Oct |
| rabi | Nov, Dec, Jan, Feb, Mar |
| whole_year (sugarcane) | all 12 months |
| long_kharif (cotton, tur) | Jun, Jul, Aug, Sep, Oct, Nov, Dec, Jan |

Crop -> window mapping:

| crop | window | rationale |
|---|---|---|
| rice | kharif | MAIN_SEASON=Kharif |
| wheat | rabi | MAIN_SEASON=Rabi |
| jowar | rabi | MAIN_SEASON=Rabi |
| soybean | kharif | MAIN_SEASON=Kharif |
| cotton | long_kharif | long-duration Kharif-sown, stays in ground into Rabi |
| sugarcane | whole_year | MAIN_SEASON=Whole Year |
| tur | long_kharif | long-duration Kharif-sown, stays in ground into Rabi |
| maize | kharif | MAIN_SEASON=Kharif |

This is the **same special-casing** `agriopt.optim.params.BOTH_SEASON_CROPS`
already applies to sugarcane/cotton/tur for LAND-occupancy purposes (they
occupy both the kharif and rabi land constraints) -- applied here in
parallel, for WATER-season purposes, via a separate `CROP_SEASON_WINDOW`
dict (kept separate from `BOTH_SEASON_CROPS` since the rainfall season
window (Jun-Jan) and the land-occupancy seasons (kharif+rabi buckets) are
conceptually different things that happen to need the same 3 crops flagged).

## 6. Net irrigation requirement

```
net_irrigation_mm(crop, scenario) = max(0, water_need_mm - Peff_season_mm)
```

where `water_need_mm` is the existing FAO TM3 midpoint
(`agriopt.data.reference.water_mm()`, unchanged) and `Peff_season_mm` is the
sum of that crop's season-window months' effective rainfall (`scenario` =
`"normal"` uses the 30-year monthly normals, `"dry"` uses the 20th-percentile
year). See `agriopt.data.rainfall.net_irrigation_mm()`.

### Results table (`agriopt.data.rainfall.rainfall_water_table()`)

| crop | water need (mm) | Peff normal (mm) | net irrigation normal (mm) | net irrigation dry (mm) |
|---|---|---|---|---|
| rice | 575.0 | 695.6 | 0.0 | 0.0 |
| wheat | 550.0 | 34.2 | 515.8 | 546.6 |
| jowar | 550.0 | 34.2 | 515.8 | 546.6 |
| soybean | 575.0 | 695.6 | 0.0 | 0.0 |
| cotton | 1000.0 | 720.2 | 279.8 | 382.7 |
| sugarcane | 2000.0 | 753.1 | 1246.9 | 1374.8 |
| tur | 400.0 | 720.2 | 0.0 | 0.0 |
| maize | 650.0 | 695.6 | 0.0 | 35.3 |

(Regenerate with `python -c "from agriopt.data.rainfall import rainfall_water_table; from agriopt.config import CROPS; print(rainfall_water_table(CROPS).round(1))"`.)

**What the numbers actually show** (checked, not assumed):

- Kharif and long-Kharif rainfed crops (rice, soybean, maize, tur, and even
  cotton to a large extent) end up with **near-zero or heavily-reduced net
  irrigation** under normal rainfall -- their season windows overlap the
  monsoon (Jun-Oct) almost entirely, so effective rainfall alone covers
  most or all of their FAO TM3 total water need. This confirms the intuition
  the Phase 8 brief asked to verify, not just assert.
- **Sugarcane's net irrigation requirement is large in absolute terms**
  (1246.9mm normal, 1374.8mm dry) because it is the only `whole_year` crop:
  its season spans all 12 months, so its effective-rainfall credit
  (753.1mm) is capped by however much of the year's rain falls during the
  ~5 wet months, while its water NEED (2000mm) is the largest of any crop.
  In **relative** terms, sugarcane's irrigation-covered SHARE of total need
  goes from 100% (under `total_need`, the old basis) to 62% under
  `net_irrigation` (1246.9/2000) -- a smaller drop in relative share than
  wheat/jowar (which go from 100% need-as-irrigation to 94% -- 515.8/550 --
  still needing almost everything from irrigation, since Nov-Mar barely
  overlaps the monsoon at all). So sugarcane's water burden does not "grow"
  in the sense of needing MORE water than before (net irrigation is always
  <= total need, by construction) -- but its irrigation burden as measured
  in `water_m3_ha` still increases relative to the fully-rainfed kharif
  crops, widening the existing profit/water tradeoff gap between them (see
  `reports/results/water_basis_comparison.md`).
- Rabi crops (wheat, jowar) see almost NO reduction (Peff normal is only
  34.2mm over Nov-Mar) -- confirming the Rabi dry season in Maharashtra
  provides essentially no rainfall relief, so `net_irrigation` ~= `total_need`
  for these two crops specifically.

## 7. `Scenario.water_basis` (backward compatibility)

`agriopt.optim.problem.Scenario` gained two new fields:

- `water_basis: str = "total_need"` -- `"total_need"` (default, unchanged
  FAO TM3 midpoint) or `"net_irrigation"`.
- `rainfall_scenario: str = "normal"` -- `"normal"` or `"dry"`, used only
  when `water_basis="net_irrigation"`.

`agriopt.optim.params.build_crop_params()` gained matching `water_basis`/
`rainfall_scenario` parameters (both default to the unchanged values), and
`agriopt.optim.solvers.solve_nsga2`/`solve_nsga3` (when building their own
`params_df` internally) pass `scenario.water_basis`/`scenario.rainfall_scenario`
through automatically. `agriopt.backtest.info.build_forecast_params_df`/
`build_realized_params_df` gained the same parameters for the backtest
pipeline. **Every existing caller that doesn't pass these arguments gets
byte-for-byte identical `water_m3_ha` values to every prior phase** -- see
`tests/test_water_net.py::test_default_water_basis_reproduces_total_need`.

See `reports/results/water_basis_comparison.md` for the full before/after
comparison (strategies, backtest) once the optimizer and backtest are rerun
under `water_basis="net_irrigation"`.
