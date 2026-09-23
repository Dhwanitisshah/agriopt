# NSGA-II vs LP reference front quality: v1 (lexicographic slice) vs v2 (grid) (Phase 5, Item 3)

v1 (`exact_front_lp`, Phase 3) sweeps ONE lexicographic profit>water>fert curve through the true 3-objective Pareto surface -- exact where defined, but a 1-D curve, not the surface. v2 (`exact_front_lp_grid`, this experiment) sweeps a profit x fertilizer-cap grid, minimizing water at each combo, then keeps only the non-dominated points -- a much denser approximation of the actual 2-D Pareto surface. Both are still LP relaxations restricted to the points the sweep visits, not the literal continuous Pareto surface, but v2 covers far more of it.

## v2 (grid reference) quality

| water_scenario | price_mode | hv_lp_grid_reference_v2 | hv_nsga2_mean | hv_nsga2_std | igd_nsga2_mean_v2 | igd_nsga2_std_v2 | grid_front_size |
|---|---|---|---|---|---|---|---|
| tight | market | 0.625 | 0.610 | 0.006 | 0.101 | 0.042 | 300 |
| tight | msp_floor | 0.556 | 0.568 | 0.001 | 0.009 | 0.001 | 289 |
| current | market | 0.600 | 0.599 | 0.004 | 0.094 | 0.051 | 289 |
| current | msp_floor | 0.547 | 0.558 | 0.001 | 0.009 | 0.001 | 289 |
| relaxed | market | 0.588 | 0.586 | 0.005 | 0.100 | 0.037 | 300 |
| relaxed | msp_floor | 0.548 | 0.559 | 0.001 | 0.008 | 0.001 | 289 |

## v1 vs v2: NSGA-II hypervolume as a fraction of the reference front's

| water | price | HV(NSGA-II)/HV(v1 slice) | HV(NSGA-II)/HV(v2 grid) |
|---|---|---|---|
| tight | market | 1.360 | 0.976 |
| tight | msp_floor | 1.015 | 1.020 |
| current | market | 1.289 | 0.998 |
| current | msp_floor | 1.010 | 1.020 |
| relaxed | market | 1.219 | 0.996 |
| relaxed | msp_floor | 1.007 | 1.021 |

- v2's reference front still doesn't fully dominate NSGA-II's in every scenario (mean ratio 1.005x) -- the grid is denser than v1 but still a finite sweep, not the continuous surface, so a residual gap can remain.
