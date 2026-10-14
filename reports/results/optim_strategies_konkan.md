# Optimizer strategies (E3.1), NET IRRIGATION water basis, region=konkan (Phase 8.1)

Water budget derived from B1's own NET-irrigation water footprint under region=konkan's own rainfall (same "derive budget from B1's footprint" pattern as Phase 3/7/8). See docs/water.md section 8 and reports/results/region_comparison.md.

## water=tight, price=market

| strategy | profit | water_m3 | fert_kg | food_share | n_crops | profit_risk | profit_pct_vs_B1 | water_pct_vs_B1 | fert_pct_vs_B1 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 129794.13 | 21140.04 | 949.40 | 0.27 | 8 | 24817.39 | 0.00 | 0.00 | 0.00 | False |
| B2 | 203846.50 | 14798.03 | 849.99 | 0.69 | 3 | 64541.41 | 57.05 | -30.00 | -10.47 | True |
| B3 | 129794.13 | 4842.32 | 765.84 | 0.51 | 3 | 74790.34 | 0.00 | -77.09 | -19.33 | True |
| OURS | 142503.06 | 7958.62 | 608.92 | 0.66 | 3 | 67724.38 | 9.79 | -62.35 | -35.86 | True |

## water=tight, price=msp_floor

| strategy | profit | water_m3 | fert_kg | food_share | n_crops | profit_risk | profit_pct_vs_B1 | water_pct_vs_B1 | fert_pct_vs_B1 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 241557.08 | 21140.04 | 949.40 | 0.27 | 8 | 24817.39 | 0.00 | 0.00 | 0.00 | False |
| B2 | 319106.49 | 14798.03 | 831.16 | 0.50 | 3 | 75237.05 | 32.10 | -30.00 | -12.45 | True |
| B3 | 241557.08 | 640.03 | 692.56 | 0.50 | 3 | 72097.79 | 0.00 | -96.97 | -27.05 | True |
| OURS | 258498.04 | 7628.52 | 667.19 | 0.50 | 3 | 71005.82 | 7.01 | -63.91 | -29.73 | True |

## water=current, price=market

| strategy | profit | water_m3 | fert_kg | food_share | n_crops | profit_risk | profit_pct_vs_B1 | water_pct_vs_B1 | fert_pct_vs_B1 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 129794.13 | 21140.04 | 949.40 | 0.27 | 8 | 24817.39 | 0.00 | 0.00 | 0.00 | False |
| B2 | 241676.23 | 21140.04 | 947.13 | 0.62 | 3 | 57900.72 | 86.20 | 0.00 | -0.24 | True |
| B3 | 129794.13 | 4842.32 | 765.84 | 0.51 | 3 | 74790.34 | 0.00 | -77.09 | -19.33 | True |
| OURS | 166955.63 | 13097.63 | 694.10 | 0.51 | 4 | 45012.81 | 28.63 | -38.04 | -26.89 | True |

## water=current, price=msp_floor

| strategy | profit | water_m3 | fert_kg | food_share | n_crops | profit_risk | profit_pct_vs_B1 | water_pct_vs_B1 | fert_pct_vs_B1 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 241557.08 | 21140.04 | 949.40 | 0.27 | 8 | 24817.39 | 0.00 | 0.00 | 0.00 | False |
| B2 | 345778.72 | 21140.04 | 872.31 | 0.50 | 3 | 78616.08 | 43.15 | 0.00 | -8.12 | True |
| B3 | 241557.08 | 640.03 | 692.56 | 0.50 | 3 | 72097.79 | 0.00 | -96.97 | -27.05 | True |
| OURS | 273490.16 | 11468.87 | 677.25 | 0.50 | 3 | 71930.33 | 13.22 | -45.75 | -28.66 | True |
