# Optimizer strategies (E3.1), NET IRRIGATION water basis (Phase 8)

Water budget derived from B1's own NET-irrigation water footprint (same "derive budget from B1's footprint" pattern as Phase 3/7). See docs/water.md and reports/results/water_basis_comparison.md.

## water=tight, price=market

| strategy | profit | water_m3 | fert_kg | food_share | n_crops | profit_risk | profit_pct_vs_B1 | water_pct_vs_B1 | fert_pct_vs_B1 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 129794.13 | 27707.31 | 949.40 | 0.27 | 8 | 24817.39 | 0.00 | 0.00 | 0.00 | False |
| B2 | 221042.59 | 19395.12 | 894.15 | 0.66 | 3 | 61122.23 | 70.30 | -30.00 | -5.82 | True |
| B3 | 129794.13 | 5101.26 | 632.23 | 0.75 | 3 | 69856.86 | 0.00 | -81.59 | -33.41 | True |
| OURS | 158449.42 | 10039.52 | 691.72 | 0.64 | 4 | 60525.80 | 22.08 | -63.77 | -27.14 | True |

## water=tight, price=msp_floor

| strategy | profit | water_m3 | fert_kg | food_share | n_crops | profit_risk | profit_pct_vs_B1 | water_pct_vs_B1 | fert_pct_vs_B1 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 241557.08 | 27707.31 | 949.40 | 0.27 | 8 | 24817.39 | 0.00 | 0.00 | 0.00 | False |
| B2 | 321732.80 | 19395.12 | 1196.44 | 0.69 | 3 | 73488.09 | 33.19 | -30.00 | 26.02 | True |
| B3 | 241557.08 | 1254.65 | 714.34 | 0.51 | 3 | 73026.47 | 0.00 | -95.47 | -24.76 | True |
| OURS | 264308.84 | 10302.81 | 679.07 | 0.54 | 4 | 71796.31 | 9.42 | -62.82 | -28.47 | True |

## water=current, price=market

| strategy | profit | water_m3 | fert_kg | food_share | n_crops | profit_risk | profit_pct_vs_B1 | water_pct_vs_B1 | fert_pct_vs_B1 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 129794.13 | 27707.31 | 949.40 | 0.27 | 8 | 24817.39 | 0.00 | 0.00 | 0.00 | False |
| B2 | 261577.68 | 27707.31 | 998.23 | 0.58 | 3 | 55849.94 | 101.53 | 0.00 | 5.14 | True |
| B3 | 129794.13 | 5101.26 | 632.23 | 0.75 | 3 | 69856.86 | 0.00 | -81.59 | -33.41 | True |
| OURS | 194044.25 | 16286.79 | 794.28 | 0.63 | 4 | 59449.36 | 49.50 | -41.22 | -16.34 | True |

## water=current, price=msp_floor

| strategy | profit | water_m3 | fert_kg | food_share | n_crops | profit_risk | profit_pct_vs_B1 | water_pct_vs_B1 | fert_pct_vs_B1 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 241557.08 | 27707.31 | 949.40 | 0.27 | 8 | 24817.39 | 0.00 | 0.00 | 0.00 | False |
| B2 | 356481.05 | 27707.31 | 1389.40 | 0.73 | 4 | 71438.47 | 47.58 | 0.00 | 46.35 | True |
| B3 | 241557.08 | 1254.65 | 714.34 | 0.51 | 3 | 73026.47 | 0.00 | -95.47 | -24.76 | True |
| OURS | 283924.01 | 13936.32 | 894.13 | 0.65 | 7 | 69951.61 | 17.54 | -49.70 | -5.82 | True |
