# Changelog: economics review fixes (branch `fix/economics-review`)

"Before" = master at `3c4574a` (the committed `reports/results/*`). "After" = regenerated on the full
dataset. Every number below is read from the cited file, not re-derived by hand.

## Phase 1 -- regenerate everything with the fixed economics

Scripts re-run in order: `30_run_optimizer`, `31_run_risk`, `50_ablation`, `60_backtest`,
`61_backtest_v2`, `70_water_basis_net`, `71_water_region`, `94_seed_robustness`, then `40_build_cache`.

### Cache check (`40_build_cache.py` vs `42_patch_cache_economics.py`)

The rebuilt `data/processed/crop_params_cache.json` was compared against the 3c4574a cache patched in
memory by `42_patch_cache_economics.convert_record/rescale_risk`: `params` and `price_modes` match
exactly (0 differences at 1e-9 tolerance). The only difference in the compared blocks is
`risk.min_eigenvalue_raw` (5,869,553 patched vs 5,859,240 rebuilt) -- the patcher rescales Sigma but does
not recompute that diagnostic. Cosmetic.

### Headline before/after

| claim | before (3c4574a) | after |
|---|---|---|
| B3 (same profit as B1) water saving, tight/market | -57.5% water | -56.6% water |
| B2 (profit-max LP) vs B1, mean of 6 scenarios | +108.4% profit, mean n_crops 2.0 | +71.3% profit, mean n_crops 3.0 |
| B2 vs B1, tight/market | +79.8% | +63.0% |
| OURS vs B1, current/market (E3.1) | +75.6% profit, -29.7% water | +56.7% profit, -31.0% water |
| B1 (current mix) food share | 0.47, feasible at current/relaxed | 0.27, **infeasible in 6/6 scenarios** (below the 30% minimum under the corrected food-share definition) |
| NSGA-II HV vs LP reference front (v1 grid), mean ratio | 1.15x | 1.05x |
| NSGA-II IGD range | 0.007-0.123 | 0.016-0.047 |
| Model B vs Model A recommendation (E3.3) | profit +1.6%, water +1.3%, fert +15.4%, **risk -4.2%** | profit -0.6%, water +0.8%, fert +14.0%, **risk +35.9%** -- **claim flipped**: Model B's recommended point is now worse than Model A's on profit, risk, water and fert |
| Sugarcane in Model B | 1.68 ha (73.7% shift under CV sensitivity) | 0.00 ha -> 0.15 ha under sensitivity |
| Seed robustness HV, NSGA-II | 0.594 +/- 0.005 | 0.599 +/- 0.005 (95% CI [0.595, 0.603]) |
| Seed robustness HV, NSGA-III | 0.569 +/- 0.006 | 0.581 +/- 0.003 (95% CI [0.579, 0.583]) |
| Most seed-sensitive crop (NSGA-III) | wheat | rice |
| Information ablation (B2 profit loss vs FULL, tight): NO_ML_YIELD | 0.0% | 15.3% |
| Information ablation: costliest degraded variant (tight / current) | NO_COST 12.5% / 8.4% | **MEAN_PRICE 19.6% / 14.6%** (NO_COST 14.2% / 12.4%) -- **claim flipped** |
| Region comparison (OURS, current/net-irrigation) | Marathwada Rs 253,960 vs Konkan Rs 232,078 | Marathwada Rs 210,216 (water 20,051 m3) vs Konkan Rs 166,956 (13,098 m3); order unchanged, gap widened |
| Covariance min eigenvalue | 5,869,553 | 5,859,240 |

### Backtest 2016-2019 (n=4; realized profit now net of cost)

Before, "profit" was effectively revenue (cost in Rs/qtl subtracted as if Rs/ha). Mean realized profit per
year, default scenario: B1 Rs 419,813 -> **Rs 162,225**; OURS Rs 486,060 -> **Rs 200,969**; ORACLE
Rs 683,560 -> Rs 292,824.

