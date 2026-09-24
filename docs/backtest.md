# Phase 7: decision backtest 2016-2020 -- methodology and ASSUMPTIONS

Question: "would AgriOpt have helped?" For each decision year `t` in
2016..2020, build every strategy's plan using ONLY information available
before sowing (June `t`), then score that plan against year `t`'s REALIZED
yield/price. ORACLE plans directly against the realized params -- a
perfect-foresight upper bound.

Code: `src/agriopt/backtest/info.py` (information sets),
`scripts/60_backtest.py` (orchestration/reporting), `tests/test_backtest.py`
(no-leakage + ORACLE-bound assertions).

## 1. `data/reference/msp_history.csv`

Columns: `crop, year, msp_rs_per_qtl, cost_a2fl_rs_per_qtl, source_url`.
`year` is the crop-year (matches `agriopt.optim.risk`'s Crop_Year convention:
kharif crop-year `t` -> harvested Oct-Dec `t`; rabi crop-year `t` ->
harvested Mar-May `t+1`). Built by fetching official PIB/desagri.gov.in
kharif/rabi MSP notifications and cross-year MSP-statement PDFs (2015-2025),
plus sugarcane FRP announcements (tagged to the sugar-season's STARTING
year, e.g. FRP for the "2016-17" sugar season -> `year=2016`) -- **every
populated cell has a `source_url`, verified by `tests/test_backtest.py`**.
No value was filled from memory; every number was fetched/read off an
official notification, a PIB-sourced comparison table in a news report, or
(rows with a plain-text source instead of a URL, all in the `year=2025` row)
directly carried over from `crop_reference.csv`'s own already-cited 2025-26
figure.

**Known gaps** (left blank, not guessed):
- `year=2015` is blank for all 7 MSP crops (rice/wheat/jowar/soybean/cotton/
  tur/maize) -- I could not find a citable per-crop KMS-2015-16/RMS-2015-16
  MSP table in the time available; only sugarcane's FRP (230, same as
  2016-17) was independently confirmed for 2015. This doesn't affect the
  2016-2020 backtest itself (year 2015 is never a decision year), but is
  flagged since the brief asked for 2015-2025 coverage.
- `cost_a2fl_rs_per_qtl` is blank for every row -- CACP's per-crop, per-year
  A2+FL cost-of-cultivation figures are not published in an easily
  fetchable consolidated table; this was expected going in (the brief calls
  it "sparse/hard to find, that's expected and fine").
- `jowar`/`soybean`/`maize` 2017's MSP came from a secondary source (a
  business-standard article's comparison table, since the primary
  agricoop.gov.in page returned a DNS failure and the desagri.gov.in mirror
  for that specific season wasn't found) rather than a directly-fetched
  primary PDF -- still cited, just flagged as secondary.

## 2. Cost-of-cultivation for year `t` (`agriopt.backtest.info.cost_for_year`)

1. If `msp_history.csv` has a published `cost_a2fl_rs_per_qtl` for
   `(crop, t)`, use it directly. (In practice: never triggers in this run,
   see gap above.)
2. **ASSUMPTION**: else `cost_t = cost_2025 * (MSP_t / MSP_2025)`, using
   `crop_reference.csv`'s already-cited 2025-26 `cost_rs_per_qtl` as the
   anchor and MSP growth as a cost-growth index (CACP sets MSP as a markup
   over cost, so MSP's year-over-year growth is a reasonable, if imperfect,
   proxy for cost growth when no direct figure exists for year `t`). This is
   the path taken for every crop-year in the 2016-2020 backtest.
   Sugarcane uses the same rule with FRP in place of MSP (crop_reference's
   sugarcane cost=173 is anchored to FRP=355 for 2025-26).

## 3. Information sets (`agriopt.backtest.info`)

For decision year `t` (sowing ~June `t`):

- **Yield forecast**: RandomForest refit on `year <= t-1` only (verified by
  `tests/test_backtest.py::test_yield_model_trained_only_on_year_leq_t_minus_1`).
  **ASSUMPTION**: `models/yield_best.json` does not persist the RF
  hyperparameters it used (only metrics/feature lists), so there is nothing
  saved to "reuse" for the 5 refits this phase needs. Each decision year
  instead retunes RF via the exact protocol Phase 1 used
  (`tune_rf` + a 3-year validation window immediately preceding the fit
  cutoff, `agriopt.models.yield_model.tuning_split`'s own convention, just
  slid to end at `t-1`). For `t=2016` this reproduces Phase 1's original
  window exactly (fit `<2013`, validate `2013-2015`). Saleable-yield
  conversion is the same `YIELD_TO_SALEABLE_QTL_PER_HA` used everywhere
  else. Rainfall input = Maharashtra median rainfall over the 5 years
  strictly before `t` (`year <= t-1`) -- never year `t`'s own rainfall.
  Models are cached under `models/backtest/` (gitignored via the existing
  root `/models/` pattern).
