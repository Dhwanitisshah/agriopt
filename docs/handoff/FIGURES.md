# Figures for the report, paper and PPT

All files are in `docs/handoff/figures/`. They are **copies** (the originals stay in `reports/results/`,
`reports/eda/`, `docs/img/`). Figures were checked against the final regeneration commit (`d88195c`, "regenerate
all results ... after Tasks 3-10") - see the status column. Suggested size in a report: 12-15 cm wide.

| File | Caption (copy this) | What it shows | One-line takeaway | Source | Status |
|---|---|---|---|---|---|
| `fig01_architecture.png` | System architecture of AgriOpt: data sources, models, per-hectare economics, optimizer, cached results and the Streamlit app. | The README's architecture diagram rendered as an image. | Heavy modelling is done offline; the app only reads one data file. | README mermaid block (rendered locally) | Current |
| `fig02_how_it_works.png` | How AgriOpt works, from data to web app. | A simple six-box flow: data, models, economics, optimizer, cached results, app. | One-glance overview for slides and the introduction. | `scripts/make_handoff_figures.py` (no data) | Current (new) |
| `fig03_headline_water_profit.png` | Backtest 2016-2019 (10 ha model farm, default water budget): realized profit and water use of the current crop mix and of AgriOpt. | Two bar charts: profit per year (230,769 vs 229,479; +0.6%) and water per year (64,291 vs 105,161 m³; -38.9%). | Same profit, much less water. **The headline slide.** | `reports/results/backtest_rows.csv` via `scripts/make_handoff_figures.py` | Current (new) |
| `fig04_pareto_front.png` | Trade-off between profit and water for the 10 ha model farm (current water budget, market prices); colour = fertilizer. | Dots: NSGA-II plans. Line: exact LP front. Markers: B1 current mix (red square), B2 profit-max (triangle), B3 same-profit-less-water (diamond), AgriOpt (star). | The recommended plan lies on the exact trade-off line; the current mix is far from it. | `reports/results/optim_pareto_front.png` | Current (regenerated in `d88195c`) |
| `fig05_allocation_by_crop.png` | Hectares per crop for each strategy (current water, market prices). | Stacked bars for B1, B2, B3 and AgriOpt. | The current mix spreads over 8 crops; AgriOpt concentrates on about 3 (rice, wheat, some sugarcane). Note: a crop in both seasons counts once, so a bar can exceed 10 ha. | `reports/results/optim_allocation_by_crop.png` | Current (`d88195c`) |
| `fig06_backtest_profit_by_year.png` | Realized profit per year, 2016-2019, default water budget, for every strategy. | Lines for B1, B2, B3, AgriOpt (OURS), risk-aware (MODEL_B) and three oracles. | Results swing a lot from year to year; AgriOpt is close to the current mix on average, below the profit-max plan. | `reports/results/backtest_realized_profit_default.png` | Current (`d88195c`) |
| `fig07_yield_vs_baseline.png` | Yield forecast error for the 8 decision crops, one year ahead (2016-2019): Random Forest vs a last-3-year average. | Paired bars of percentage error per crop; "RF loses" is marked. | The yield model beats the 3-year average on only 3 of 8 crops. | `reports/results/yield_decision_crops_verdicts.csv` via `scripts/make_handoff_figures.py` | Current (new) |
| `fig08_regions_equal_budget.png` | AgriOpt profit by region at the same water budget (54,532 m³, normal rainfall, 10 ha). | Bars for Konkan, Maharashtra, Madhya Maharashtra, Vidarbha, Marathwada (273,010 down to 224,101). | At equal water, Konkan does best and Marathwada worst. | `reports/results/region_equal_budget.csv` via `scripts/make_handoff_figures.py` | Current (new) |
| `fig09_backtest_capture_ratio.png` | Capture ratio (realized profit divided by perfect-foresight profit) per strategy, default and tight water. | Grouped bars; 1.0 = perfect foresight. | The profit-max plan captures most; the partial oracles show yield knowledge is worth more than price knowledge. Labels of the last two bars overlap slightly - widen the picture or crop in your editor. | `reports/results/backtest_capture_ratio.png` | Current (`d88195c`) |
| `fig10_risk_correlation.png` | Correlation of the crops' detrended yearly revenues (Maharashtra, about 18-21 years). | A heat-map matrix; red = move together. | Crops tend to rise and fall together (mean correlation 0.49), so diversifying buys less risk reduction than expected. | `reports/results/risk_correlation_heatmap.png` | Current (regenerated; output identical to Phase-1 run, hence the earlier commit date) |
| `fig11_price_forecast.png` | Actual vs forecast 12-month-ahead market price for rice, wheat and cotton (Naive vs XGBoost). | Three line charts, late 2022 to Oct 2025. | The simple "last price" forecast tracks reality better than XGBoost. | `reports/results/price_actual_vs_forecast_h12.png` | Current - model-level figure; the price model was not retrained and its results do not depend on the economics fixes (file date 2026-09-23) |
| `fig12_app_recommendation.png` | Screenshot: Recommendation tab of the live app (default inputs). | Profit, water, fertilizer, food share, profit risk, hectares per crop. | What a user sees first. | `docs/img/recommendation.png` | Current (captured after the fixes) |
| `fig13_app_tradeoffs.png` | Screenshot: Trade-offs tab (Pareto chart). | Interactive version of `fig04`. | Users can see all alternatives. | `docs/img/tradeoffs.png` | Current |
| `fig14_app_regional.png` | Screenshot: Regional view tab (Konkan vs Marathwada). | Strategy tables for the two regions. | Regional differences are in the app. | `docs/img/regional.png` | Current. Note: this tab shows the per-region-own-budget tables; use `fig08` for the fair equal-budget comparison. |

## How the "current" status was checked

- Figures that depend on the economics (profit, backtest, optimizer, risk) were regenerated by the final
  regeneration commit `d88195c` (check with `git log -1 -- <file>`). `fig10` is also economics-independent in
  content (a correlation of revenue deviations) and the final run reproduced it unchanged.
- Figures about the trained models (`fig11`) come from model runs that were not repeated because the models were
  not retrained; the economics corrections do not change them.
- The new figures (`fig02`, `fig03`, `fig07`, `fig08`) are drawn directly from the committed result files by
  `scripts/make_handoff_figures.py`; re-running it reproduces them.

## Figures in the repository that we did NOT copy (and why)

| File | Why not |
|---|---|
| `reports/results/per_crop_mape.png`, `pred_vs_actual.png` | From the first yield-model run, based on pooled evaluation across crops in different units. Use `fig07` instead. |
| `reports/results/shap_summary_xgb.png` | Explains the XGBoost model, not the deployed Random Forest; optional for the paper (state this if used). |
| `reports/results/yield_loso.png`, `yield_loso_crop_mix.png` | Leave-one-state-out check; pooled units, mixed message. Mention in text only if needed (`yield_loso.md`). |
| `reports/results/backtest_realized_profit_tight.png`, `backtest_planned_vs_realized.png`, `backtest_decomposition_tight_v2.png`, `risk_profit_distribution.png`, `risk_vs_profit_front.png` | Current and correct but more technical; use in appendices. |
| `reports/eda/*.png` | Data-audit plots (current; not affected by the fixes). `yield_over_years_by_crop.png` and `prices_monthly.png` are good for the Data chapter. |

## Stale figures

None of the copied figures is stale. If you find an old image in an older slide deck, replace it with the file here.
