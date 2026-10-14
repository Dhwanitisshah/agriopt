# NSGA-II / NSGA-III seed robustness (Phase 9 / E3.4)

10 seeds (0-9), default scenario (water_budget_m3=72155.8 m3 -- B1's 'current' water usage at price_mode='market', matching scripts/30_run_optimizer.py's canonical default; land_ha=10.0). params_df is built ONCE and reused across every seed within an algorithm, so all seed-to-seed variation below is NSGA's own stochastic-search variation (Phase 8 already fixed the RF-nondeterminism bug that used to contaminate this).

## Hypervolume (normalized, joint ref_point=[1.1]*n_obj)

| algorithm | HV mean | HV std | 95% CI (normal approx, n=10) |
|---|---|---|---|
| NSGA-II | 0.5989 | 0.0051 | [0.5952, 0.6025] |
| NSGA-III | 0.5809 | 0.0034 | [0.5785, 0.5833] |

**Small-n caveat**: n=10 seed-runs is a small sample for a CI (same spirit as the Phase 7 backtest's n=4/5-year caveat) -- the normal-approximation CI here is a rough guide to seed sensitivity, not a precise interval.

## Recommended allocation: per-crop std of hectares across the 10 seeds

| crop | NSGA-II alloc std (ha) | NSGA-III alloc std (ha) |
|---|---|---|
| rice | 0.585 | 1.027 |
| wheat | 0.763 | 0.665 |
| jowar | 0.005 | 0.017 |
| soybean | 0.034 | 0.014 |
| cotton | 0.025 | 0.005 |
| sugarcane | 0.099 | 0.166 |
| tur | 0.797 | 0.897 |
| maize | 0.086 | 0.125 |

- Most seed-sensitive crop in the final recommendation: **tur** (NSGA-II), **rice** (NSGA-III) -- i.e. which crop's recommended hectares swing most just from changing the optimizer's random seed, holding the scenario and params fixed.
- Mean per-crop allocation std: NSGA-II=0.299 ha, NSGA-III=0.365 ha (out of land_ha=10.0) -- a small share of total land, worth disclosing to a user who reruns the optimizer and gets a slightly different plan each time.
