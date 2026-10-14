# Risk evaluation of B1/B2/B3/OURS (Model A) / Model B (Phase 5.1, Item 5)

Scenario: water=current, price=market (land=10.0 ha).
Model B pseudo-weights (profit, water, fert, risk) = (0.4, 0.2, 0.1, 0.3).

`scenario_*` columns come from `historical_scenarios()` -- profit re-evaluated under each of the ~18-19 actual historical years' deviations (no resampling), since the discrete historical record is small enough that a smooth bootstrap would manufacture outcomes never actually observed. `scenario_mean` should equal `profit` (deterministic point estimate) very closely -- deviations are mean-centered per allocation (see agriopt.optim.risk).

| strategy | profit | water_m3 | fert_kg | n_crops | portfolio_risk_rs | scenario_n_years | scenario_mean | scenario_worst_year_profit | scenario_worst_year | scenario_P10 | scenario_n_loss_years | feasible |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 129794.13 | 72155.83 | 949.40 | 8 | 119601.60 | 18 | 129794.13 | -41281.76 | 2015 | 3874.62 | 1 | False |
| B2 | 296092.58 | 72155.83 | 1443.70 | 3 | 81090.13 | 19 | 296092.58 | 169969.87 | 2002 | 179971.29 | 0 | True |
| B3 | 129794.13 | 31312.82 | 632.67 | 3 | 56200.09 | 19 | 129794.13 | 28582.37 | 2019 | 68708.15 | 0 | True |
| OURS_A | 203432.66 | 49779.85 | 953.22 | 4 | 61987.29 | 18 | 203432.66 | 103889.29 | 2019 | 124148.97 | 0 | True |
| ModelB | 202261.95 | 50161.53 | 1086.80 | 3 | 84267.79 | 18 | 202261.95 | 100004.51 | 2004 | 115978.91 | 0 | True |

## Sensitivity: sugarcane risk

Model B's recommendation depends on Sigma, which gives sugarcane an unusually low std (0.095) purely because its price is a constant FRP, not a mandi series -- not necessarily because it is genuinely less risky. This reruns Model B with sugarcane's relative-deviation std replaced by the median of the other 7 crops' std (0.273), correlations unchanged, to test how much that assumption drives the recommendation.

| | before (measured std) | after (median-of-others std) |
|---|---|---|
| sugarcane hectares | 0.00 | 0.15 |
| total portfolio risk (Rs) | 84,268 | 95,149 |
| profit (Rs) | 202,262 | 207,166 |

**Not robust**: sugarcane hectares shift by 4557.4% once its std is raised to a typical crop's level -- part of Model B's original preference for sugarcane was an artifact of its constant-FRP price understating its true risk, not a genuine profit/water/fert advantage.
