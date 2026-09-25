# Optimizer strategies (E3.1), NET IRRIGATION water basis (Phase 8)

Water budget derived from B1's own NET-irrigation water footprint (same "derive budget from B1's footprint" pattern as Phase 3/7). See docs/water.md and reports/results/water_basis_comparison.md.

## water=tight, price=market

| strategy | profit | water_m3 | fert_kg | food_share | n_crops | profit_risk | profit_pct_vs_B1 | water_pct_vs_B1 | fert_pct_vs_B1 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 166258.97 | 25980.01 | 971.33 | 0.47 | 8 | 23416.91 | 0.00 | 0.00 | 0.00 | False |
| B2 | 349191.20 | 18186.01 | 1025.75 | 0.85 | 3 | 52360.81 | 110.03 | -30.00 | 5.60 | True |
| B3 | 166258.97 | 0.00 | 746.21 | 0.92 | 2 | 60411.05 | 0.00 | -100.00 | -23.18 | True |
| OURS | 247836.55 | 10347.98 | 795.23 | 0.79 | 3 | 55000.76 | 49.07 | -60.17 | -18.13 | True |

## water=tight, price=msp_floor

| strategy | profit | water_m3 | fert_kg | food_share | n_crops | profit_risk | profit_pct_vs_B1 | water_pct_vs_B1 | fert_pct_vs_B1 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 278021.92 | 25980.01 | 971.33 | 0.47 | 8 | 23416.91 | 0.00 | 0.00 | 0.00 | False |
| B2 | 404680.63 | 18186.01 | 904.85 | 0.85 | 3 | 70149.78 | 45.56 | -30.00 | -6.84 | True |
| B3 | 278021.92 | 3239.72 | 799.36 | 0.97 | 3 | 71174.10 | 0.00 | -87.53 | -17.70 | True |
| OURS | 302376.01 | 9727.22 | 693.71 | 0.60 | 6 | 69323.96 | 8.76 | -62.56 | -28.58 | True |

## water=current, price=market

| strategy | profit | water_m3 | fert_kg | food_share | n_crops | profit_risk | profit_pct_vs_B1 | water_pct_vs_B1 | fert_pct_vs_B1 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 166258.97 | 25980.01 | 971.33 | 0.47 | 8 | 23416.91 | 0.00 | 0.00 | 0.00 | True |
| B2 | 423747.48 | 25980.01 | 1132.57 | 0.79 | 3 | 44459.17 | 154.87 | -0.00 | 16.60 | True |
| B3 | 166258.97 | 0.00 | 746.21 | 0.92 | 2 | 60411.05 | 0.00 | -100.00 | -23.18 | True |
| OURS | 305165.82 | 15121.56 | 943.01 | 0.79 | 3 | 45116.79 | 83.55 | -41.80 | -2.92 | True |

## water=current, price=msp_floor

| strategy | profit | water_m3 | fert_kg | food_share | n_crops | profit_risk | profit_pct_vs_B1 | water_pct_vs_B1 | fert_pct_vs_B1 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 278021.92 | 25980.01 | 971.33 | 0.47 | 8 | 23416.91 | 0.00 | 0.00 | 0.00 | True |
| B2 | 470729.05 | 25980.01 | 959.85 | 0.79 | 3 | 69728.95 | 69.31 | 0.00 | -1.18 | True |
| B3 | 278021.92 | 3239.72 | 799.36 | 0.97 | 3 | 71174.10 | 0.00 | -87.53 | -17.70 | True |
| OURS | 351844.65 | 15183.77 | 746.83 | 0.78 | 6 | 66739.91 | 26.55 | -41.56 | -23.11 | True |