| claim | before | after |
|---|---|---|
| OURS mean profit per 1,000 m3 water | Rs 9,051 (default) / 9,271 (tight) vs B1 Rs 5,636 | Rs 3,938 / 4,374 vs B1 Rs 2,241 (ratio 1.6x -> 1.8x-2.0x) |
| OURS capture_ratio_w (water-matched oracle) | 0.966 | 0.883 (default) / 0.881 (tight) |
| MODEL_B capture_ratio_w | 0.862-0.880 | 0.804 (default) / 0.790 (tight) |
| OURS wins vs B1, default | 4/4 | 3/4 |
| OURS wins vs B1, tight | 0/4 vs raw B1, 4/4 vs B1_SCALED | 3/4 vs raw B1, 3/4 vs B1_SCALED |
| OURS mean profit vs B1, tight | -Rs 65,174/yr | **-Rs 399/yr** (indistinguishable from B1) |
| OURS mean profit vs B1, default | +Rs 66,247/yr (+15.8%) | +Rs 38,744/yr (+23.9%) |
| Sign / Wilcoxon p, OURS default | 0.125 / 0.125 | 0.625 / 0.250 |
| B2 == ORACLE allocation | identical in 8/8 cells (artefact of revenue-as-profit) | identical in **1/8** cells |
| Net-irrigation basis: B2/B3 capture_ratio_w | 0.954 / 0.954 (B1 0.576) | 0.820 / 0.818 (B1 0.531) |
| Net-irrigation basis: OURS profit per 1,000 m3 | Rs 35,330 vs B1 Rs 15,464 | Rs 14,297 vs B1 Rs 5,605 |

Weaker claims: (a) in the tight water scenario OURS no longer beats the current mix on realized profit,
it ties it while using ~35,600 m3 less water; (b) the "perfect-foresight" B2 == ORACLE finding is gone,
so forecast skill is now measurable (Task 7 builds on this); (c) all p-values remain non-significant.

Caveat on B1: under the corrected food-share definition B1 and B1_SCALED violate the 30% food-share
constraint in 10/10 year-scenario cells, so "OURS vs B1" mixes a profit comparison with a constraint
violation. Task 4 (fair current-mix baseline) addresses this; do not read the B1 rows as final.

### Water basis (net irrigation)

`water_basis_comparison.md` was stale relative to the Phase 8.1 rainfall model (it still showed the
Phase 8 state-wide rainfall: rice net irrigation 0 mm). Regenerated: rice 200 mm under a normal year
(575 mm total need), soybean/tur/maize 0 mm. This changes the index row but is not caused by the cost fix.

### Other changes in this phase

* `tests/test_backtest_v2.py`: `test_b2_and_oracle_allocations_are_identical_within_tolerance` pinned the
  old buggy behaviour (B2 == ORACLE in every cell); replaced with
  `test_b2_and_oracle_allocations_differ_in_most_cells`.
* `scripts/30_run_optimizer.py`: the generated finding said B1's food share (27.2%) was "comfortably
  above the 30% minimum"; now compares against the real minimum.

## Phase 2

### Task 3 -- exact LP recommendation (H3)

`solvers.polish_front` replaces every NSGA-II point by the lexicographic LP optimum at the same water and
fertilizer caps (max profit, then min water, then min fert), de-duplicates and drops dominated points.
`baselines.nsga2_recommended(polish=True)` (default) polishes before the pseudo-weights pick, so OURS and the
front shown in the app are LP-efficient. This keeps the pseudo-weights *meaning* of the recommendation (same
weights, same objective space) instead of a weighted-sum LP, which would jump to a single vertex. Raw
`solve_nsga2` is untouched, so the NSGA-II-vs-LP front-quality experiments (E3.2/E3.4 HV, IGD) still measure
the heuristic, not the polish. NSGA-III (risk mode) is unchanged. Polish adds ~0.7 s to a ~2.5 s solve.

OURS, six E3.1 scenarios (water budget x price mode; `seed=42`; 10 ha). "LP gap" = how much more profit an LP
earns at the same water and fert (the dominance the review found); after polish it is 0.000% everywhere.