- **Price forecast**: naive = last observed monthly modal price at the
  decision month, ffilled to the same convention `build_wide_price_table`
  already uses. **ASSUMPTION**: kharif crops (incl. cotton/tur, which are
  Kharif-sown even though they occupy both seasons' land) use May of year
  `t`; rabi crops use October of year `t`. Sugarcane has no mandi series --
  its "price forecast" is simply `FRP_t` from `msp_history.csv`, which is
  legitimately known ahead of sowing (the government announces FRP before
  the season, it isn't discovered at harvest).
- **Cost**: `cost_for_year(crop, t)`, see above -- identical whether used
  for planning or for scoring the realized outcome (cost isn't "revealed"
  after harvest the way yield/price are; it's realized as spent).
- **Risk (Model B)**: `agriopt.backtest.info.build_risk_inputs_leakfree(t-1, ...)`
  -- a parametrized reimplementation of `agriopt.optim.risk.build_risk_inputs`
  that restricts every step (yield years, price months, the OLS detrend fit
  itself) to `year <= t-1`, so the covariance matrix Sigma never sees a
  future year (verified by
  `test_risk_sigma_deviation_matrix_only_uses_years_leq_t_minus_1`).
  Sugarcane keeps risk.py's existing "constant FRP -> yield-only variance"
  treatment, just with FRP evaluated at `t-1` rather than 2025-26.
- **Current mix (B1)**: `agriopt.backtest.info.current_mix_leakfree` --
  **NOT** a direct reuse of `agriopt.optim.baselines.current_mix`, because
  that function reads `yield_clean.parquet` with no year cutoff at all and
  takes the most recent 5 years in the WHOLE file; for early decision years
  (e.g. `t=2016`) that would silently leak 2016-2019 area shares into a
  "historical" baseline for 2016. `current_mix_leakfree` is the same
  area-share algorithm, restricted to `year <= t-1` first.

Realized outcomes for year `t`:
- **yield**: actual Maharashtra `yield_clean` row for `(crop, MAIN_SEASON[crop], t)`,
  saleable-converted.
- **price**: mean modal price over the harvest window for year `t` (same
  `HARVEST_WINDOW_MONTHS` convention as `agriopt.optim.risk`) -- the real
  realized market price, not a forecast. Sugarcane: `FRP_t` (same figure as
  planned -- there's no separate "realized" FRP, it's an administered price).
- **cost**: same `cost_for_year(crop, t)` as planning.

**Data gap, found not assumed**: Maharashtra's `yield_clean.parquet` has
**zero rows for year 2020, for every crop** (its Maharashtra coverage tops
out at 2019 -- confirmed by direct inspection, not a code bug). So `t=2020`
has NO realized outcome for ANY crop or strategy. Planning still runs for
2020 (it only needs data through 2019), but every realized-profit /
forecast-error / capture-ratio / win-count / significance-test figure in
`reports/results/backtest_summary.md` is computed over **2016-2019 (n=4)**,
not the full 5 decision years -- called out explicitly in that report and in
`backtest_findings.md`, never silently averaged over whatever happens to be
non-NaN.

## 4. Strategies and scenarios (`scripts/60_backtest.py`)

Two water scenarios per year: `default` (water budget = B1's own realized...
i.e. its OWN forecast-time water footprint that year, x1.0) and `tight`
(x0.7) -- matching the `WATER_MULTIPLIERS` convention already used in
`scripts/31_run_risk.py`/`scripts/50_ablation.py`. B1's water footprint is
computed once per year (leak-free B1 under a land-only dummy scenario) and
used as the shared water budget for every strategy that year/scenario, so
all strategies face an identical constraint.

- **B1**: `current_mix_leakfree` (years `t-5..t-1` area shares).
- **B2**: `solve_lp_profit_max` on the leak-free forecast params.
- **B3**: `solve_lp_eps`, `min_profit` = B1's forecast profit.
- **OURS**: `nsga2_recommended`, weights `(0.5, 0.3, 0.2)` (matches
  `baselines.nsga2_recommended`'s own default), seed=0.
- **MODEL_B**: `nsga3_recommended`, weights `(0.4, 0.2, 0.1, 0.3)` (matches
  `scripts/31_run_risk.py`'s `MODEL_B_WEIGHTS`), seed=0, using the leak-free
  Sigma.
- **ORACLE**: `solve_lp_profit_max` on the REALIZED params for year `t` --
  the perfect-foresight upper bound. Every other strategy's `x` is planned
  under forecast params, then scored TWICE (planned profit under forecast
  params, realized profit under realized params) -- water/fert are
  physical properties of the allocation itself (crop_reference-driven, not
  yield/price-driven), so they're identical in both scorings and reported
  once.

**ASSUMPTION** (missing-crop handling in realized scoring): if a crop has no
realized data for year `t` but a strategy allocated it >0 ha, that crop's
contribution to REALIZED profit is treated as 0 (excluded, not imputed) and
flagged via the `missing_realized_crops` column in `backtest_rows.csv` --
never silently guessed. In practice this only ever triggers as "every crop
missing" (2020), since 2016-2019 have complete realized data for all 8
crops.

## 5. Statistics

Paired sign test + Wilcoxon signed-rank on (OURS - B1) and (MODEL_B - B1)
realized-profit differences, per scenario, over the years with a realized
outcome for both (**n=4** here, not 5, per the 2020 data gap above).
**Stated plainly in every report this phase writes: n=4 gives essentially no
statistical power. These p-values are exploratory/directional signals only
-- not evidence of a significant effect in either direction.**
