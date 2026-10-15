# Optimizer strategies (E3.1), NET IRRIGATION water basis, region=marathwada (Phase 8.1)

Water budget derived from B1's own NET-irrigation water footprint under region=marathwada's own rainfall (same "derive budget from B1's footprint" pattern as Phase 3/7/8). See docs/water.md section 8 and reports/results/region_comparison.md.

## water=tight, price=market

| strategy | profit | water_m3 | fert_kg | food_share | n_crops | profit_risk | profit_pct_vs_B1 | water_pct_vs_B1 | fert_pct_vs_B1 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 182833.11 | 60605.98 | 1375.94 | 0.45 | 8 | 166631.90 | 0.00 | 0.00 | 0.00 | False |
| B2 | 270903.52 | 42424.18 | 1022.18 | 0.56 | 3 | 146792.29 | 48.17 | -30.00 | -25.71 | True |
| B3 | 182833.11 | 24744.25 | 796.03 | 0.73 | 3 | 196668.48 | 0.00 | -59.17 | -42.15 | True |
| OURS | 190567.82 | 27412.77 | 768.16 | 0.70 | 3 | 199065.96 | 4.23 | -54.77 | -44.17 | True |

## water=tight, price=msp_floor

| strategy | profit | water_m3 | fert_kg | food_share | n_crops | profit_risk | profit_pct_vs_B1 | water_pct_vs_B1 | fert_pct_vs_B1 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 343281.89 | 60605.98 | 1375.94 | 0.45 | 8 | 207079.31 | 0.00 | 0.00 | 0.00 | False |
| B2 | 361621.63 | 42424.18 | 1408.23 | 0.72 | 4 | 254893.66 | 5.34 | -30.00 | 2.35 | True |
| B3 | 343281.89 | 37553.80 | 1326.02 | 0.74 | 3 | 265289.66 | 0.00 | -38.04 | -3.63 | True |
| OURS | 280075.50 | 23672.73 | 885.99 | 0.57 | 4 | 249811.05 | -18.41 | -60.94 | -35.61 | True |

## water=current, price=market

| strategy | profit | water_m3 | fert_kg | food_share | n_crops | profit_risk | profit_pct_vs_B1 | water_pct_vs_B1 | fert_pct_vs_B1 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 182833.11 | 60605.98 | 1375.94 | 0.45 | 8 | 166631.90 | 0.00 | 0.00 | 0.00 | True |
| B2 | 361473.86 | 60605.98 | 1254.75 | 0.38 | 3 | 110370.27 | 97.71 | 0.00 | -8.81 | True |
| B3 | 182833.11 | 24744.25 | 796.03 | 0.73 | 3 | 196668.48 | 0.00 | -59.17 | -42.15 | True |
| OURS | 248237.05 | 38862.81 | 913.90 | 0.63 | 3 | 180412.17 | 35.77 | -35.88 | -33.58 | True |

## water=current, price=msp_floor

| strategy | profit | water_m3 | fert_kg | food_share | n_crops | profit_risk | profit_pct_vs_B1 | water_pct_vs_B1 | fert_pct_vs_B1 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 343281.89 | 60605.98 | 1375.94 | 0.45 | 8 | 207079.31 | 0.00 | 0.00 | 0.00 | True |
| B2 | 425126.76 | 60605.98 | 1640.80 | 0.54 | 4 | 200735.74 | 23.84 | 0.00 | 19.25 | True |
| B3 | 343281.89 | 37553.80 | 1326.02 | 0.74 | 3 | 265289.66 | 0.00 | -38.04 | -3.63 | True |
| OURS | 327185.78 | 34089.94 | 1204.67 | 0.69 | 4 | 260730.34 | -4.69 | -43.75 | -12.45 | True |