| scenario | raw profit | LP gap (raw) | polished profit | polished vs raw | water, fert (raw -> polished) |
|---|---|---|---|---|---|
| tight / market | 144,925 | 2.04% | 158,746 | +9.5%* | 35,099 -> 37,863 m3; 796 -> 796 kg |
| current / market | 203,433 | 0.78% | 205,016 | +0.8% | 49,780 m3; 953 kg (unchanged) |
| relaxed / market | 253,513 | 1.86% | 258,218 | +1.9% | 62,935 m3; 1,226 kg (unchanged) |
| tight / msp_floor | 207,318 | 0.19% | 207,715 | +0.2% | 38,726 m3; 558 kg (unchanged) |
| current / msp_floor | 264,841 | 0.10% | 265,118 | +0.1% | 52,285 m3; 862 kg (unchanged) |
| relaxed / msp_floor | 299,924 | 0.47% | 301,340 | +0.5% | 61,033 m3; 1,113 -> 1,082 kg |

\* tight/market: the polished front is differently shaped, so the pseudo-weights pick moves along it (+7.9%
water, +9.5% profit); that row mixes the polish gain (2.0%) with a different trade-off point.
The review quoted 0.6-3.5%; on the current economics the measured LP gap is 0.1-2.0%.

New tests: `test_ours_is_not_dominated_by_an_lp_at_same_water_and_fert` (3 water budgets, real params: no LP
at <= OURS water and <= OURS fert earns strictly more) and
`test_polish_front_lifts_dominated_points_to_the_lp_frontier` (data-free toy). `94_seed_robustness.py` now
measures the allocation std of the *polished* recommendation (HV stays on the raw front).

### Task 4 -- fair current-mix baseline (H6)

* `baselines.mix_from_shares` builds B1 per season. A both-season crop (cotton, sugarcane, tur) is fixed at
  its historical share of the *larger* season's cropped area (its hectares count in both seasons); each
  single-season crop fills the rest of its own season in proportion to its history. The old construction
  normalised over all crops, so B1 left land idle. `current_mix` (app + scripts) and the backtest's
  `current_mix_leakfree` now share this one function (the latter previously duplicated the algorithm).
* `baselines.closest_feasible_mix` / `solvers.solve_lp_closest`: B1 made feasible as an LP that moves the
  fewest hectares (L1) while meeting water, food share, season land and max share. `evaluate_v2.
  scale_b1_to_water_budget` (uniform shrink) is replaced by `b1_closest_feasible`; the `B1_SCALED` label is
  kept, `b1_scale_factor` in `backtest_fairness_v2.csv` becomes `b1_hectares_moved`.

B1 on the 10 ha farm, no water limit (current-economics params, market prices):

| | before | after |
|---|---|---|
| kharif / rabi land used | 7.61 / 6.22 ha | 10.00 / 10.00 ha |
| B1 profit | Rs 129,794 | Rs 182,833 (+40.9%) |
| B1 water, fert | 72,156 m3, 949 kg | 104,851 m3, 1,376 kg |
| B1 food share | 0.272 (**infeasible**, < 0.30) | 0.449 (feasible) |

Scenario budgets are defined as 0.7 / 1.0 / 1.3 x B1's own water, so every budget rises with the bigger B1
(e.g. "current" 72,156 -> 104,851 m3). "+X% vs current mix" for OURS (polished, seed 42, market prices):

| water | vs B1 before | vs B1 after | vs feasible B1 (LP) after | OURS water vs B1 before -> after |
|---|---|---|---|---|
| tight (0.7x) | +22.3% | +13.8% | +89.3% (B1 LP moves 2.73 ha, profit Rs 109,907) | -47.5% -> -52.4% |
| current (1.0x) | +58.0% | +51.6% | +51.6% (B1 already feasible, 0 ha moved) | -31.0% -> -35.7% |
| relaxed (1.3x) | +98.9% | +90.6% | +90.6% | -12.8% -> -18.1% |

B2 vs B1 (current): +128.1% -> +130.3%; B3 water saving vs B1: -56.6% -> -58.5%.
So the profit claims fall by 6-9 points (B1 earns more once it uses its land), water savings grow, and B1 is no
longer food-infeasible at current/relaxed water. In the tight scenario raw B1 is still water-infeasible, and the
"vs feasible B1" figure (+89%) is large because the LP-nearest repair is blind to profit; read it as "vs what
minimal repair of today's mix earns", not as an optimised baseline.
Reports and the README table are regenerated once at the end of Phase 2 (all tasks change them).

