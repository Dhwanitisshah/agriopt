# Optimizer strategies (E3.1), NET IRRIGATION water basis, region=marathwada (Phase 8.1)

Water budget derived from B1's own NET-irrigation water footprint under region=marathwada's own rainfall (same "derive budget from B1's footprint" pattern as Phase 3/7/8). See docs/water.md section 8 and reports/results/region_comparison.md.

## water=tight, price=market

| strategy | profit | water_m3 | fert_kg | food_share | n_crops | profit_risk | profit_pct_vs_B1 | water_pct_vs_B1 | fert_pct_vs_B1 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 166258.97 | 34053.94 | 971.33 | 0.47 | 8 | 23416.91 | 0.00 | 0.00 | 0.00 | False |
| B2 | 285746.79 | 23837.76 | 868.54 | 0.90 | 3 | 70470.46 | 71.87 | -30.00 | -10.58 | True |
| B3 | 166258.97 | 10708.95 | 767.87 | 0.95 | 3 | 71025.37 | 0.00 | -68.55 | -20.95 | True |
| OURS | 189870.25 | 13752.75 | 684.53 | 0.85 | 3 | 69848.63 | 14.20 | -59.61 | -29.53 | True |

## water=tight, price=msp_floor

| strategy | profit | water_m3 | fert_kg | food_share | n_crops | profit_risk | profit_pct_vs_B1 | water_pct_vs_B1 | fert_pct_vs_B1 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 278021.92 | 34053.94 | 971.33 | 0.47 | 8 | 23416.91 | 0.00 | 0.00 | 0.00 | False |
| B2 | 412305.54 | 23837.76 | 854.89 | 0.50 | 3 | 70775.50 | 48.30 | -30.00 | -11.99 | True |
| B3 | 278021.92 | 6908.70 | 722.44 | 0.50 | 3 | 72416.40 | 0.00 | -79.71 | -25.62 | True |
| OURS | 299622.95 | 13350.90 | 657.74 | 0.52 | 4 | 70163.37 | 7.77 | -60.79 | -32.28 | True |

## water=current, price=market

| strategy | profit | water_m3 | fert_kg | food_share | n_crops | profit_risk | profit_pct_vs_B1 | water_pct_vs_B1 | fert_pct_vs_B1 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 166258.97 | 34053.94 | 971.33 | 0.47 | 8 | 23416.91 | 0.00 | 0.00 | 0.00 | True |
| B2 | 378104.54 | 34053.94 | 945.46 | 0.81 | 3 | 69831.44 | 127.42 | 0.00 | -2.66 | True |
| B3 | 166258.97 | 10708.95 | 767.87 | 0.95 | 3 | 71025.37 | 0.00 | -68.55 | -20.95 | True |
| OURS | 253959.73 | 20844.98 | 769.62 | 0.83 | 4 | 69144.40 | 52.75 | -38.79 | -20.77 | True |

## water=current, price=msp_floor

| strategy | profit | water_m3 | fert_kg | food_share | n_crops | profit_risk | profit_pct_vs_B1 | water_pct_vs_B1 | fert_pct_vs_B1 | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | 278021.92 | 34053.94 | 971.33 | 0.47 | 8 | 23416.91 | 0.00 | 0.00 | 0.00 | True |
| B2 | 493341.73 | 34053.94 | 934.83 | 0.50 | 3 | 70018.38 | 77.45 | 0.00 | -3.76 | True |
| B3 | 278021.92 | 6908.70 | 722.44 | 0.50 | 3 | 72416.40 | 0.00 | -79.71 | -25.62 | True |
| OURS | 355913.38 | 20522.37 | 712.75 | 0.54 | 5 | 69757.67 | 28.02 | -39.74 | -26.62 | True |
