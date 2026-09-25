# Optimizer strategies (E3.1), NET IRRIGATION water basis, region=konkan (Phase 8.1)

Water budget derived from B1's own NET-irrigation water footprint under region=konkan's own rainfall (same "derive budget from B1's footprint" pattern as Phase 3/7/8). See docs/water.md section 8 and reports/results/region_comparison.md.

## water=tight, price=market

| strategy | profit | water_m3 | fert_kg | food_share | n_crops | profit_risk | profit_pct_vs_B1 | water_pct_vs_B1 | fert_pct_vs_B1 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 166258.97 | 22259.24 | 971.33 | 0.47 | 8 | 23416.91 | 0.00 | 0.00 | 0.00 | False |
| B2 | 265650.05 | 15581.47 | 698.62 | 0.85 | 3 | 69537.75 | 59.78 | -30.00 | -28.08 | True |
| B3 | 166258.97 | 7126.55 | 581.07 | 0.93 | 3 | 69890.87 | 0.00 | -67.98 | -40.18 | True |
| OURS | 184934.94 | 9137.17 | 563.76 | 0.83 | 3 | 68414.91 | 11.23 | -58.95 | -41.96 | True |

## water=tight, price=msp_floor

| strategy | profit | water_m3 | fert_kg | food_share | n_crops | profit_risk | profit_pct_vs_B1 | water_pct_vs_B1 | fert_pct_vs_B1 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 278021.92 | 22259.24 | 971.33 | 0.47 | 8 | 23416.91 | 0.00 | 0.00 | 0.00 | False |
| B2 | 396119.81 | 15581.47 | 838.93 | 0.50 | 3 | 70948.13 | 42.48 | -30.00 | -13.63 | True |
| B3 | 278021.92 | 4088.36 | 722.44 | 0.50 | 3 | 72416.40 | -0.00 | -81.63 | -25.62 | True |
| OURS | 299508.04 | 9385.67 | 604.08 | 0.79 | 6 | 66579.27 | 7.73 | -57.83 | -37.81 | True |

## water=current, price=market

| strategy | profit | water_m3 | fert_kg | food_share | n_crops | profit_risk | profit_pct_vs_B1 | water_pct_vs_B1 | fert_pct_vs_B1 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 166258.97 | 22259.24 | 971.33 | 0.47 | 8 | 23416.91 | 0.00 | 0.00 | 0.00 | True |
| B2 | 344150.03 | 22259.24 | 791.45 | 0.79 | 3 | 69308.77 | 107.00 | 0.00 | -18.52 | True |
| B3 | 166258.97 | 7126.55 | 581.07 | 0.93 | 3 | 69890.87 | 0.00 | -67.98 | -40.18 | True |
| OURS | 232078.44 | 13364.85 | 696.05 | 0.75 | 6 | 67148.57 | 39.59 | -39.96 | -28.34 | True |

## water=current, price=msp_floor

| strategy | profit | water_m3 | fert_kg | food_share | n_crops | profit_risk | profit_pct_vs_B1 | water_pct_vs_B1 | fert_pct_vs_B1 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 278021.92 | 22259.24 | 971.33 | 0.47 | 8 | 23416.91 | 0.00 | 0.00 | 0.00 | True |
| B2 | 464737.49 | 22259.24 | 906.61 | 0.50 | 3 | 70265.03 | 67.16 | 0.00 | -6.66 | True |
| B3 | 278021.92 | 4088.36 | 722.44 | 0.50 | 3 | 72416.40 | -0.00 | -81.63 | -25.62 | True |
| OURS | 345879.68 | 12968.60 | 770.70 | 0.49 | 3 | 69190.67 | 24.41 | -41.74 | -20.66 | True |
