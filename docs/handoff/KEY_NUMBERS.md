# Key numbers (single source of truth)

Use **only** the numbers on this page. Every number comes from a file committed in this repo
(path in the "Source" column, relative to the repo root). If a number is not here, ask before using it.

**The main message to use everywhere**

> AgriOpt keeps profit about the same as the current crop mix while using about 36-39% less water.
> It does **not** claim higher profit than the current mix.

Why "36-39%": the planning-time comparison gives 35.7% less water and the 4-year backtest gives
38.9% less (see rows A1 and A3). Quote the range, or quote the backtest figure (38.9%) when you
mean "what actually happened in 2016-2019".

Terms used below are explained in `GLOSSARY.md`. "Current mix" = the historical Maharashtra crop
mix on a 10 ha farm (called B1 in the files). "AgriOpt" = the recommended plan (called OURS in the files).

---

## 1. Headline results

| # | Claim | Final number | Source file | Safe wording |
|---|---|---|---|---|
| A1 | Water saved, planning-time comparison (10 ha, current water budget, market prices) | **-35.7%** (67,368 vs 104,851 m³) | `reports/results/optim_strategies.md` (water=current, price=market, row OURS) | "In the planning model the recommended plan uses about 36% less water than the current mix." |
| A2 | Realized profit in the backtest, default water | AgriOpt **₹230,769/yr** vs current mix **₹229,479/yr** (**+0.6%**, +₹1,290; better in 2 of 4 years) | `reports/results/backtest_summary_v2.md` (sections 2 and 5); chart `docs/handoff/figures/fig03_headline_water_profit.png` | "In a 4-year backtest AgriOpt earned about the same profit as the current mix." |
| A3 | Water saved in the same backtest | **-38.9%** (64,291 vs 105,161 m³ per year, the 4 scored years) | `reports/results/backtest_rows.csv` (default scenario, years 2016-2019; the figure is computed from the `water_m3` column) | "...while using about 39% less water." |
| A4 | Profit per 1,000 m³ of water, backtest default | AgriOpt **₹3,714** vs current mix **₹2,181** (1.7x) | `reports/results/backtest_summary_v2.md` section 2 | "AgriOpt earns about 1.7 times as much profit per unit of water." |
| A5 | Tight water (70% of the current mix's use), backtest | AgriOpt ₹200,645/yr; the current mix would need more water than allowed (infeasible); the closest feasible version of the current mix earns ₹154,455/yr | `reports/results/backtest_summary_v2.md` section 2 | "When water is cut by 30%, AgriOpt beats the closest feasible current mix (3 of 4 years)." Do **not** say it beats the raw current mix there (it loses by ₹28,834/yr, section 5 of the same file). |
| A6 | Planning-time profit uplift (forecast prices) | +51.6% (current water, market prices) | `reports/results/optim_strategies.md` | **Do not present as an expected gain.** It is based on forecast prices, which are too optimistic; the backtest (A2) shows +0.6% on realized outcomes. Under MSP-floor prices the same table shows -7.3%. |
| A7 | Profit-maximising plan (B2) is better on profit | B2 earns ₹288,084/yr (default) and ₹259,036/yr (tight) in the backtest, more than AgriOpt in every year | `reports/results/backtest_summary_v2.md` section 5 | "A plain profit-maximising plan earns more but uses all the water; AgriOpt trades a little profit-seeking for large water savings." |
| A8 | Perfect foresight (ORACLE) upper bound | ₹339,253/yr (default), ₹295,022/yr (tight) | `reports/results/backtest_skill.md` | "Even perfect knowledge of yields and prices would add only 14-18% over the profit-max plan." |

## 2. Data sizes and sources

| # | Item | Number | Source file |
|---|---|---|---|
| B1 | Yield dataset size | 19,689 rows, 30 states, 55 crops, years 1997-2020 | `reports/eda/eda_report.md` section a |
| B2 | Decision crops | 8: rice, wheat, jowar, soybean, cotton, sugarcane, tur, maize | `README.md`; `src/agriopt/config.py` |
| B3 | Maharashtra yield data usable for scoring | ends in 2019 (no 2020 rows) | `reports/results/backtest_summary.md` (first paragraph) |
| B4 | Mandi price history | 7 crops with monthly modal prices, about 263-296 months each (2001/2002 to Oct 2025); **sugarcane has no mandi series** | `reports/eda/eda_report.md` ("Price coverage") |
| B5 | Rainfall | IMD sub-divisional monthly rainfall 1901-2015; the last 30 years (1986-2015) are used; 4 Maharashtra subdivisions | `docs/water.md` sections 1 and 3 |
| B6 | Backtest years | 2016-2019 scored (n = 4); 2020 planned but cannot be scored | `reports/results/backtest_summary.md` |
| B7 | Trained yield model size | about 528 MB (why the app uses a pre-built cache) | `README.md` (Architecture) |

## 3. Per-hectare economics (the 8 crops)

Source for the whole table: `data/processed/crop_params_cache.json`, block `price_modes.market`
(rounded). Costs are all-India per quintal times Maharashtra yield; sugarcane is annualised over a
15-month cycle and its price is FRP minus ₹75/qtl harvesting-and-transport (`README.md`, "How
per-hectare economics are computed").

| crop | yield (qtl/ha) | price (₹/qtl) | cost (₹/ha) | profit (₹/ha) |
|---|---|---|---|---|
| rice | 24 | 2,600 | 37,624 | 24,328 |
| wheat | 16 | 2,621 | 20,378 | 22,734 |
| jowar | 9 | 2,600 | 22,486 | 1,222 |
| soybean | 12 | 3,923 | 42,834 | 4,479 |
| cotton | 11 | 6,442 | 59,049 | 14,954 |
| sugarcane | 571 | **280** | 98,854 | **61,141** |
| tur | 9 | 6,269 | 43,858 | 10,717 |
| maize | 19 | 1,814 | 28,436 | 5,780 |

**Profit per cubic metre of water** (derived: profit per hectare divided by crop water need per hectare, both
from the same cache block, total-need water basis; rounded). Use it to explain why the optimizer prefers some crops.

| rice | wheat | sugarcane | tur | cotton | maize | soybean | jowar |
|---|---|---|---|---|---|---|---|
| ₹4.2 | ₹4.1 | ₹3.8 | ₹2.7 | ₹1.5 | ₹0.9 | ₹0.8 | ₹0.2 |

## 4. Model quality

| # | Claim | Number | Source file | Safe wording |
|---|---|---|---|---|
| C1 | Price model: simplest method wins | Mean error (₹/qtl) of "Naive" (use the last known price) at 3 / 6 / 12 months ahead: **373.6 / 512.6 / 750.9**; XGBoost: 454.4 / 743.2 / 1,194.3 | `reports/results/price_results.md`, `price_findings.md` | "A simple 'last price' forecast beat the machine-learning model at every horizon." |
| C2 | Naive vs XGBoost, is the difference real? | **Not statistically significant** at any horizon (p = 0.076 / 0.081 / 0.071 at 3 / 6 / 12 months; the bootstrap check gives 0.065 / 0.038 / 0.109) | `reports/results/price_significance.md` | "The two are statistically indistinguishable; Naive is simply never worse." Do not say "Naive significantly beats XGBoost". |
| C3 | Yield model vs a 3-year average (8 decision crops, one year ahead, 2016-2019) | RandomForest beats the 3-year average on **3 of 8** crops (rice, wheat, soybean); loses on jowar, cotton, sugarcane, tur, maize. Average error 19.4% vs 19.7% | `reports/results/yield_decision_crops.md`; chart `fig07_yield_vs_baseline.png` | "The yield model is about as good as a 3-year average; it is not a clear improvement." |
| C4 | Where forecasts lose money | Knowing the true **yields** in advance closes ~64-68% of the gap to perfect foresight; knowing true **prices** closes ~35-37% | `reports/results/backtest_skill.md` | "Yield error costs more than price error." |
| C5 | Conformal intervals (90% target) | Real coverage 94.1% overall (152 Maharashtra test rows, 2016-2020); cotton and tur only 75% | `reports/results/yield_conformal.md` | "The uncertainty bands are about right overall, weaker for cotton and tur." |
| C6 | Yield model on unseen state | Excluding Maharashtra from training raises its error from 0.506 to 0.750 (+48.4%) | `reports/results/yield_loso.md` (Maharashtra row) | "Local data matters." Note the error is in mixed units; use for direction only. |
| C7 | Old "R² = 0.938" for the yield model | **Do not use** (see section 7) | `reports/results/yield_results.md` (note at top) | n/a |

## 5. Optimizer and risk

| # | Claim | Number | Source file |
|---|---|---|---|
| D1 | Same profit, less water (B3 vs current mix, tight/market) | **-58.5%** water at identical profit | `reports/results/optim_strategies.md` |
| D2 | Profit-max plan averages | +65.1% profit over the current mix across 6 scenarios, in about 3 crops | `reports/results/optim_findings.md` |
| D3 | Current mix is food-feasible | food-crop share 45% (minimum is 30%); it breaks the water limit only in the two tight scenarios | `reports/results/optim_strategies.md`, `optim_findings.md` |
| D4 | NSGA-II vs exact LP | NSGA-II front quality is 1.07x the simple LP reference and 0.947x the denser grid reference; the final recommended plan is **LP-polished** (exactly optimal for its own water and fertilizer; raw NSGA-II was 0.1-2.0% below) | `reports/results/optim_front_quality.md`, `optim_front_quality_v2.md`, `reports/results/CHANGELOG_fixes.md` (Task 3) |
| D5 | Risk-aware plan (Model B) vs standard plan (Model A), current water | profit +17.0%, water +21.2%, fertilizer -1.8%, rupee risk +7.0%, but risk per rupee of profit **-8.6%** (0.254 vs 0.278) | `reports/results/optim_findings_v2.md`, `risk_strategies.md` |
| D6 | Risk-aware presets lean on sugarcane | sugarcane gives **75-78% of profit** in the app's risk-aware medium and large presets | `data/processed/crop_params_cache.json` (`preset_results`), `reports/results/CHANGELOG_fixes.md` (Task 5 and final section) |
| D7 | Standard presets | sugarcane share of profit 3-53% (median ~31%) | same cache file; `README.md` ("How per-hectare economics are computed") |
| D8 | Seed stability (10 seeds) | NSGA-II recommended allocation moves 0.18 ha per crop between runs; NSGA-III moves **0.70 ha** | `reports/results/optim_seed_robustness.md` |
| D9 | Information ablation (profit loss when information is worse), tight water | mean-price 14.4%, no-cost-data 12.3%, no-ML-yield 11.3%, MSP-price 11.3%. Current water: MSP-price 12.0%, mean-price 8.9%, no-cost 8.9%, no-ML-yield 4.3% | `reports/results/ablation_decisions.md` |
| D10 | Crop price correlations | mean correlation of crop revenues 0.49 (crops move together) | `reports/results/risk_matrix.md` |

## 6. Water and regions

| # | Claim | Number | Source file | Safe wording |
|---|---|---|---|---|
| E1 | Net irrigation need, state-wide, normal year (mm) | rice 266, wheat 516, jowar 516, soybean 66, cotton 433, sugarcane 1,318, tur 136, maize 91 | `reports/results/water_basis_comparison.md` | "Net irrigation = crop water need minus usable rain, added up month by month." |
| E2 | Regions at the **same** water budget (54,532 m³, normal rain) | AgriOpt profit: Konkan ₹273,010 > Maharashtra ₹258,265 > Madhya Maharashtra ₹244,796 > Vidarbha ₹239,686 > Marathwada ₹224,101 | `reports/results/region_equal_budget.csv`; `region_comparison.md`; chart `fig08_regions_equal_budget.png` | "At equal water, Konkan does best and Marathwada worst." |
| E3 | Dry year, tight water, Marathwada | AgriOpt earns 11.2% **less** than the current mix (₹162,350 vs ₹182,833) | `reports/results/region_equal_budget.csv` (rainfall=dry, water_scenario=tight) | "In a dry year with little water, Marathwada is hardest hit." |

## 7. DO NOT USE - old numbers

These were produced before the economics fixes or by methods that overstated the result. If you see them
in an old slide, email or draft, replace them.

| Old number / claim | Correct number now | Why it changed |
|---|---|---|
| "B2 gives +108.4% profit over the current mix" | +65.1% (mean of 6 scenarios) | The old backtest and tables treated cost per quintal as cost per hectare, so "profit" was nearly revenue. Sugarcane was also not annualised. |
| "OURS earns ₹9,051-9,271 per 1,000 m³ of water" (current mix ₹5,636) | **₹3,714** (current mix ₹2,181) | Same cost bug; profit was about 2.4-2.6x too high. |
| "OURS captures 0.966 of the best possible profit" | 0.871 (default water) | Same cause; also B2 no longer equals the oracle. |
| "B3 saves 57.5% water" | 58.5% | The economics fixes, and a fairer current-mix baseline that now uses all its land (it used only 62-76% before), change the reference. |
| "OURS earns +75.6% over the current mix" | +51.6% (planning time), +0.6% (backtest) | Fairer current-mix baseline; and the backtest shows the planning figure is optimistic. |
| "Marathwada beats Konkan" (₹253,960 vs ₹232,078) | At equal water: **Konkan ₹273,010 beats Marathwada ₹224,101** | Old comparison gave the rainier region a smaller water budget. |
| "Naive significantly beats XGBoost at 6 and 12 months (p = 0.031, 0.020)" | Not significant (p = 0.081, 0.071) | The old test treated 7 crops as 7 independent series; they move together. |
| "Yield model RandomForest R² = 0.938" | Do not quote. Use C3 (beats a 3-year average on 3 of 8 crops) | The pooled R² mixed tonnes, bales and milled-rice units, so it mostly measured crop size. |
| "Dropping the ML yield changes nothing" | Dropping it costs 4.3-11.3% of profit in the profit-max planner | The old result was an artefact of the sugarcane bug. |
| "Model B (risk-aware) lowers risk by 4%" | Risk per rupee -8.6%, but rupee risk +7.0% | The risk objective was changed (the old absolute-rupee objective rewarded leaving land idle) and the economics were fixed; Model B is now compared on risk per rupee of profit. |
| "Profit risk +100% vs current mix" in the app | +1% to +40% depending on the preset | The old "independent crops" risk understated the current mix's risk. |
| "Rice needs 0 mm net irrigation" / soybean, tur, maize "0 mm" | rice 266, soybean 66, tur 136, maize 91 mm | The old method let a rainy July cover a dry September. Now added month by month. |
| "Sugarcane gives 59-81% of profit in every plan" | 3-53% in standard presets | Old economics priced one 15-month cycle as if it were one year, at gross FRP. |
| "Marathwada preset: 71% of profit from sugarcane" | ~37% (standard) | Water model changed (real dry year, monthly balance). |
| "B2 equals the oracle in every cell" | Identical in 0 of 8 cells | Artefact of the cost bug. |
| "OURS wins 4/4 years against the current mix" | 2 of 4 (default); 1 of 4 (tight, raw current mix) | Cost bug; see A2/A5. |
| Any figure from an older results zip, old slides or old drafts | Re-check against this page | Produced by older code (before the economics fixes). |

## 8. Things that are NOT in the repo (do not invent them)

- Team names, guide name, college/university report format: use the placeholders `[TEAM NAMES]`, `[GUIDE NAME]`, `[COLLEGE FORMAT]`.
- Maharashtra-specific cost of cultivation (₹/ha). The model uses all-India cost per quintal; this is a known limitation.
- Any real-farmer field trial. The backtest is the only "real-world" evidence.
