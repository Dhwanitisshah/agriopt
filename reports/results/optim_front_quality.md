# NSGA-II vs exact LP front quality (E3.2)

| water_scenario | price_mode | hv_lp_reference | hv_nsga2_mean | hv_nsga2_std | igd_nsga2_mean | igd_nsga2_std | runtime_mean_s | runtime_std_s | lp_front_size | nsga_front_size_mean |
|---|---|---|---|---|---|---|---|---|---|---|
| tight | market | 0.448 | 0.610 | 0.006 | 0.123 | 0.056 | 1.522 | 0.076 | 50 | 100.000 |
| tight | msp_floor | 0.559 | 0.568 | 0.001 | 0.008 | 0.001 | 1.530 | 0.067 | 50 | 100.000 |
| current | market | 0.465 | 0.599 | 0.004 | 0.111 | 0.065 | 1.228 | 0.201 | 50 | 100.000 |
| current | msp_floor | 0.552 | 0.558 | 0.001 | 0.008 | 0.001 | 1.449 | 0.264 | 50 | 100.000 |
| relaxed | market | 0.481 | 0.586 | 0.005 | 0.115 | 0.045 | 1.565 | 0.123 | 50 | 100.000 |
| relaxed | msp_floor | 0.555 | 0.559 | 0.001 | 0.007 | 0.001 | 1.454 | 0.050 | 50 | 100.000 |
