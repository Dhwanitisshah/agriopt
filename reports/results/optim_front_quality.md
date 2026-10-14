# NSGA-II vs exact LP front quality (E3.2)

| water_scenario | price_mode | hv_lp_reference | hv_nsga2_mean | hv_nsga2_std | igd_nsga2_mean | igd_nsga2_std | runtime_mean_s | runtime_std_s | lp_front_size | nsga_front_size_mean |
|---|---|---|---|---|---|---|---|---|---|---|
| tight | market | 0.577 | 0.598 | 0.002 | 0.039 | 0.004 | 2.746 | 0.277 | 50 | 100.000 |
| tight | msp_floor | 0.662 | 0.667 | 0.002 | 0.016 | 0.002 | 2.565 | 0.198 | 50 | 100.000 |
| current | market | 0.549 | 0.596 | 0.005 | 0.047 | 0.008 | 2.549 | 0.261 | 50 | 100.000 |
| current | msp_floor | 0.633 | 0.642 | 0.006 | 0.020 | 0.005 | 2.666 | 0.116 | 50 | 100.000 |
| relaxed | market | 0.526 | 0.593 | 0.005 | 0.044 | 0.012 | 2.660 | 0.163 | 50 | 100.000 |
| relaxed | msp_floor | 0.612 | 0.647 | 0.004 | 0.033 | 0.010 | 2.506 | 0.147 | 50 | 100.000 |
