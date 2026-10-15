# Optimizer strategies (E3.1), NET IRRIGATION water basis (Phase 8)

Water budget derived from B1's own NET-irrigation water footprint (same "derive budget from B1's footprint" pattern as Phase 3/7). See docs/water.md and reports/results/water_basis_comparison.md.

## water=tight, price=market

| strategy | profit | water_m3 | fert_kg | food_share | n_crops | profit_risk | profit_pct_vs_B1 | water_pct_vs_B1 | fert_pct_vs_B1 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 182833.11 | 54531.58 | 1375.94 | 0.45 | 8 | 166631.90 | 0.00 | 0.00 | 0.00 | False |
| B2 | 274255.50 | 38172.11 | 1030.79 | 0.55 | 3 | 145093.94 | 50.00 | -30.00 | -25.08 | True |
| B3 | 182833.11 | 21519.98 | 796.03 | 0.73 | 3 | 196668.48 | 0.00 | -60.54 | -42.15 | True |
| OURS | 194508.75 | 24197.88 | 803.55 | 0.72 | 3 | 199570.97 | 6.39 | -55.63 | -41.60 | True |

## water=tight, price=msp_floor

| strategy | profit | water_m3 | fert_kg | food_share | n_crops | profit_risk | profit_pct_vs_B1 | water_pct_vs_B1 | fert_pct_vs_B1 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 343281.89 | 54531.58 | 1375.94 | 0.45 | 8 | 207079.31 | 0.00 | 0.00 | 0.00 | False |
| B2 | 358347.12 | 38172.11 | 1396.23 | 0.73 | 4 | 258070.84 | 4.39 | -30.00 | 1.47 | True |
| B3 | 343281.89 | 34469.24 | 1326.02 | 0.74 | 3 | 265289.66 | 0.00 | -36.79 | -3.63 | True |
| OURS | 280205.86 | 21983.24 | 734.31 | 0.53 | 4 | 245181.74 | -18.37 | -59.69 | -46.63 | True |

## water=current, price=market

| strategy | profit | water_m3 | fert_kg | food_share | n_crops | profit_risk | profit_pct_vs_B1 | water_pct_vs_B1 | fert_pct_vs_B1 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 182833.11 | 54531.58 | 1375.94 | 0.45 | 8 | 166631.90 | 0.00 | 0.00 | 0.00 | True |
| B2 | 364071.21 | 54531.58 | 1261.42 | 0.38 | 3 | 109710.47 | 99.13 | 0.00 | -8.32 | True |
| B3 | 182833.11 | 21519.98 | 796.03 | 0.73 | 3 | 196668.48 | 0.00 | -60.54 | -42.15 | True |
| OURS | 258265.00 | 36518.54 | 938.42 | 0.61 | 3 | 175347.51 | 41.26 | -33.03 | -31.80 | True |

## water=current, price=msp_floor

| strategy | profit | water_m3 | fert_kg | food_share | n_crops | profit_risk | profit_pct_vs_B1 | water_pct_vs_B1 | fert_pct_vs_B1 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 343281.89 | 54531.58 | 1375.94 | 0.45 | 8 | 207079.31 | 0.00 | 0.00 | 0.00 | True |
| B2 | 421323.13 | 54531.58 | 1626.87 | 0.55 | 4 | 203473.91 | 22.73 | 0.00 | 18.24 | True |
| B3 | 343281.89 | 34469.24 | 1326.02 | 0.74 | 3 | 265289.66 | 0.00 | -36.79 | -3.63 | True |
| OURS | 335225.11 | 35787.33 | 822.57 | 0.53 | 4 | 248076.39 | -2.35 | -34.37 | -40.22 | True |
