# Risk evaluation of B1/B2/B3/OURS (Model A) / Model B, NET IRRIGATION water basis (Phase 8)

Scenario: water=current, price=market (land=10.0 ha), water_basis=net_irrigation.
Model B pseudo-weights (profit, water, fert, risk) = (0.4, 0.2, 0.1, 0.3).

Mirrors reports/results/risk_strategies.md's structure exactly, under the net-irrigation water basis -- see docs/water.md.

| strategy | profit | water_m3 | fert_kg | n_crops | portfolio_risk_rs | scenario_n_years | scenario_mean | scenario_worst_year_profit | scenario_worst_year | scenario_P10 | scenario_n_loss_years | feasible |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 166258.97 | 25980.01 | 971.33 | 8 | 122519.43 | 18 | 166258.97 | -10888.30 | 2015 | 40739.87 | 1 | True |
| B2 | 423747.48 | 25980.01 | 1132.57 | 3 | 151995.36 | 19 | 423747.48 | 248170.08 | 2002 | 266485.78 | 0 | True |
| B3 | 166258.97 | 0.00 | 746.21 | 2 | 172228.90 | 19 | 166258.97 | 4437.50 | 2002 | 30665.78 | 0 | True |
| OURS_A | 305165.82 | 15121.56 | 943.01 | 3 | 142479.21 | 18 | 305165.82 | 169394.16 | 2002 | 196420.30 | 0 | True |
| ModelB | 288650.47 | 16181.48 | 1068.78 | 6 | 84062.21 | 18 | 288650.47 | 191062.24 | 2002 | 195425.09 | 0 | True |
