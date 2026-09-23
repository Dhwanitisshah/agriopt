# Risk evaluation of B1/B2/B3/OURS (Model A) / Model B (Phase 5.1, Item 5)

Scenario: water=current, price=market (land=10.0 ha).
Model B pseudo-weights (profit, water, fert, risk) = (0.4, 0.2, 0.1, 0.3).

`scenario_*` columns come from `historical_scenarios()` -- profit re-evaluated under each of the ~18-19 actual historical years' deviations (no resampling), since the discrete historical record is small enough that a smooth bootstrap would manufacture outcomes never actually observed. `scenario_mean` should equal `profit` (deterministic point estimate) very closely -- deviations are mean-centered per allocation (see agriopt.optim.risk).

| strategy | profit | water_m3 | fert_kg | n_crops | portfolio_risk_rs | scenario_n_years | scenario_mean | scenario_worst_year_profit | scenario_worst_year | scenario_P10 | scenario_n_loss_years | feasible |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 166258.97 | 74274.19 | 971.33 | 8 | 122519.43 | 18 | 166258.97 | -10888.30 | 2015 | 40739.87 | 1 | True |
| B2 | 443722.32 | 74274.19 | 1008.35 | 2 | 86304.32 | 19 | 443722.32 | 277647.10 | 2003 | 343321.38 | 0 | True |
| B3 | 166258.97 | 31586.17 | 566.32 | 2 | 36847.48 | 19 | 166258.97 | 104240.37 | 2003 | 113522.24 | 0 | True |
| OURS_A | 291925.22 | 52242.14 | 704.83 | 5 | 63909.99 | 18 | 291925.22 | 201782.41 | 2003 | 222478.62 | 0 | True |
| ModelB | 296564.75 | 52936.01 | 813.14 | 4 | 61218.33 | 18 | 296564.75 | 186739.47 | 2003 | 217110.66 | 0 | True |

## Sensitivity: sugarcane risk

Model B's recommendation depends on Sigma, which gives sugarcane an unusually low std (0.095) purely because its price is a constant FRP, not a mandi series -- not necessarily because it is genuinely less risky. This reruns Model B with sugarcane's relative-deviation std replaced by the median of the other 7 crops' std (0.273), correlations unchanged, to test how much that assumption drives the recommendation.

| | before (measured std) | after (median-of-others std) |
|---|---|---|
| sugarcane hectares | 1.68 | 0.44 |
| total portfolio risk (Rs) | 61,218 | 87,146 |
| profit (Rs) | 296,565 | 272,971 |

**Not robust**: sugarcane hectares shift by 73.7% once its std is raised to a typical crop's level -- part of Model B's original preference for sugarcane was an artifact of its constant-FRP price understating its true risk, not a genuine profit/water/fert advantage.
