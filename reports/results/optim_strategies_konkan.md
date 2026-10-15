# Optimizer strategies (E3.1), NET IRRIGATION water basis, region=konkan (Phase 8.1)

Water budget derived from B1's own NET-irrigation water footprint under region=konkan's own rainfall (same "derive budget from B1's footprint" pattern as Phase 3/7/8). See docs/water.md section 8 and reports/results/region_comparison.md.

## water=tight, price=market

| strategy | profit | water_m3 | fert_kg | food_share | n_crops | profit_risk | profit_pct_vs_B1 | water_pct_vs_B1 | fert_pct_vs_B1 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 182833.11 | 51788.03 | 1375.94 | 0.45 | 8 | 166631.90 | 0.00 | 0.00 | 0.00 | False |
| B2 | 282836.66 | 36251.62 | 1148.57 | 0.38 | 3 | 90685.08 | 54.70 | -30.00 | -16.53 | True |
| B3 | 182833.11 | 19638.90 | 958.03 | 0.47 | 3 | 87725.97 | 0.00 | -62.08 | -30.37 | True |
| OURS | 190498.82 | 21163.67 | 838.65 | 0.68 | 4 | 171886.68 | 4.19 | -59.13 | -39.05 | True |

## water=tight, price=msp_floor

| strategy | profit | water_m3 | fert_kg | food_share | n_crops | profit_risk | profit_pct_vs_B1 | water_pct_vs_B1 | fert_pct_vs_B1 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 343281.89 | 51788.03 | 1375.94 | 0.45 | 8 | 207079.31 | 0.00 | 0.00 | 0.00 | False |
| B2 | 354866.39 | 36251.62 | 1383.49 | 0.74 | 4 | 261479.28 | 3.37 | -30.00 | 0.55 | True |
| B3 | 343281.89 | 33549.25 | 1326.02 | 0.74 | 3 | 265289.66 | 0.00 | -35.22 | -3.63 | True |
| OURS | 290380.97 | 21359.81 | 896.47 | 0.56 | 4 | 249364.32 | -15.41 | -58.76 | -34.85 | True |

## water=current, price=market

| strategy | profit | water_m3 | fert_kg | food_share | n_crops | profit_risk | profit_pct_vs_B1 | water_pct_vs_B1 | fert_pct_vs_B1 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 182833.11 | 51788.03 | 1375.94 | 0.45 | 8 | 166631.90 | 0.00 | 0.00 | 0.00 | True |
| B2 | 376333.91 | 51788.03 | 1324.30 | 0.30 | 3 | 98056.07 | 105.83 | 0.00 | -3.75 | True |
| B3 | 182833.11 | 19638.90 | 958.03 | 0.47 | 3 | 87725.97 | 0.00 | -62.08 | -30.37 | True |
| OURS | 253234.80 | 31904.54 | 963.19 | 0.60 | 3 | 161765.76 | 38.51 | -38.39 | -30.00 | True |

## water=current, price=msp_floor

| strategy | profit | water_m3 | fert_kg | food_share | n_crops | profit_risk | profit_pct_vs_B1 | water_pct_vs_B1 | fert_pct_vs_B1 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 343281.89 | 51788.03 | 1375.94 | 0.45 | 8 | 207079.31 | 0.00 | 0.00 | 0.00 | True |
| B2 | 420937.13 | 51788.03 | 1625.45 | 0.55 | 4 | 203756.21 | 22.62 | 0.00 | 18.13 | True |
| B3 | 343281.89 | 33549.25 | 1326.02 | 0.74 | 3 | 265289.66 | 0.00 | -35.22 | -3.63 | True |
| OURS | 323770.12 | 30921.82 | 781.69 | 0.57 | 4 | 249910.29 | -5.68 | -40.29 | -43.19 | True |
