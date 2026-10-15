# NSGA-II / NSGA-III seed robustness (Phase 9 / E3.4)

10 seeds (0-9), default scenario (water_budget_m3=104850.6 m3 -- B1's 'current' water usage at price_mode='market', matching scripts/30_run_optimizer.py's canonical default; land_ha=10.0). params_df is built ONCE and reused across every seed within an algorithm, so all seed-to-seed variation below is NSGA's own stochastic-search variation (Phase 8 already fixed the RF-nondeterminism bug that used to contaminate this).

## Hypervolume (normalized, joint ref_point=[1.1]*n_obj)

| algorithm | HV mean | HV std | 95% CI (normal approx, n=10) |
|---|---|---|---|
| NSGA-II | 0.5856 | 0.0069 | [0.5807, 0.5906] |
| NSGA-III | 0.5717 | 0.0083 | [0.5658, 0.5777] |

**Small-n caveat**: n=10 seed-runs is a small sample for a CI (same spirit as the Phase 7 backtest's n=4/5-year caveat) -- the normal-approximation CI here is a rough guide to seed sensitivity, not a precise interval.

## Recommended allocation: per-crop std of hectares across the 10 seeds

| crop | NSGA-II alloc std (ha) | NSGA-III alloc std (ha) |
|---|---|---|
| rice | 0.000 | 1.597 |
| wheat | 1.011 | 0.917 |
| jowar | 0.000 | 0.010 |
| soybean | 0.000 | 0.055 |
| cotton | 0.000 | 0.004 |
| sugarcane | 0.415 | 1.256 |
| tur | 0.000 | 1.770 |
| maize | 0.000 | 0.004 |

- Most seed-sensitive crop in the final recommendation: **wheat** (NSGA-II), **tur** (NSGA-III) -- i.e. which crop's recommended hectares swing most just from changing the optimizer's random seed, holding the scenario and params fixed.
- Mean per-crop allocation std: NSGA-II=0.178 ha, NSGA-III=0.702 ha (out of land_ha=10.0) -- a small share of total land, worth disclosing to a user who reruns the optimizer and gets a slightly different plan each time.
