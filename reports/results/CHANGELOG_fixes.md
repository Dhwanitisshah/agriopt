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
