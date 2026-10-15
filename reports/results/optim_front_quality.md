# NSGA-II vs exact LP front quality (E3.2)

| water_scenario | price_mode | hv_lp_reference | hv_nsga2_mean | hv_nsga2_std | igd_nsga2_mean | igd_nsga2_std | runtime_mean_s | runtime_std_s | lp_front_size | nsga_front_size_mean |
|---|---|---|---|---|---|---|---|---|---|---|
| tight | market | 0.547 | 0.599 | 0.006 | 0.038 | 0.005 | 1.077 | 0.032 | 50 | 100.000 |
| tight | msp_floor | 0.633 | 0.643 | 0.004 | 0.015 | 0.001 | 1.138 | 0.036 | 50 | 100.000 |
| current | market | 0.520 | 0.588 | 0.004 | 0.051 | 0.006 | 1.225 | 0.033 | 50 | 100.000 |
| current | msp_floor | 0.636 | 0.661 | 0.006 | 0.038 | 0.007 | 1.217 | 0.018 | 50 | 100.000 |
| relaxed | market | 0.510 | 0.571 | 0.005 | 0.039 | 0.004 | 1.218 | 0.019 | 50 | 100.000 |
| relaxed | msp_floor | 0.641 | 0.657 | 0.004 | 0.033 | 0.004 | 1.248 | 0.040 | 50 | 100.000 |
