# Risk evaluation of B1/B2/B3/OURS (Model A) / Model B, NET IRRIGATION water basis (Phase 8)

Scenario: water=current, price=market (land=10.0 ha), water_basis=net_irrigation.
Model B pseudo-weights (profit, water, fert, risk) = (0.4, 0.2, 0.1, 0.3).

Mirrors reports/results/risk_strategies.md's structure exactly, under the net-irrigation water basis -- see docs/water.md.

| strategy | profit | water_m3 | fert_kg | n_crops | portfolio_risk_rs | scenario_n_years | scenario_mean | scenario_worst_year_profit | scenario_worst_year | scenario_P10 | scenario_n_loss_years | feasible |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 129794.13 | 27707.31 | 949.40 | 8 | 119601.60 | 18 | 129794.13 | -41281.76 | 2015 | 3874.62 | 1 | False |
| B2 | 261577.68 | 27707.31 | 998.23 | 3 | 151616.19 | 19 | 261577.68 | 97236.35 | 2002 | 130236.76 | 0 | True |
| B3 | 129794.13 | 5101.26 | 632.23 | 3 | 200830.62 | 19 | 129794.13 | -41414.33 | 2004 | -24910.62 | 6 | True |
| OURS_A | 194044.25 | 16286.79 | 794.28 | 4 | 169621.94 | 18 | 194044.25 | 64955.78 | 2002 | 89277.39 | 0 | True |
| ModelB | 182411.32 | 17100.61 | 1065.65 | 6 | 94070.55 | 18 | 182411.32 | 81065.45 | 2019 | 95026.63 | 0 | True |
