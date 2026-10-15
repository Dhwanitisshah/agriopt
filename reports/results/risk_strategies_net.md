# Risk evaluation of B1/B2/B3/OURS (Model A) / Model B, NET IRRIGATION water basis (Phase 8)

Scenario: water=current, price=market (land=10.0 ha), water_basis=net_irrigation.
Model B pseudo-weights (profit, water, fert, risk) = (0.4, 0.2, 0.1, 0.3).

Mirrors reports/results/risk_strategies.md's structure exactly, under the net-irrigation water basis -- see docs/water.md.

| strategy | profit | water_m3 | fert_kg | n_crops | portfolio_risk_rs | scenario_n_years | scenario_mean | scenario_worst_year_profit | scenario_worst_year | scenario_P10 | scenario_n_loss_years | feasible |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 182833.11 | 54531.58 | 1375.94 | 8 | 166631.90 | 18 | 182833.11 | -56583.55 | 2015 | 13065.16 | 1 | True |
| B2 | 364071.21 | 54531.58 | 1261.42 | 3 | 109710.47 | 19 | 364071.21 | 216739.13 | 2002 | 239228.08 | 0 | True |
| B3 | 182833.11 | 21519.98 | 796.03 | 3 | 196668.48 | 19 | 182833.11 | 5423.79 | 2002 | 30812.73 | 0 | True |
| OURS_A | 258265.00 | 36518.54 | 938.42 | 3 | 175347.51 | 19 | 258265.00 | 90932.20 | 2002 | 102410.88 | 0 | True |
| ModelB | 233908.91 | 33351.14 | 1077.45 | 4 | 174861.63 | 18 | 233908.91 | 86679.78 | 2002 | 122091.59 | 0 | True |
