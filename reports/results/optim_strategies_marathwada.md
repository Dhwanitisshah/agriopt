# Optimizer strategies (E3.1), NET IRRIGATION water basis, region=marathwada (Phase 8.1)

Water budget derived from B1's own NET-irrigation water footprint under region=marathwada's own rainfall (same "derive budget from B1's footprint" pattern as Phase 3/7/8). See docs/water.md section 8 and reports/results/region_comparison.md.

## water=tight, price=market

| strategy | profit | water_m3 | fert_kg | food_share | n_crops | profit_risk | profit_pct_vs_B1 | water_pct_vs_B1 | fert_pct_vs_B1 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 129794.13 | 32569.93 | 949.40 | 0.27 | 8 | 24817.39 | 0.00 | 0.00 | 0.00 | False |
| B2 | 225549.96 | 22798.95 | 905.72 | 0.65 | 3 | 60331.27 | 73.78 | -30.00 | -4.60 | True |
| B3 | 129794.13 | 7034.77 | 732.78 | 0.64 | 3 | 70497.20 | 0.00 | -78.40 | -22.82 | True |
| OURS | 168093.18 | 13299.12 | 697.49 | 0.66 | 3 | 66372.48 | 29.51 | -59.17 | -26.53 | True |

## water=tight, price=msp_floor

| strategy | profit | water_m3 | fert_kg | food_share | n_crops | profit_risk | profit_pct_vs_B1 | water_pct_vs_B1 | fert_pct_vs_B1 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 241557.08 | 32569.93 | 949.40 | 0.27 | 8 | 24817.39 | 0.00 | 0.00 | 0.00 | False |
| B2 | 329696.94 | 22798.95 | 1244.33 | 0.71 | 3 | 73577.89 | 36.49 | -30.00 | 31.07 | True |
| B3 | 241557.08 | 2866.55 | 714.34 | 0.51 | 3 | 73026.47 | 0.00 | -91.20 | -24.76 | True |
| OURS | 269199.24 | 12577.79 | 715.65 | 0.51 | 4 | 72561.54 | 11.44 | -61.38 | -24.62 | True |

## water=current, price=market

| strategy | profit | water_m3 | fert_kg | food_share | n_crops | profit_risk | profit_pct_vs_B1 | water_pct_vs_B1 | fert_pct_vs_B1 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 129794.13 | 32569.93 | 949.40 | 0.27 | 8 | 24817.39 | 0.00 | 0.00 | 0.00 | False |
| B2 | 269505.83 | 32569.93 | 1018.59 | 0.56 | 3 | 55350.09 | 107.64 | 0.00 | 7.29 | True |
| B3 | 129794.13 | 7034.77 | 732.78 | 0.64 | 3 | 70497.20 | 0.00 | -78.40 | -22.82 | True |
| OURS | 210215.98 | 20051.05 | 862.90 | 0.65 | 3 | 59692.10 | 61.96 | -38.44 | -9.11 | True |

## water=current, price=msp_floor

| strategy | profit | water_m3 | fert_kg | food_share | n_crops | profit_risk | profit_pct_vs_B1 | water_pct_vs_B1 | fert_pct_vs_B1 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 241557.08 | 32569.93 | 949.40 | 0.27 | 8 | 24817.39 | 0.00 | 0.00 | 0.00 | False |
| B2 | 366246.57 | 32569.93 | 1425.16 | 0.70 | 4 | 68253.43 | 51.62 | 0.00 | 50.11 | True |
| B3 | 241557.08 | 2866.55 | 714.34 | 0.51 | 3 | 73026.47 | 0.00 | -91.20 | -24.76 | True |
| OURS | 290539.07 | 17466.96 | 894.42 | 0.60 | 5 | 71800.06 | 20.28 | -46.37 | -5.79 | True |
