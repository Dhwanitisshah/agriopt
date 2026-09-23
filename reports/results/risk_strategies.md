# Risk evaluation of B1/B2/B3/OURS (Model A) / Model B (Phase 5, Item 5)

Scenario: water=current, price=market (land=10.0 ha).
Model B pseudo-weights (profit, water, fert, risk) = (0.4, 0.2, 0.1, 0.3).

| strategy | profit | water_m3 | fert_kg | n_crops | portfolio_risk_rs | bootstrap_mean | bootstrap_P5 | bootstrap_P_loss | bootstrap_CVaR5 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 166258.97 | 74274.19 | 971.33 | 8 | 122519.43 | 183700.11 | 4649.34 | 0.00 | 4649.34 | True |
| B2 | 443722.32 | 74274.19 | 1008.35 | 2 | 86304.32 | 436044.09 | 271736.09 | 0.00 | 271736.09 | True |
| B3 | 166258.97 | 31586.17 | 566.32 | 2 | 36847.48 | 165370.65 | 104016.54 | 0.00 | 104016.54 | True |
| OURS_A | 291925.22 | 52242.14 | 704.83 | 5 | 63909.99 | 288048.94 | 198468.80 | 0.00 | 198468.80 | True |
| ModelB | 296564.75 | 52936.01 | 813.14 | 4 | 61218.33 | 293496.14 | 183813.96 | 0.00 | 183813.96 | True |