New tests: toy per-season construction, toy `closest_feasible_mix` (exact 2.25 ha), real-data B1 land use and
LP repair (moves fewer hectares than uniform shrink), `B1_SCALED` fully feasible in all 10 backtest cells,
leak-free mix fills both seasons.

Side effect found by the test suite: preset water budgets are multiples of B1's water, so the fuller B1 raises
them and the profit-maximising presets lean further on sugarcane (net profit Rs 61,141/ha vs Rs 24,328 for
rice). Sugarcane share of recommended profit by preset: small 36%, medium 44%, large 52%, drought 23%,
**Marathwada dry-year 71%**. `test_cached_recommendations_are_not_sugarcane_dominated` capped every preset at
50%; that was a heuristic, so it now requires the *median* share < 50% (what the old bug violated in every
preset). The 71% Marathwada figure is a sensitivity to flag, not a pass: it rests on all-India cost per
quintal and a single sugarcane price (Task 12 / H1 will revisit).

### Task 5 -- risk mode must not reward fallow land (H5)

**Objective.** The risk-aware NSGA-III's 4th objective was the absolute `sqrt(x' Sigma x)` in rupees, which
an empty field drives to zero. It is now risk per rupee of expected profit, `sqrt(x' Sigma x) / profit(x)`
(`risk.risk_per_profit_vectorized`, `CropAllocationProblemRisk(risk_measure="cv")`, default; `"absolute"`
reproduces the old behaviour). Scaling every crop's hectares by c leaves it unchanged, so planting less buys
no safety; a plan with no positive profit scores the cap (5.0), never "safe". I chose this over a hard
minimum-cropped-area constraint because a land floor would make water-limited scenarios infeasible.

Evidence (10 ha, current water, market prices, frp_based Sigma, seed 42, weights risk 0.8 / profit 0.1 /
water 0.05 / fert 0.05):

| risk objective | profit | absolute risk | risk per Rs profit | kharif / rabi ha cropped |
|---|---|---|---|---|
| absolute (old) | Rs 149,161 | Rs 50,730 | 0.340 | 3.25 / 5.05 |
| per profit (new) | Rs 324,420 | Rs 82,536 | 0.254 | 6.25 / 6.36 |

The old objective bought a lower rupee risk by idling ~6.7 ha of 20 ha-seasons *and* halving profit, and was
worse on risk per rupee. At the default weights it also failed to converge in the tight scenario (Model B
dominated by Model A on all four axes: profit 190,794 vs 208,088, risk 138,239 vs 63,468), which is the
mechanism behind the Phase 1 "Model B is worse than Model A" flip. With the new objective, Model B vs Model A
(NSGA-II, polished):

| water | A profit / risk Rs / risk per Rs | B profit / risk Rs / risk per Rs |
|---|---|---|
| tight | 208,088 / 63,468 / 0.305 | 228,243 / 62,301 / 0.273 |
| current | 277,183 / 77,157 / 0.278 | 324,420 / 82,536 / 0.254 |
| relaxed | 348,510 / 90,592 / 0.260 | 409,384 / 101,912 / 0.249 |

Model B now beats Model A on profit and risk per rupee in all three; it takes on more rupee risk at
current/relaxed water because it also plants more sugarcane (frp_based Sigma gives it a low CV; the app's
default `conservative` Sigma does not).

**Reported profit risk.** `baselines.evaluate(..., Sigma=)` now computes `profit_risk = sqrt(x' Sigma x)`;
the app pipeline, the preset cache and scripts 30/31 pass Sigma (the app always, not only in risk-aware mode).
Without Sigma it falls back to the independent-crops figure. The independent figure understated risk about
5x because it ignored positive co-movement (cache presets, `conservative` Sigma):

| preset | B1 risk before -> after | OURS vs B1 (normal mode) before -> after | OURS vs B1 (risk-aware) before -> after |
|---|---|---|---|
| small rainfed | 7,007 -> 35,908 | +105.7% -> +16.5% | -32.6% -> +10.1% |
| medium mixed | 17,516 -> 89,770 | +88.7% -> +13.4% | -23.3% -> +6.5% |
| large irrigated | 52,549 -> 269,310 | +58.3% -> +1.2% | -41.4% -> +20.4% |
| drought year | 35,033 -> 179,540 | +102.2% -> +12.8% | -16.8% -> +10.7% |
| Marathwada dry | 17,516 -> 89,770 | +140.5% -> +39.5% | -3.5% -> +19.3% |

Two claims weaken: (1) the headline "profit risk +100% vs current mix" in normal mode was an artefact and is
+1% to +40%; (2) the risk-aware plan no longer shows a rupee-risk *reduction* vs the current mix in any preset
(+6% to +20%). Per rupee of profit it is still lower than B1 (0.98) in 4 of 5 presets (0.77-0.97); the drought
preset is slightly higher (1.04). Risk-aware is not uniformly less risky than the normal plan either: large
irrigated 0.77 vs 0.60 per rupee, medium 0.83 vs 0.80 (the normal plan leaves rabi land idle to save water).

New tests: `tests/test_risk_measure.py` (toy: absolute risk halves when land is halved, per-profit risk does
not; empty/losing plans get the cap; `evaluate` with Sigma counts correlation) and a real-data test that a
risk-heavy Model B crops >= 90% of Model A's area with no higher risk per rupee.

### Task 6 -- risk inputs follow the user's scenario (M4)

`risk.sigma_from_deviations(deviation_matrix, R, crops, std_overrides)` is now the single place
Sigma = dev_cov * outer(R, R) is built (`build_risk_inputs` and `sigma_with_overridden_std` call it; the cached
Sigma is unchanged to the last digit). The app computes it at request time with `app.data.risk_inputs_for_params`,
taking R = yield x price from the *active* params_df (price mode, per-crop price multipliers and the sugarcane FRP
override included) and the cached historical deviation matrix; `revenue_vector(params_df, crops)` feeds the Risk
tab. The cache build derives each preset's Sigma the same way. Previously the Risk tab and risk-aware solver paired
scenario profits with the *market-price* R from the cache.

Default inputs reproduce the cached Sigma exactly, so the five cached presets are unchanged (verified: every
preset B1/OURS profit and risk identical before/after). Effect on live what-if scenarios (10 ha, current water,
risk-aware, conservative Sigma):

| scenario | B1 risk, stale -> live Sigma | risk-aware plan: risk the old app showed -> true (live) risk | plan chosen with live Sigma: risk / profit |
|---|---|---|---|
| soybean price -30% | 179,540 -> 170,514 | 184,821 -> 184,818 | 211,541 / 238,801 |
| rice price +30% | 179,540 -> 180,970 | 185,465 -> 194,594 | 191,675 / 317,948 |
| MSP-floor price mode | 179,540 -> 219,738 (+22%) | 158,738 -> 201,916 (+27%) | 211,384 / 314,932 (old plan: 299,122) |

So in MSP-floor mode the old app understated the risk of both B1 and its recommendation by 22-27%, and a
price shock moved profit but not risk. New tests (`tests/test_risk_follows_scenario.py`): default inputs
reproduce the cache for both sugarcane modes; a rice +20% shock multiplies rice variance by 1.44 and its
covariances by 1.2 and leaves the other crops untouched; the FRP override rescales sugarcane risk; MSP mode gets
its own PSD Sigma; cached preset profit risk equals the request-time value.

### Task 7 -- backtest validity (H4)

**(a) Look-ahead removed.** The optimizer makes one joint kharif+rabi decision, but rabi prices were read in
*October* while kharif was planned in *May*. Every crop is now planned on 1 May of year t
(`info.PLAN_MONTH`); rabi prices are the naive carry-forward of the last price at or before May. I chose
one May planning date over a two-stage plan because the long-duration crops (cotton, tur, sugarcane) commit land in
both seasons and the NSGA solvers would need a staged formulation; the single date is the conservative reading
(a farmer who sees October prices before sowing wheat is better informed than this). `info_set="season"`
reproduces the old behaviour. A/B on identical code (`scripts/62_backtest_skill.py`, mean realized profit per
year over 2016-2019, Rs, 10 ha):

| scenario | strategy | May info (headline) | legacy Oct look-ahead | look-ahead flattered by |
|---|---|---|---|---|
| default | OURS | 230,769 | 232,036 | +1,267 |
| default | B2 | 288,084 | 288,084 | 0 |
| tight | OURS | 200,645 | 208,052 | +7,407 |
| tight | B2 | 259,036 | 259,036 | 0 |

The look-ahead did not matter for the profit-max LP (wheat/jowar never entered its plan) and flattered OURS by
0.5-3.7%. New tests: every price origin is <= 1 May of t; the legacy option still reads wheat in October.

**(b) The backtest can now measure forecast skill.** B2 and ORACLE disagree in 8/8 headline cells. Added
`ORACLE_PRICE` (realized prices, forecast yields) and `ORACLE_YIELD` (the reverse) and a no-sugarcane variant
(`reports/results/backtest_skill.md`):

| variant / water | B2 | ORACLE | B2 capture | gap closed by price foresight | by yield foresight |
|---|---|---|---|---|---|
| all crops / default | 288,084 | 339,253 | 85% | 35% | 68% |
| all crops / tight | 259,036 | 295,022 | 88% | 37% | 64% |
| no sugarcane / default | 284,212 | 317,630 | 89% | -1% | 52% |
| no sugarcane / tight | 252,365 | 290,120 | 87% | 18% | 87% |

Most of what perfect foresight would add comes from yields, not prices (the two overlap, so shares are not
additive). Dropping sugarcane barely moves B2's capture (85-89%), so sugarcane is not what hid the skill signal.
OURS is *not* the best realized-profit strategy: it trades profit for water and fertilizer (pseudo-weights 0.5 /
0.3 / 0.2). Headline (May info, all crops, mean realized profit per year): default B1 229,479, B2 288,084,
B3 220,337, OURS 230,769, MODEL_B 259,420; tight B1 229,479, B2 259,036, B3 228,429, OURS 200,645,
MODEL_B 197,695. These are after the Task 3-6 changes, so they differ from the Phase 1 table
(e.g. B1 162,225 -> 229,479, because B1 now uses all its land and the water budgets scale with it).

**(c) p-values dropped.** With n=4 the smallest attainable two-sided sign / Wilcoxon p is 0.125, so neither can
ever reject. `60_backtest.py` no longer computes them; it writes `backtest_deltas.csv` and a per-year delta
table (OURS and MODEL_B minus B1) in `backtest_summary.md`. The README no longer quotes sign p=0.625 /
Wilcoxon p=0.25.

**(d) All baselines.** `61_backtest_v2.py` adds `mean_realized_profit` for every strategy to the win summary and
writes `backtest_deltas_v2.csv` (OURS / MODEL_B minus B1, B1_SCALED, B2 and B3, per year and scenario) plus a
section 5 table in `backtest_summary_v2.md`. The README backtest row will list all of them. The app's Backtest tab
caption claimed "B2 and ORACLE are identical in every year/scenario" (false even before this change); it now
describes the real situation.

### Task 8 -- yield model honesty (M1)

The headline yield table pooled every Maharashtra crop in its native unit (t/ha, bales/ha, milled-rice
equivalent), so pooled MAE / R^2 mostly ranked crops by magnitude. New `scripts/95_yield_decision_crops.py`
(does not retrain; uses the saved models) reports only the 8 decision crops, in the optimizer's saleable qtl/ha,
against a new `BaselineRecentMean` (mean of the last 3 years of the same state/crop/season), plus last-year and
all-years baselines. Two designs, both on 2016-2019 (n=4 per crop): **one-step-ahead** (RF refit each year on
<= t-1, as the optimizer uses it; primary) and fixed origin (the <= 2015 model, up to 4 years ahead).

| crop | RF MAPE % | last-3-yr mean MAPE % | RF vs last-3-yr (MAE) | one-step-ahead |
|---|---|---|---|---|
| rice | 14.8 | 17.3 | +15% | RF wins |
| wheat | 8.6 | 11.3 | +26% | RF wins |
| soybean | 9.1 | 18.6 | +51% | RF wins |
| jowar | 26.9 | 21.3 | -20% | **RF loses** |
| cotton | 28.0 | 25.8 | -7% | **RF loses** |
| tur | 33.7 | 30.9 | -7% | **RF loses** |
| maize | 31.4 | 30.9 | -6% | **RF loses** |
| sugarcane | 3.0 | 1.5 | -96% | **RF loses** |

RF beats the last-3-year mean on 3/8 crops and loses on 5/8; against the *best* of the three naive baselines it
loses on 7/8 (all but wheat; the all-years mean often wins). Mean MAPE 19.4% (RF) vs 19.7% (last-3-yr). Fixed
origin: RF loses to the last-3-year mean on 4/8 (rice, jowar, sugarcane, maize), mean MAPE 19.1% vs 22.9%.

Claim that gets weaker: "RandomForest wins" (RESULTS_INDEX E1.1) rested on the pooled Maharashtra MAE
(0.506 vs 0.667 for Baseline-Mean) and R^2 = 0.938. Both are dropped from the README/index/app/`yield_results.md`
(the pooled R^2 columns stay in `yield_results.csv` as an audit trail; `10_train_yield.py` now omits them from its
markdown). The Wilcoxon "RF beats XGBoost" row is annotated: its 152 paired errors pool crops in native units.
Combined with Task 7 (perfect yield foresight would close ~2/3 of the gap to the perfect-foresight plan), the
yield forecast is the weak, high-value link. This is a finding to act on (e.g. shrink the RF toward a recent mean
for the crops where it loses), not something I changed in the optimizer. The app's Evidence tab now shows this
decision-crop table instead of the pooled MAE/R^2 line. Tests: baseline unit test, committed-table consistency
(flags match MAEs), no `_R2` in the committed markdown.

### Task 9 -- price model significance (M5)

`90_price_significance.py` stacked the 7 crops into one series (n = 252-315) and ran a plain DM test, treating
crops' errors as independent. They are not: prices move together within a month, and overlapping h-step forecasts
are serially dependent. New `stats.dm_test.panel_diebold_mariano` averages the loss differential across crops per
origin month (each month is a cluster, so n = 36-45 months) and runs the HLN-corrected DM with h-1 HAC lags on that
series; `block_bootstrap_pvalue` resamples months in overlapping blocks (block = max(h, 6)) as a check that does not
rely on the HAC estimator. `dm_from_loss_diff` is the shared core (`diebold_mariano` unchanged in behaviour).

| comparison | stacked (before) p | panel p | block-bootstrap p |
|---|---|---|---|
| Naive vs XGBoost h=3 | 0.057 | 0.076 | 0.065 |
| Naive vs XGBoost h=6 | **0.031** | 0.081 | 0.038 |
| Naive vs XGBoost h=12 | **0.020** | 0.071 | 0.109 |
| Naive vs Seasonal-Naive h=3 | <0.001 | <0.001 | 0.0004 |
| Naive vs Seasonal-Naive h=6 | 0.001 | 0.002 | 0.005 |
| Naive vs Seasonal-Naive h=12 | 1.0 (identical forecasts) | 1.0 | 1.0 |

Claim that got weaker: "Naive significantly beats XGBoost at h=6 and h=12" no longer holds under the panel test
(only the h=6 bootstrap rejects, borderline). Running the unchanged stacked test on today's library versions gives
0.035 (h=6) and 0.030 (h=12), not the committed 0.031 / 0.020: the XGBoost rolling backtest is not bit-stable across
environments (scikit-learn/xgboost versions), which is one more reason not to lean on 0.03-vs-0.05. Tests
(`tests/test_panel_dm.py`, data-free): one-crop panel equals the plain DM; with a shared monthly shock and no true
difference over 60 simulated no-effect panels (40 months x 7 crops) the stacked test rejects at p<0.05 in 45% of them, the panel test in 8% (nominal 5%); a real
effect is still detected; missing crops are averaged over; identical forecasts return p = 1 (the bootstrap
initially returned a spurious 0.0002 there -- fixed).

### Task 10 -- water model (M2)

Three changes in `agriopt.data.rainfall` (+ `scripts/71_water_region.py`, `docs/water.md` section 9):

1. **Net irrigation = sum of monthly deficits.** Was `max(0, need - sum of the season's monthly effective
   rain)`, which let a July surplus pay for a September deficit. Now `sum_m max(0, need_m - Peff_m)` over the
   season-window months; the FAO TM3 seasonal need is spread *uniformly* over the window (stated assumption --
   there is no monthly crop-coefficient profile in the repo and none was invented). Rice puddling water is still
   added for rice only. "Normal" is the mean over the 30 observed years of each year's monthly balance, not the
   balance of the mean year: the deficit is convex in rainfall, and balancing the smooth mean year understated
   irrigation need (in a first draft it made a real dry year need *less* water than normal for rice).
2. **"Dry" is a real year.** Was the 20th percentile of each month independently (a composite where every month
   is unusually dry at once). Now `dry_year(region)`: the observed year whose usable rain (summed over the 8
   crops' season windows, min(monthly need, Peff)) is nearest the 20th percentile; `monthly_dry_year` returns that
   year's own months. (The June-September total is a poor selector under a monthly balance -- see docs/water.md
   9.3.) Chosen years: maharashtra 2003, konkan 2002, madhya_maharashtra 2000, marathwada 1986, vidarbha 2014.
3. **Regions compared at equal water budgets.** `region_equal_budget.csv` and a new section of
   `region_comparison.md` give every region the same absolute m3 (0.7x / 1.0x of the state-wide normal-year B1
   footprint), normal and dry.

State-wide net irrigation, mm (before -> after): normal -- rice 200 -> 266, wheat 514 -> 516, soybean 0 -> 66,
cotton 324 -> 433, sugarcane 1,293 -> 1,318, tur 0 -> 136, maize 0 -> 91; dry -- rice 212 -> 289, soybean 12 -> 89,
cotton 435 -> 480, tur 0 -> 163, maize 87 -> 119, sugarcane 1,427 -> 1,372. The monthly balance raises the water
cost of the monsoon crops the old form called free ("0 mm" for soybean, tur and maize was an artefact of
averaging a wet July over the season). The old composite dry year overstated the thirst of most crops in
Marathwada: rice 422 -> 367, cotton 646 -> 561, sugarcane 1,641 -> 1,541 (tur 46 -> 162 goes the other way).

Effect on the five cached presets (the app default basis is net irrigation; budgets are multiples of B1's water):

| preset | water budget m3 | OURS profit | OURS vs B1 |
|---|---|---|---|
| small rainfed | 6,414 -> 7,634 | 39,335 -> 39,271 | +8% -> +7% |
| medium mixed | 22,906 -> 27,266 | 127,043 -> 122,910 | +39% -> +34% |
| large irrigated | 89,332 -> 106,337 | 457,123 -> 469,955 | +67% -> +71% |
| drought year | 27,487 -> 32,719 | 178,063 -> 174,312 | -3% -> -5% |
| Marathwada dry year | 36,105 -> 32,654 | 133,821 -> 122,855 | +46% -> +34% |

**A conclusion flips.** Under per-region budgets (each region's budget from its *own* B1 footprint), Marathwada
looked 26% better than Konkan (OURS Rs 210,216 vs 166,956 in Phase 1) -- partly because the rainier region was
handed a smaller budget. At the same absolute budget (normal rainfall, 1.0x = 54,532 m3) OURS earns
Konkan Rs 273,010 > Maharashtra 258,265 > Madhya 244,796 > Vidarbha 239,686 > Marathwada 224,101, i.e. Konkan is
22% ahead of Marathwada; at the tight budget Marathwada and Vidarbha fall to -1.5% / -1.8% vs the current mix, and
in a dry year at the tight budget Marathwada to -11.2%. (The own-budget table, regenerated under the new water model, now has
Marathwada at 248,237 vs Konkan 253,235.) Tests: `tests/test_water_monthly.py` (synthetic cases showing a surplus
month does not cover a later deficit, normal = mean of yearly balances, rain used <= monthly need; dry year is an
observed year near the 20th percentile; dry needs more irrigation than normal in total in every region);
`test_water_region.py` expectations that encoded the old model (dry >= normal per crop; rice == puddling water at
normal) are updated, with the reason in each docstring: rabi crops can need slightly less in a year with good
winter rain (Marathwada wheat 508 vs state-wide normal 516).
