# Decision backtest v2: fairness, water-matched oracle, decomposition (Phase 7.1)

## 1. B1 feasibility and B1_SCALED fairness

| year | scenario | budget_m3 | b1_water_m3 | b1_feasible | b1_scale_factor | b1_scaled_water_m3 | b1_scaled_feasible | b1_scaled_food_share_violated |
|---|---|---|---|---|---|---|---|---|
| 2016 | default | 75,242.917 | 75,242.917 | True | 1.000 | 75,242.917 | True | False |
| 2016 | tight | 52,670.042 | 75,242.917 | False | 0.700 | 52,670.042 | True | False |
| 2017 | default | 74,214.207 | 74,214.207 | True | 1.000 | 74,214.207 | True | False |
| 2017 | tight | 51,949.945 | 74,214.207 | False | 0.700 | 51,949.945 | True | False |
| 2018 | default | 73,900.714 | 73,900.714 | True | 1.000 | 73,900.714 | True | False |
| 2018 | tight | 51,730.499 | 73,900.714 | False | 0.700 | 51,730.499 | True | False |
| 2019 | default | 74,423.749 | 74,423.749 | True | 1.000 | 74,423.749 | True | False |
| 2019 | tight | 52,096.624 | 74,423.749 | False | 0.700 | 52,096.624 | True | False |
| 2020 | default | 74,274.185 | 74,274.185 | True | 1.000 | 74,274.185 | True | False |
| 2020 | tight | 51,991.930 | 74,274.185 | False | 0.700 | 51,991.930 | True | False |

## 2. Win counts and capture ratios (2016-2019, n=4)

| scenario | strategy | n_years | win_count_vs_b1 | win_count_vs_b1_scaled | mean_capture_ratio_w | mean_profit_per_1000m3 |
|---|---|---|---|---|---|---|
| default | B1 | 4 | nan | nan | 0.612 | 5,636.307 |
| default | B1_SCALED | 4 | nan | nan | 0.612 | 5,636.307 |
| default | B2 | 4 | 4.000 | 4.000 | 1.000 | 9,178.823 |
| default | B3 | 4 | 4.000 | 4.000 | 1.000 | 9,509.605 |
| default | MODEL_B | 4 | 2.000 | 2.000 | 0.880 | 8,129.625 |
| default | ORACLE | 4 | nan | nan | 1.000 | 9,178.823 |
| default | OURS | 4 | 4.000 | 4.000 | 0.966 | 9,051.012 |
| tight | B1 | 4 | nan | nan | 0.612 | 5,636.307 |
| tight | B1_SCALED | 4 | nan | nan | 0.602 | 5,636.307 |
| tight | B2 | 4 | 4.000 | 4.000 | 1.000 | 9,360.228 |
| tight | B3 | 4 | 4.000 | 4.000 | 1.000 | 9,509.605 |
| tight | MODEL_B | 4 | 0.000 | 3.000 | 0.862 | 8,083.521 |
| tight | ORACLE | 4 | nan | nan | 1.000 | 9,360.228 |
| tight | OURS | 4 | 0.000 | 4.000 | 0.966 | 9,270.611 |

## 3. Budget-level capture ratio (vs ORACLE, same definition as Phase 7)

| scenario | strategy | capture_ratio |
|---|---|---|
| default | B1 | 0.614 |
| default | B1_SCALED | 0.614 |
| default | B2 | 1.000 |
| default | B3 | 0.638 |
| default | MODEL_B | 0.662 |
| default | ORACLE | 1.000 |
| default | OURS | 0.711 |
| tight | B1 | 0.860 |
| tight | B1_SCALED | 0.602 |
| tight | B2 | 1.000 |
| tight | B3 | 0.893 |
| tight | MODEL_B | 0.649 |
| tight | ORACLE | 1.000 |
| tight | OURS | 0.727 |

## 4. B2 vs ORACLE allocation

| year | scenario | identical_alloc | max_abs_diff_ha | b2_realized_profit | oracle_realized_profit |
|---|---|---|---|---|---|
| 2016 | default | True | 0.0000 | 747,992 | 747,992 |
| 2016 | tight | True | 0.0000 | 567,941 | 567,941 |
| 2017 | default | True | 0.0000 | 619,069 | 619,069 |
| 2017 | tight | True | 0.0000 | 430,893 | 430,893 |
| 2018 | default | True | 0.0000 | 656,458 | 656,458 |
| 2018 | tight | True | 0.0000 | 456,315 | 456,315 |
| 2019 | default | True | 0.0000 | 710,719 | 710,719 |
| 2019 | tight | True | 0.0000 | 497,132 | 497,132 |
