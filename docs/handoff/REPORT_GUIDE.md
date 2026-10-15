# B.Tech project report: chapter-by-chapter guide

Written for: students who did not write the code. Every number is from `KEY_NUMBERS.md` (look up the row
code in brackets, e.g. [A2]). Fill in `[TEAM NAMES]`, `[GUIDE NAME]`, `[INSTITUTION NAME]`, `[COLLEGE FORMAT]`
(the college's own chapter order and page limits override this outline - keep the content, change the order).
The paragraphs below are drafts to adapt in your own words; keep the facts.

Figure paths are inside `docs/handoff/figures/` (captions in `FIGURES.md`).

---

## Front matter

Title page, certificate, declaration, acknowledgements, list of figures/tables: `[COLLEGE FORMAT]`.
Suggested title: *AgriOpt: A multi-objective, water-aware crop allocation decision-support tool for Maharashtra.*

## Abstract (about 200 words - ready draft)

> Farmers in Maharashtra usually choose crops by habit and last year's prices, with no simple way to weigh profit
> against water use, fertilizer use, food security and risk. We built AgriOpt, a decision-support tool that
> recommends how to split a farm between eight major crops. It combines a Random Forest yield model, a price
> forecasting model, and government data on cost of cultivation, support prices, crop water need and rainfall to
> compute per-hectare economics, then uses multi-objective evolutionary optimisation (NSGA-II, with NSGA-III for
> a risk-aware mode), cross-checked against exact linear programming. We tested the tool with a leak-free
> backtest over 2016-2019, planning each year only from information available beforehand. On a 10 ha model
> farm, AgriOpt earned about the same profit as the current regional crop mix (Rs 230,769 against Rs 229,479 per
> year) while using about 39% less water. It does not outperform the current mix on profit, and the backtest
> covers only four years. We also report honest negative findings: the yield model is not clearly better than a
> three-year average, and a simple "last price" forecast is as good as machine learning for prices. The tool is
> available as an interactive web application.

(Numbers: [A2], [A3]. Keep the last two sentences; examiners value them.)

---

## Chapter 1. Introduction

**What to write:** the problem, why it matters, what you built, what the report contains.

Key points (adapt):
1. *Context.* Maharashtra grows cotton, soybean, sugarcane, rice, wheat, jowar, tur and maize, in both the
   monsoon (kharif) and winter (rabi) seasons. Rainfall is uneven across regions and years, so water is a
   limiting resource, and sugarcane in particular is very water-hungry.
2. *The gap.* Farmers decide mostly by habit and recent prices. Tools that look at only profit tend to
   recommend one or two thirsty, high-margin crops. A good plan must trade off profit against water,
   fertilizer, food security and risk.
3. *What AgriOpt does.* Given a farm size and water budget, it recommends hectares per crop, shows the trade-offs
   against simpler plans, and shows how the plan would have performed in past years.
4. *Honest headline.* Same profit as the current crop mix, about 36-39% less water [A1, A3]. It is a
   decision-support tool, not an oracle.
5. *Report structure.* One short paragraph listing the chapters.

**Figures:** `fig02_how_it_works.png` (one-glance overview). **Read:** `README.md` (first page).

## Chapter 2. Problem statement and objectives

**Problem statement (draft):** "Given a farm of L hectares in Maharashtra, a seasonal water budget, a minimum
share of food crops and a cap on any single crop, decide how many hectares to give each of eight crops so that
profit is high, water use and fertilizer use are low, and (optionally) risk is low."

**Objectives (suggested list):**
1. Build a per-hectare profile (yield, price, cost, water, fertilizer, risk) for eight crops.
2. Formulate crop allocation as a multi-objective optimisation problem and solve it.
3. Compare the recommendation with simple baselines (current mix, profit-maximising plan, same-profit-less-water plan).
4. Test the approach honestly with a leak-free historical backtest.
5. Deliver the result as an easy-to-use web application.

**Read:** `docs/formulation.md` (sections "Decision variables" to "Constraints").

## Chapter 3. Literature review

**What to write:** 4 short sub-sections, 2-3 references each, then the gap.
1. *Multi-objective crop planning.* Sarker & Ray (2009) model crop planning with several objectives and
   evolutionary algorithms. NSGA-II (Deb et al. 2002) is the standard algorithm; NSGA-III (Deb & Jain 2014)
   handles more objectives.
2. *Crop yield prediction.* van Klompenburg et al. (2020) review machine-learning yield prediction; Jeong et al.
   (2016) show Random Forests work well at regional scale.
3. *Forecast evaluation.* Naive baselines (Hyndman & Athanasopoulos 2021), the Diebold-Mariano test (1995) with
   the Harvey-Leybourne-Newbold correction (1997); conformal prediction for uncertainty (Lei et al. 2018).
4. *Water and risk.* FAO crop-water guidance (Allen et al. 1998; Brouwer & Heibloem 1986) and portfolio risk
   (Markowitz 1952), here applied to a "portfolio" of crops.
5. *The gap AgriOpt addresses (draft):* few published tools combine yield and price forecasts, an explicit water
   budget, a risk measure and an honest leak-free backtest in one Indian-state-level, openly available tool.
   (State this as your positioning, not as a claim that nothing else exists.)

**Source file:** `LITERATURE_AND_REFERENCES.md` (all citations verified; use `references.bib`).

## Chapter 4. Data sources

**What to write:** a table of data, then a paragraph on data quality.

| Data | Source (see references file) | Size / coverage | Used for |
|---|---|---|---|
| Crop area, production, yield | Kaggle compilation of Indian agricultural statistics | 19,689 rows, 30 states, 55 crops, 1997-2020 | yield model |
| Mandi (market) prices | CEDA Agmarknet API; Kaggle mandi CSV (secondary) | 7 crops, monthly, 2001-2025; none for sugarcane | price model |
| Cost, MSP | PIB / CACP releases, `data/reference/` | all-India cost per quintal | economics |
| Sugarcane price | CCEA Fair and Remunerative Price | Rs 355/qtl minus Rs 75 transport = Rs 280 | economics |
| Water need, fertilizer | FAO TM3; FAO (2005) | per crop | economics |
| Rainfall | IMD sub-divisional monthly 1901-2015; IITM areas | last 30 years, 4 subdivisions | net irrigation |

Key points: (1) yield and production numbers were checked for unit consistency (rice is milled-rice
equivalent; cotton is bales) - see `docs/units.md`; (2) three extreme single-observation rows were dropped
(`reports/results/feature_audit.md`); (3) fertilizer columns in the yield dataset turned out to be a year proxy
and were excluded; (4) Maharashtra yield data stops at 2019.

**Figures:** `reports/eda/yield_over_years_by_crop.png`, `reports/eda/prices_monthly.png`.
**Read:** `reports/eda/eda_report.md`, `docs/reference_data.md`, `docs/units.md`.

## Chapter 5. Methodology

Split into six sections. For each: one paragraph "what", one "why", one "limit".

### 5.1 Yield model
- *What:* a Random Forest (an average of many decision trees) trained on all-India data up to 2015, using crop,
  season, state, year and rainfall; predicts yield in tonnes or bales per hectare, converted to quintals of
  marketed product. Chosen on a 2013-2015 validation window, not on the test years.
- *Uncertainty:* split conformal prediction gives 90% intervals; real coverage was 94.1% overall, only 75% for
  cotton and tur [C5].
- *Honest result:* on the eight decision crops, one year ahead, it beats a last-3-year average on only 3 of 8
  crops [C3]. Say it plainly.
- **Figure:** `fig07_yield_vs_baseline.png`. **Read:** `reports/results/yield_decision_crops.md`, `yield_findings.md`.

### 5.2 Price model
- *What:* three forecasters per crop: Naive (repeat last price), Seasonal-Naive, XGBoost. The deployed 12-month
  forecast is the Naive one because it was never worse [C1]. An optional "MSP floor" never lets the forecast
  fall below the support price. Sugarcane has no market price series, so its price is the government FRP.
- *Statistics:* the difference between Naive and XGBoost is not statistically significant once crops are treated
  as moving together [C2].
- **Figure:** `fig11_price_forecast.png`. **Read:** `reports/results/price_findings.md`, `price_significance.md`.

### 5.3 Per-hectare economics
- Profit per hectare = yield x farm-gate price - cost. Cost is given per quintal, so it is multiplied by yield.
  Sugarcane stays in the ground about 15 months, so its yield, water and fertilizer are scaled to a one-year
  basis; its price is FRP minus Rs 75/quintal harvesting-and-transport. All crops go through one function so the
  app, the cache and the backtest cannot disagree.
- Table of the eight crops: `KEY_NUMBERS.md` section 3 (sugarcane Rs 61,141/ha, rice Rs 24,328/ha, jowar only Rs 1,222/ha).
- **Read:** `README.md` ("How per-hectare economics are computed"), `src/agriopt/optim/params.py` (function `economic_row`).

### 5.4 Water model
- Net irrigation = water the crop needs minus the rain it can actually use, added up **month by month** (a very
  wet month does not make up for a dry one later). Crop need comes from FAO tables; rain from IMD data using the
  standard effective-rainfall formula. "Dry year" is a real observed year near the 20th percentile of usable rain.
- Numbers: [E1]. **Read:** `docs/water.md` section 9 (the current method); sections 1-8 are the background.

### 5.5 Optimizer
- Decision: hectares per crop (8 numbers). Objectives: maximise profit, minimise water, minimise fertilizer.
  Constraints: kharif land, rabi land (cotton, tur and sugarcane use land in both seasons), water budget, food
  crops at least 30% of cropped area, at most 50% of the farm in one crop.
- Method: NSGA-II (a genetic algorithm that returns a whole set of best trade-off plans, the *Pareto front*);
  one plan is picked using weights (profit 0.5, water 0.3, fertilizer 0.2). Because the three objectives are all
  linear, the picked plan is then "polished" by linear programming so it is exactly optimal for its own water and
  fertilizer. An exact LP is also used as a reference to check NSGA-II [D4].
- Baselines: B1 current mix; B2 maximum profit; B3 same profit as B1 with least water.
- **Figures:** `fig04_pareto_front.png`, `fig05_allocation_by_crop.png`. **Read:** `docs/formulation.md`
  (note: the "Baselines" and "Risk metric" parts describe the first version; `REPORT_GUIDE` and `KEY_NUMBERS`
  describe the final one - see the note in that file).

### 5.6 Risk model and risk-aware mode
- Risk is measured from 18-21 years of each crop's revenue, after removing its trend; the covariance matrix
  captures that crops tend to fail together (mean correlation 0.49 [D10]). Portfolio risk = sqrt(x' Sigma x).
- Risk-aware mode (NSGA-III, four objectives) minimises risk **per rupee of profit**, so that leaving land idle
  cannot look "safe". Mark this mode as **experimental**: in the app's medium and large presets it puts 75-78%
  of profit on sugarcane [D6], and its recommended plan moves 0.7 ha per crop between random seeds [D8].
- **Figure:** `fig10_risk_correlation.png`. **Read:** `reports/results/risk_matrix.md`, `risk_strategies.md`.

### 5.7 Backtest design
- For each year t from 2016 to 2020, plan using only information available on 1 May of year t (yield model
  refit on data up to t-1, last known prices, historical costs), then score the same plan against what actually
  happened. Only 2016-2019 can be scored (no 2020 yield data), so n = 4.
- Strategies compared: current mix (B1), its closest feasible version (B1_SCALED), profit-max (B2),
  same-profit-less-water (B3), AgriOpt (OURS), risk-aware (MODEL_B), and "oracles" that know the future (to
  measure the best possible).
- **Figures:** `fig06_backtest_profit_by_year.png`, `fig09_backtest_capture_ratio.png`.
  **Read:** `docs/backtest.md`, `reports/results/backtest_summary_v2.md`.

## Chapter 6. System architecture and implementation

**What to write:** the architecture figure, then the app tour.
1. *Offline vs online.* Heavy work (loading a ~528 MB model, running the optimizer for preset farms) is done
   offline by one script, which writes one data file; the web app only reads that file, so it starts fast and
   runs on free hosting.
2. *The app (8 tabs):* Recommendation (hectares, profit, water, fertilizer, food share, profit risk, plain-English
   explanation); Trade-offs (the Pareto chart); Strategy comparison; Risk; Backtest 2016-2019; Regional view
   (Konkan vs Marathwada); Model inputs and evidence; About and limitations.
3. *Inputs:* land, water budget, minimum food share, maximum share per crop, price mode, region, water basis,
   priority slider (profit vs sustainability), risk-aware switch, what-if price changes, five farmer presets.
4. *Quality control:* automated tests, including one that re-solves the table values from the stored data to make
   sure published results never go stale, and a test that the app starts on the exact software versions used in
   deployment.
5. *Tools:* Python, scikit-learn, XGBoost, pymoo, SciPy, Streamlit, Plotly.

**Figures:** `fig01_architecture.png`, `fig12_app_recommendation.png`, `fig13_app_tradeoffs.png`,
`fig14_app_regional.png`. **Read:** `README.md` (Architecture, Reproduce), `app/streamlit_app.py` (skim).

## Chapter 7. Results

Present in this order, each with one table or figure and one sentence of "so what".

1. **Headline: same profit, less water.** `fig03_headline_water_profit.png` [A2, A3, A4]. Planning-time comparison
   [A1].
2. **All strategies side by side** (table in `README.md`, "Decision backtest ... every baseline"; `fig06`).
   Point out that the profit-max plan earns more [A7] and perfect foresight only 14-18% more [A8].
3. **Tight water** [A5]: AgriOpt beats the closest feasible current mix in 3 of 4 years.
4. **Trade-off surface** `fig04_pareto_front.png`; recommended plan sits on the exact LP front [D4].
5. **Recommended crop mixes** `fig05_allocation_by_crop.png`: current mix uses 8 crops, AgriOpt about 3.
6. **Regions at equal water** `fig08_regions_equal_budget.png` [E2, E3].
7. **Model results** `fig07` [C3], `fig11` [C1, C2], conformal [C5].
8. **Risk** [D5, D6, D8], with the experimental label.
9. **What information matters** (ablation) [D9].

## Chapter 8. Discussion

Key points:
1. *Why not higher profit?* The optimizer works with forecast prices, which look better than what happens
   (forecast profit +51.6% vs realized +0.6% [A6]). It is also asked to save water and fertilizer, not only to
   earn money; the pure profit-max plan does earn more [A7].
2. *Why does saving water cost so little profit?* Crops differ a lot in profit per cubic metre of water
   (`KEY_NUMBERS.md` section 3: rice about Rs 4.2, wheat Rs 4.1, sugarcane Rs 3.8, but cotton Rs 1.5 and
   jowar, soybean and maize under Rs 1). The optimizer shifts land toward rice, wheat and a little sugarcane
   (`fig05`) and away from the water-hungry, low-return crops.
3. *Where would more accuracy help?* In yields: perfect yield knowledge closes about two thirds of the gap to
   perfect foresight, prices only about one third [C4].
4. *Regional lesson.* At the same water, regions differ by up to 22% in achievable profit [E2].
5. *Honest negatives.* The ML yield model barely beats a 3-year average [C3]; the simple price forecast is hard
   to beat [C1, C2].

## Chapter 9. Limitations (ready draft - keep all of it)

> 1. **Short backtest.** Only four years (2016-2019) can be scored because Maharashtra yield data ends in 2019.
>    With four paired years no statistical significance test can reach the usual 5% level, so we report per-year
>    differences instead and treat the results as four case studies.
> 2. **All-India costs.** Cost of cultivation is an all-India figure per quintal multiplied by Maharashtra yield,
>    and for several crops it is derived from the published MSP margin. Profit margins are therefore partly set
>    by policy rather than measured per state. State-wise cost per hectare is the most valuable missing input.
> 3. **Yield model.** On the eight decision crops it beats a three-year average on only three crops, and the
>    backtest shows yield error is the largest source of lost profit.
> 4. **Sugarcane.** It has the highest net profit per hectare in the model but no market price series (the
>    government FRP is used), so its measured price risk is artificially low. In the experimental risk-aware
>    presets it takes 75-78% of profit, which should not be read as advice.
> 5. **Water model.** The FAO seasonal water need is spread evenly over the season because no monthly profile
>    was available; rice percolation losses are not included; rainfall data end in 2015.
> 6. **Old and generic inputs.** Fertilizer doses are 2003/04 all-India figures (soybean uses a recommended dose);
>    tur's water need uses the bean figure as a proxy; the harvest-year convention used for risk is assumed.
> 7. **Model farm.** Results are for a 10 ha farm built from the state-level crop mix. We did not run field
>    trials or use farm-level data.
> 8. **One planning date.** The backtest plans everything on 1 May. A real farmer could adjust winter crops later.
> 9. **Risk-aware mode is experimental** and less stable across random seeds (0.7 ha per crop vs 0.18 ha).

## Chapter 10. Conclusion

Draft: "AgriOpt shows that a transparent, data-driven plan can keep a Maharashtra farm's profit at about the
current level while using roughly 36-39% less water. The tool is honest about its limits: it does not beat the
current mix on profit, the backtest is short, and the yield forecast is only as good as a simple average. Within
those limits it gives farmers and planners a way to see the trade-offs between profit, water, fertilizer and
risk before committing land."

## Chapter 11. Future work

1. State-wise (Maharashtra) cost of cultivation per hectare from the CACP reports - the single most valuable upgrade.
2. A better yield model (district-level data, weather within the season, shrinking the model toward a recent average).
3. A two-stage plan (commit kharif crops in May, decide winter crops in October).
4. Longer backtest when newer yield data become available.
5. A monthly crop-water profile and a percolation estimate for rice.
6. Field validation with extension officers and farmers; a Marathi/Hindi interface.

## References

Use `LITERATURE_AND_REFERENCES.md` and `references.bib`. Cite only what you use.

## Appendices (suggested)

A. The 8-crop economics table (`KEY_NUMBERS.md` section 3). B. Full backtest table (`reports/results/backtest_summary_v2.md`).
C. Glossary (`GLOSSARY.md`). D. How to reproduce (`README.md`, "Reproduce"). E. Screenshots (`fig12`-`fig14`).

---

### Note on `docs/formulation.md`

That file was written for the first version of the optimizer. Where it differs from this guide, this guide is
right: (a) the current mix baseline now fills both seasons' land and is built season by season; (b) the
recommended plan is LP-polished; (c) profit risk is sqrt(x' Sigma x) not the independent-crops formula; (d) cost
is per quintal x yield with sugarcane annualised; (e) food share counts season-hectares. The file carries a
banner saying so.
