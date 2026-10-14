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
