# Research paper guide (IEEE / Springer style)

Written for: students writing a conference/journal-style paper from this project. Numbers are from
`KEY_NUMBERS.md` (row codes in brackets). Fill in `[TEAM NAMES]`, `[INSTITUTION NAME]`, `[VENUE TEMPLATE]`.

## How to frame it (important)

This is **a water-saving decision-support tool with an honest, leak-free backtest** - not a profit-maximising
breakthrough. Reviewers trust papers that state limits clearly. The strongest, safe sentence is:

> On a four-year leak-free backtest, the recommended plan matched the profit of the current regional crop mix
> (+0.6%) while using 38.9% less water.

Do **not** write: "outperforms", "maximises profit", "accurately predicts yield", "significantly better".
Words that are safe: "comparable profit", "substantially lower water use", "in a four-year backtest",
"directional evidence".

## Three honest contributions

1. **A water-aware, risk-aware multi-objective formulation, solved and verified exactly.** Crop allocation for
   eight Maharashtra crops with profit, water and fertilizer objectives and season-aware land, food-security and
   per-crop-share constraints. Because the three objectives are linear, the evolutionary (NSGA-II) front is
   checked against exact linear programming, and the recommended plan is polished onto the exact front (raw
   NSGA-II was 0.1-2.0% below it) [D4]. A risk-aware four-objective mode (NSGA-III) minimises risk **per rupee
   of profit**, because an absolute-rupee risk objective rewards leaving land idle.
2. **An evaluation protocol that is hard to cheat.** A leak-free historical backtest (each year planned only
   from information available on 1 May), a fair, constraint-satisfying version of the current mix as the baseline,
   an equal-water-budget regional comparison, and oracles that know the true yields, true prices or both - which
   split the loss from imperfect forecasts into a yield part (about 64-68%) and a price part (about 35-37%) [C4].
3. **Honest empirical findings, including negative ones, and an open reproducible tool.** Same profit and
   about 36-39% less water [A1-A4]; a Random Forest yield model that beats a three-year average on only 3 of 8
   crops [C3]; a naive price forecast that is statistically indistinguishable from XGBoost under a
   month-clustered Diebold-Mariano test [C2]; all code, data tables and results in a public repository with a
   check that published tables stay in step with the code.

## Suggested title

*Water-aware multi-objective crop allocation for Maharashtra: formulation, exact verification and a leak-free
backtest.*

## Abstract (about 180 words - draft)

> We present AgriOpt, a decision-support tool that allocates farmland among eight major Maharashtra crops under
> profit, water and fertilizer objectives, with land, food-security and diversification constraints. Per-hectare
> economics combine a Random Forest yield model, a price forecaster and government cost, support-price and
> crop-water data; irrigation need is computed as a monthly water balance from IMD rainfall. Because the
> objectives are linear, we verify NSGA-II against exact linear programming and polish its recommendation onto
> the exact front; a four-objective NSGA-III mode adds a risk-per-rupee objective. In a leak-free backtest over
> 2016-2019 on a 10 ha model farm, the recommended plan earned Rs 230,769 per year versus Rs 229,479 for the
> current regional crop mix (+0.6%) while using 38.9% less water. Oracle experiments show yield forecast error
> accounts for most of the profit lost to imperfect foresight. The yield model beats a three-year average on only
> three of eight crops, and a naive price forecast is statistically indistinguishable from XGBoost. We discuss
> limitations - four scored years, all-India cost data - and release code and results.

## 1. Introduction

Write 4 paragraphs: (1) water stress and crop choice in Maharashtra; (2) why profit-only tools fail
(recommend one or two thirsty crops); (3) what we do (list the three contributions above); (4) paper roadmap.
**Read:** `README.md` first page. **Figure:** `fig02_how_it_works.png` (optional).

## 2. Related work

