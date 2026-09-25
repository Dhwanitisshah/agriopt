# NSGA-II / NSGA-III seed robustness (Phase 9 / E3.4)

10 seeds (0-9), default scenario (water_budget_m3=74274.2 m3 -- B1's 'current' water usage at price_mode='market', matching scripts/30_run_optimizer.py's canonical default; land_ha=10.0). params_df is built ONCE and reused across every seed within an algorithm, so all seed-to-seed variation below is NSGA's own stochastic-search variation (Phase 8 already fixed the RF-nondeterminism bug that used to contaminate this).

## Hypervolume (normalized, joint ref_point=[1.1]*n_obj)

| algorithm | HV mean | HV std | 95% CI (normal approx, n=10) |
|---|---|---|---|
| NSGA-II | 0.5935 | 0.0047 | [0.5901, 0.5968] |
| NSGA-III | 0.5691 | 0.0055 | [0.5651, 0.5730] |

**Small-n caveat**: n=10 seed-runs is a small sample for a CI (same spirit as the Phase 7 backtest's n=4/5-year caveat) -- the normal-approximation CI here is a rough guide to seed sensitivity, not a precise interval.

## Recommended allocation: per-crop std of hectares across the 10 seeds

| crop | NSGA-II alloc std (ha) | NSGA-III alloc std (ha) |
|---|---|---|
| rice | 0.767 | 0.775 |
| wheat | 0.572 | 0.975 |
| jowar | 0.012 | 0.011 |
| soybean | 0.016 | 0.002 |
| cotton | 0.005 | 0.008 |
| sugarcane | 0.166 | 0.170 |
| tur | 0.782 | 0.834 |
| maize | 0.019 | 0.008 |

- Most seed-sensitive crop in the final recommendation: **tur** (NSGA-II), **wheat** (NSGA-III) -- i.e. which crop's recommended hectares swing most just from changing the optimizer's random seed, holding the scenario and params fixed.
- Mean per-crop allocation std: NSGA-II=0.293 ha, NSGA-III=0.348 ha (out of land_ha=10.0) -- a small share of total land, worth disclosing to a user who reruns the optimizer and gets a slightly different plan each time.
