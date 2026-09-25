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

## 2. Maharashtra monthly rainfall (Phase 8.1: AREA-WEIGHTED mean)

**Superseded by Phase 8.1** (see section 8 below) -- Maharashtra's monthly
rainfall is now the **area-weighted mean** across the 4 subdivisions (weight
= each subdivision's official area / their total area, `agriopt.data.rainfall.area_weights()`),
computed per year first (so each year's Maharashtra value is itself a
weighted average of that year's 4 subdivision values), then
averaged/percentiled across years. Phase 8 originally used a plain
unweighted mean here, flagged as an ASSUMPTION because per-subdivision areas
were not readily available; Phase 8.1 found a citable official source for
those areas (IITM, see section 8.1) and switched to area-weighting. **This
changes the computed Maharashtra state-wide rainfall figures from Phase 8's
committed numbers** -- see section 8.4 for the exact before/after delta.
Maharashtra's 4 IMD subdivisions are, in fact, quite different in area
(Madhya Maharashtra at 115,306 sq km is nearly 3.4x Konkan & Goa's 34,095 sq
km), so this was NOT a negligible correction -- see section 8.4.

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

### Results table (`agriopt.data.rainfall.rainfall_water_table()`) -- ORIGINAL Phase 8 numbers (unweighted mean, no rice puddling adjustment)

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

**Superseded by Phase 8.1** -- see section 8.4 for the current (area-weighted
+ rice puddling adjustment) numbers, region="maharashtra". The findings below
describe the ORIGINAL Phase 8 (unweighted) numbers; section 8.4 covers what
changed and why the qualitative conclusions still hold.

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

## 8. Phase 8.1: area-weighted rainfall, rice puddling caveat, per-region water basis

Phase 8.1 addressed three gaps Phase 8 had explicitly flagged as
ASSUMPTIONs/LIMITATIONs: the unweighted Maharashtra mean, the missing rice
puddling-water caveat, and the state-wide-only rainfall (no way to ask for a
single subdivision's own numbers).

### 8.1 Area-weighting the Maharashtra average (found + cited)

**Outcome: a citable, authoritative area figure WAS found** (this was
explicitly allowed to be a "keep the unweighted mean, documented as a
limitation" outcome if not found -- it was found).

**Source**: IITM (Indian Institute of Tropical Meteorology, Pune -- an
autonomous institute under India's Ministry of Earth Sciences; PRIMARY data
source stated as IMD), "IITM Indian regional/subdivisional Monthly Rainfall
data set" (IITM-IMR), metadata file `iitm-subdivrf.txt`:
`https://www.tropmet.res.in/data/data-archival/rain/iitm-subdivrf.txt`
(landing page `https://www.tropmet.res.in/static_pages.php?page_id=53`,
format documented in `https://www.tropmet.res.in/data/data-archival/rain/Readme.pdf`,
which states each subdivision header record contains "Numerical Code of the
subdivision; Name of the subdivision; Area of the subdivision in sq.km.;
Percentage of the area out of the total area of the country; ...").

Verbatim header lines fetched from that file:

```
146 23.KONKAN AND GOA         SUBDIVISION  Area   34095 SQ.KM 1.18 PER   5 STN
146 24.MADHYA MAHARASHTRA     SUBDIVISION  Area  115306 SQ.KM 4.00 PER   9 STN
146 25.MARATHWADA             SUBDIVISION  Area   64525 SQ.KM 2.24 PER   5 STN
146 26.VIDARBHA               SUBDIVISION  Area   97536 SQ.KM 3.39 PER   8 STN
```

("MARATHWADA" is this source's own spelling; it is the same subdivision as
the Kaggle rainfall dataset's "MATATHWADA" -- see the module docstring on
that spelling.) Sum = 311,462 sq km. Cross-check: Maharashtra's actual state
area is ~307,713 sq km (well-known figure) -- the IITM sum is close to but
slightly above this, consistent with "Konkan & Goa" genuinely including
Goa's own ~3,702 sq km (i.e. these are real subdivision-boundary areas, not
an unrelated/incompatible figure that happens to be in the right order of
magnitude).

**What was explicitly rejected as NOT sufficiently citable**: Maharashtra's
6 "revenue divisions" (Konkan, Pune, Nashik, Aurangabad, Amravati, Nagpur --
an administrative, not meteorological, partition) turned up area figures
more easily in general web search, but their boundaries do not cleanly map
1:1 onto the 4 IMD meteorological subdivisions (e.g. "Vidarbha" = Amravati +
Nagpur divisions combined; "Konkan" division excludes Goa, whereas IMD's
"Konkan & Goa" subdivision includes it) -- using revenue-division areas as a
stand-in for IMD subdivision areas would have been exactly the kind of
unverified proxy the task brief warned against, so they were not used.

Area weights (`agriopt.data.rainfall.area_weights()`), area / total:

| subdivision | area (sq km) | weight |
|---|---|---|
| Konkan & Goa | 34,095 | 0.1095 |
| Madhya Maharashtra | 115,306 | 0.3702 |
| Marathwada | 64,525 | 0.2072 |
| Vidarbha | 97,536 | 0.3131 |

`_regional_yearly()` (`agriopt.data.rainfall`) now computes the
"maharashtra" region's per-year monthly rainfall as this weighted
combination, replacing Phase 8's `groupby("YEAR")[MONTH_COLS].mean()`
(equal 25%-each weighting).

### 8.2 Rice puddling water (found + cited, partial)

FAO's Irrigation Water Management Training Manual No. 3, Chapter 4
"Determination of the Irrigation Schedule for Paddy Rice"
(`https://www.fao.org/4/t7202e/t7202e07.htm`) gives the standing-water
irrigation balance for puddled/transplanted rice as:

```
IN = ET_crop + SAT + PERC + WL - Peff
```

- **SAT** ("the amount of water needed to saturate the root zone") **= 200
  mm** -- a one-time, pre-season land-preparation/puddling requirement,
  relatively soil-independent. **Used as `RICE_EXTRA_MM = 200.0`** in
  `agriopt.data.rainfall.net_irrigation_mm()`, added ONLY for `crop="rice"`,
  ONLY inside `net_irrigation_mm()` (i.e. only the `water_basis="net_irrigation"`
  path) -- `water_mm()`/the `"total_need"` basis is completely unchanged, so
  no Phase 1-8 `total_need`-basis output is affected.
- **PERC** (percolation/seepage) **= 2-8 mm/day depending on soil type**
  (60-240 mm/month) -- explicitly NOT reduced to a single point figure and
  NOT added here: it is highly soil-type dependent, and this repo has no
  per-field/per-region soil-type data to justify picking one value over
  another (documented LIMITATION, not a blocker, per the task brief's
  explicit allowance for this exact situation).
- **WL** (standing water layer, 20-100mm) -- also not added, for the same
  reason (it is closer to an ongoing operational choice than a fixed
  physical requirement, and interacts with PERC in ways this repo cannot
  quantify without soil data).

So `RICE_EXTRA_MM` captures the land-preparation component only, not the
full puddled-rice water burden -- a partial, explicitly-scoped fix, not a
claim that rice's net irrigation figure is now "complete."

### 8.3 `region` parameter (Scenario.region / REGIONS)

`agriopt.data.rainfall.REGIONS = ("maharashtra", "konkan",
"madhya_maharashtra", "marathwada", "vidarbha")`. `monthly_normals()`,
`monthly_dry_year()`, `effective_rainfall_monthly()`,
`season_effective_rainfall_mm()`, `net_irrigation_mm()`, and
`rainfall_water_table()` all gained a `region` parameter (default
`"maharashtra"`, unchanged behavior for every existing caller that doesn't
pass it). `"maharashtra"` uses the area-weighted combination (8.1); any
other region key uses that single IMD subdivision's own rainfall directly
(no weighting -- REGION_TO_SUBDIVISION maps the key to the dataset's own
SUBDIVISION string).

`agriopt.optim.problem.Scenario` gained `region: str = "maharashtra"`.
`agriopt.optim.params.build_crop_params()` gained a matching `region`
parameter, used only when `water_basis="net_irrigation"`.
`agriopt.optim.solvers.solve_nsga2/solve_lp_profit_max/solve_lp_eps/exact_front_lp`
now also pass `scenario.region` through when building their own
`params_df`. `agriopt.backtest.info.build_forecast_params_df`/
`build_realized_params_df` gained the same `region` parameter, for
consistency with the existing `water_basis`/`rainfall_scenario` threading
pattern (this phase does NOT rerun the backtest per-region -- see
`reports/results/region_comparison.md`, which reruns only the E3 strategies
table for `marathwada`/`konkan`).

### 8.4 Net effect: does the "maharashtra" default change from Phase 8's numbers?

**Yes.** Area-weighting is NOT a small correction here: Madhya Maharashtra
(37.0% weight) and Vidarbha (31.3%) are comparatively dry, while Konkan &
Goa (10.9% weight, but the wettest subdivision by far) previously counted
equally (25%) under the unweighted mean. Net effect: the area-weighted
monsoon-month rainfall is noticeably LOWER than the old unweighted figure
(e.g. June normal: 295.0mm unweighted -> 223.6mm area-weighted; July:
450.2mm -> 343.8mm), because the wettest subdivision (Konkan) is
underweighted relative to its old 25% share.

`rainfall_water_table(CROPS, region="maharashtra")` now (area-weighted +
`RICE_EXTRA_MM`):

| crop | water need (mm) | Peff normal (mm) | net irrigation normal (mm) | net irrigation dry (mm) |
|---|---|---|---|---|
| rice | 575.0 | 650.5 | 200.0 | 212.5 |
| wheat | 550.0 | 35.6 | 514.4 | 546.4 |
| jowar | 550.0 | 35.6 | 514.4 | 546.4 |
| soybean | 575.0 | 650.5 | 0.0 | 12.5 |
| cotton | 1000.0 | 675.6 | 324.4 | 434.8 |
| sugarcane | 2000.0 | 707.5 | 1292.5 | 1427.0 |
| tur | 400.0 | 675.6 | 0.0 | 0.0 |
| maize | 650.0 | 650.5 | 0.0 | 87.5 |

vs Phase 8's original (unweighted, no rice adjustment) table in section 6.
Peff normal dropped for every crop (e.g. rice/soybean/maize kharif window:
695.6 -> 650.5mm; cotton/tur long-kharif: 720.2 -> 675.6mm; rabi
wheat/jowar: 34.2 -> 35.6mm, essentially unchanged since Nov-Mar rainfall
barely differs by subdivision). Net irrigation normal/dry rose slightly for
every crop except rice (whose 0.0 -> 200.0/212.5 jump is dominated by
`RICE_EXTRA_MM`, not the area-weighting itself -- rice's Peff normal only
dropped 695.6 -> 650.5, still above its 575mm need, so the area-weighting
alone would have kept rice's net irrigation at 0.0; the puddling adjustment
is what moves it off zero).

**Qualitative conclusions from Phase 8's findings (section 6) still hold**:
kharif/long-kharif rainfed crops remain far cheaper in net-irrigation terms
than Rabi crops or sugarcane; Rabi crops still see almost no rainfall
relief; sugarcane's absolute net-irrigation burden is still the largest of
any crop. The area-weighting shifted magnitudes, not the qualitative
pattern.

No `tests/test_water_net.py` assertion hardcodes an exact rainfall-derived
mm figure (all are inequality/structural checks), so this change did not
require adjusting that file's expected values -- see `tests/test_water_region.py`
for the new region-specific tests (including a regression check that
`build_crop_params()`'s DEFAULT `region="maharashtra"` reproduces this
section's numbers).

### 8.5 Regional net-irrigation table (all 4 regions x 2 scenarios)

See `reports/results/region_comparison.md` for the full 8-crop x 4-region x
2-scenario table and the E3 strategies rerun for `marathwada`/`konkan`.
