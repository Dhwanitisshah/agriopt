# NSGA-II vs LP reference front quality: v1 (lexicographic slice) vs v2 (grid) (Phase 5, Item 3)

v1 (`exact_front_lp`, Phase 3) sweeps ONE lexicographic profit>water>fert curve through the true 3-objective Pareto surface -- exact where defined, but a 1-D curve, not the surface. v2 (`exact_front_lp_grid`, this experiment) sweeps a profit x fertilizer-cap grid, minimizing water at each combo, then keeps only the non-dominated points -- a much denser approximation of the actual 2-D Pareto surface. Both are still LP relaxations restricted to the points the sweep visits, not the literal continuous Pareto surface, but v2 covers far more of it.

## v2 (grid reference) quality

| water_scenario | price_mode | hv_lp_grid_reference_v2 | hv_nsga2_mean | hv_nsga2_std | igd_nsga2_mean_v2 | igd_nsga2_std_v2 | grid_front_size |
|---|---|---|---|---|---|---|---|
| tight | market | 0.646 | 0.599 | 0.006 | 0.044 | 0.004 | 300 |
| tight | msp_floor | 0.678 | 0.643 | 0.004 | 0.030 | 0.003 | 300 |
| current | market | 0.630 | 0.588 | 0.004 | 0.049 | 0.002 | 289 |
| current | msp_floor | 0.687 | 0.661 | 0.006 | 0.036 | 0.004 | 289 |
| relaxed | market | 0.607 | 0.571 | 0.005 | 0.037 | 0.002 | 289 |
| relaxed | msp_floor | 0.677 | 0.657 | 0.004 | 0.032 | 0.001 | 289 |

## v1 vs v2: NSGA-II hypervolume as a fraction of the reference front's

| water | price | HV(NSGA-II)/HV(v1 slice) | HV(NSGA-II)/HV(v2 grid) |
|---|---|---|---|
| tight | market | 1.094 | 0.927 |
| tight | msp_floor | 1.015 | 0.948 |
| current | market | 1.131 | 0.933 |
| current | msp_floor | 1.040 | 0.963 |
| relaxed | market | 1.119 | 0.939 |
| relaxed | msp_floor | 1.025 | 0.971 |

- **v2 resolves the v1 anomaly**: NSGA-II's hypervolume was ABOVE the v1 slice's in every scenario (mean ratio 1.07x, Phase 3 finding) simply because v1 only traces a curve, not the surface -- against the denser v2 grid, NSGA-II's hypervolume ratio is 0.947x (<=1 within tolerance in every scenario), the expected relationship for an approximate front vs a denser LP-exact reference.
