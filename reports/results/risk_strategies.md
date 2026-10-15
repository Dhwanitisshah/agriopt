# Risk evaluation of B1/B2/B3/OURS (Model A) / Model B (Phase 5.1, Item 5)

Scenario: water=current, price=market (land=10.0 ha).
Model B pseudo-weights (profit, water, fert, risk) = (0.4, 0.2, 0.1, 0.3).

`scenario_*` columns come from `historical_scenarios()` -- profit re-evaluated under each of the ~18-19 actual historical years' deviations (no resampling), since the discrete historical record is small enough that a smooth bootstrap would manufacture outcomes never actually observed. `scenario_mean` should equal `profit` (deterministic point estimate) very closely -- deviations are mean-centered per allocation (see agriopt.optim.risk).

| strategy | profit | water_m3 | fert_kg | n_crops | portfolio_risk_rs | risk_per_profit | scenario_n_years | scenario_mean | scenario_worst_year_profit | scenario_worst_year | scenario_P10 | scenario_n_loss_years | feasible |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 182833.11 | 104850.60 | 1375.94 | 8 | 166631.90 | 0.91 | 18 | 182833.11 | -56583.55 | 2015 | 13065.16 | 1 | True |
| B2 | 421029.37 | 104850.60 | 1782.26 | 3 | 105044.38 | 0.25 | 19 | 421029.37 | 270856.93 | 2002 | 285649.90 | 0 | True |
| B3 | 182833.11 | 43553.98 | 963.45 | 2 | 59254.46 | 0.32 | 19 | 182833.11 | 69217.75 | 2019 | 103479.40 | 0 | True |
| OURS_A | 277183.19 | 67367.54 | 1365.70 | 3 | 77156.77 | 0.28 | 19 | 277183.19 | 155738.04 | 2002 | 166460.88 | 0 | True |
| ModelB | 324419.52 | 81681.22 | 1341.16 | 4 | 82536.39 | 0.25 | 18 | 324419.52 | 213472.11 | 2002 | 217557.40 | 0 | True |

## Sensitivity: sugarcane risk

Model B's recommendation depends on Sigma, which gives sugarcane an unusually low std (0.095) purely because its price is a constant FRP, not a mandi series -- not necessarily because it is genuinely less risky. This reruns Model B with sugarcane's relative-deviation std replaced by the median of the other 7 crops' std (0.273), correlations unchanged, to test how much that assumption drives the recommendation.

| | before (measured std) | after (median-of-others std) |
|---|---|---|
| sugarcane hectares | 2.53 | 2.30 |
| total portfolio risk (Rs) | 82,536 | 139,485 |
| profit (Rs) | 324,420 | 319,932 |

**Robust**: sugarcane hectares shift by only 9.1% when its std is raised to a typical crop's level -- the recommendation was not leaning on sugarcane's artificially low measured risk.