Four short paragraphs (2-3 citations each; all in `LITERATURE_AND_REFERENCES.md`):
multi-objective crop planning (Sarker & Ray 2009); evolutionary multi-objective algorithms (Deb et al. 2002;
Deb & Jain 2014; Blank & Deb 2020; hypervolume, Zitzler & Thiele 1999); crop yield prediction with machine
learning (van Klompenburg et al. 2020; Jeong et al. 2016); forecast evaluation and uncertainty (Diebold & Mariano
1995; Harvey et al. 1997; Lei et al. 2018). Finish with how this work differs: openly released, end to end from
data to app, and evaluated with a leak-free backtest and exact verification. (Do not claim novelty of NSGA-II
or of the Random Forest.)

## 3. Methodology

**3.1 Data.** 19,689 yield rows (30 states, 55 crops, 1997-2020); monthly mandi prices for 7 crops (2001-2025);
IMD rainfall (last 30 years of 1901-2015); cost, MSP, FRP, water need, fertilizer tables [B1-B5].
**3.2 Yield model.** Random Forest; crop, season, state, year and rainfall as inputs; trained to 2015, selected on
2013-2015 validation; split-conformal 90% intervals [C5].
**3.3 Price model.** Naive, Seasonal-Naive and XGBoost, 3-12 month horizons; MSP floor option; sugarcane at FRP.
**3.4 Per-hectare economics.** profit = yield x farm-gate price - cost per quintal x yield; sugarcane annualised
(15-month cycle) and priced at FRP minus Rs 75/qtl; one function used everywhere.
**3.5 Water.** Net irrigation = sum over season months of max(0, monthly need - effective rain); FAO seasonal
need spread evenly (assumption); "dry" = real observed year near the 20th percentile of usable rain.
**3.6 Optimisation problem.** Variables x_i (ha). Minimise -profit, water, fertilizer. Constraints: kharif and
rabi land (cotton, tur, sugarcane occupy both), water budget, food crops >= 30% of cropped season-hectares,
x_i <= 50% of land. NSGA-II, population 100, 200 generations; recommended point by pseudo-weights (0.5, 0.3, 0.2)
then LP-polish. Exact LP reference fronts for verification.
**3.7 Risk.** Revenue covariance Sigma from detrended yearly revenue; risk = sqrt(x' Sigma x); NSGA-III objective
= risk / profit.
**3.8 Baselines.** B1 current mix (historical crop areas, built per season, 10 ha); B1_SCALED (closest feasible
version); B2 profit-max LP; B3 same profit with least water.
**3.9 Backtest.** Plan on 1 May of year t using data to t-1; score against realized yield and price; years
2016-2019 (n = 4); oracles ORACLE, ORACLE_PRICE, ORACLE_YIELD.
**Read:** `docs/formulation.md` (see the banner), `docs/water.md` section 9, `docs/backtest.md`,
`reports/results/CHANGELOG_fixes.md` (why each design choice was made).

## 4. Experiments

List: (E1) strategy comparison at three water levels and two price modes; (E2) NSGA-II vs exact LP front quality
(hypervolume, IGD) and seed robustness (10 seeds); (E3) backtest 2016-2019 with per-year differences; (E4) oracle
decomposition of forecast loss, with and without sugarcane, and with the earlier look-ahead variant; (E5) information
ablation (what if yield, price or cost data were worse); (E6) regional comparison at equal water budgets, normal
and dry years; (E7) forecast-model evaluation on the 8 decision crops and Diebold-Mariano tests; (E8) risk-aware mode.
**Read:** `reports/results/RESULTS_INDEX.md` (one row per experiment, with source files).

## 5. Results

### Main results table (copy; every row has its source)

| Result | Number | Source file |
|---|---|---|
| Realized profit per year, 2016-2019, default water (10 ha) | AgriOpt **230,769** vs current mix **229,479** (+0.6%) | `reports/results/backtest_summary_v2.md` |
| Water per year, same backtest | AgriOpt **64,291 m³** vs **105,161 m³** (-38.9%) | `reports/results/backtest_rows.csv` |
| Profit per 1,000 m³ | **₹3,714** vs **₹2,181** | `reports/results/backtest_summary_v2.md` |
| Profit-max plan (B2) | 288,084 per year; perfect foresight 339,253 | `reports/results/backtest_skill.md` |
| Tight water (0.7x) | AgriOpt 200,645; closest feasible current mix 154,455 | `reports/results/backtest_summary_v2.md` |
| Forecast loss split | yield foresight closes 64-68% of the gap to perfect foresight; price foresight 35-37% | `reports/results/backtest_skill.md` |
| Planning-time comparison (not a forecast of gain) | AgriOpt -35.7% water; profit +51.6% on forecast prices | `reports/results/optim_strategies.md` |
| Same profit, least water (B3) | -58.5% water | `reports/results/optim_strategies.md` |
| NSGA-II vs exact LP | 1.07x the simple reference, 0.947x the grid reference; recommended plan exactly on the LP front | `reports/results/optim_front_quality.md`, `optim_front_quality_v2.md` |
| Yield model vs 3-year average | wins on 3 of 8 crops | `reports/results/yield_decision_crops.md` |
| Price models (MAE Rs/qtl at 3/6/12 months) | Naive 373.6 / 512.6 / 750.9; XGBoost 454.4 / 743.2 / 1,194.3 | `reports/results/price_results.md` |
| Naive vs XGBoost significance | p = 0.076 / 0.081 / 0.071 (not significant) | `reports/results/price_significance.md` |
| Regions at equal water (normal rain) | Konkan 273,010 ... Marathwada 224,101 | `reports/results/region_equal_budget.csv` |
| Risk-aware vs standard plan | risk per rupee -8.6%; rupee risk +7.0%; profit +17.0%; water +21.2% | `reports/results/optim_findings_v2.md` |

Report the per-year differences instead of p-values for the backtest (with four paired years no test can reach
p < 0.125): `reports/results/backtest_summary_v2.md` section 5.

### Figures to use (5)

1. `fig03_headline_water_profit.png` - the headline result.
2. `fig04_pareto_front.png` - trade-off surface with baselines; recommended plan on the exact LP line.
3. `fig06_backtest_profit_by_year.png` - realized profit by year for every strategy including oracles.
4. `fig07_yield_vs_baseline.png` - the honest yield-model result.
5. `fig08_regions_equal_budget.png` - regional comparison at equal water.
Optional: `fig01_architecture.png` (system), `fig10_risk_correlation.png` (risk).

## 6. Discussion

(1) Why profit is not higher: forecast optimism (+51.6% planned vs +0.6% realized) and the water/fertilizer
objectives [A6]. (2) Yield error matters more than price error [C4]. (3) Simple baselines are strong: a 3-year
average for yield, "last price" for prices [C2, C3]. (4) Equal-budget regional comparison reverses a naive
per-region-budget result [E2]. (5) Risk-aware mode is experimental: concentration on sugarcane, less stable
across seeds [D6, D8].

## 7. Threats to validity (put in Discussion or its own section)

Four scored years; all-India costs; state-level not farm-level; unit assumptions for rice and cotton; fertilizer
data from 2003/04; one planning date; no field trial. Full text in `REPORT_GUIDE.md`, Chapter 9.

## 8. Conclusion and future work

Three sentences: what was built; the honest headline; the next step (state-wise costs, better yield model,
two-stage planning, field validation).

## Reproducibility statement (journals like this)

"Code, curated reference tables, cached model outputs and all result files are in the project repository. Scripts
numbered 10-95 regenerate every result; a test re-solves the optimizer tables from the stored data to ensure the
published tables are consistent with the code." (`README.md`, "Reproduce".)

## Checklist before submitting

- [ ] Every number appears in `KEY_NUMBERS.md`.
- [ ] No "significantly" unless a test in `reports/results/` says so (e.g. Naive vs Seasonal-Naive at 3 and 6 months).
- [ ] Limitations paragraph present.
- [ ] All references come from `references.bib`; check the venue's template.
- [ ] `[TEAM NAMES]`, `[INSTITUTION NAME]` filled in.
