# Decision backtest v2: fairness, water-matched oracle, decomposition (Phase 7.1)

## 1. B1 feasibility and B1_SCALED fairness

| year | scenario | budget_m3 | b1_water_m3 | b1_feasible | b1_scale_factor | b1_scaled_water_m3 | b1_scaled_feasible | b1_scaled_food_share_violated |
|---|---|---|---|---|---|---|---|---|
| 2016 | default | 72,864.074 | 72,864.074 | False | 1.000 | 72,864.074 | False | True |
| 2016 | tight | 51,004.852 | 72,864.074 | False | 0.700 | 51,004.852 | False | True |
| 2017 | default | 72,066.133 | 72,066.133 | False | 1.000 | 72,066.133 | False | True |
| 2017 | tight | 50,446.293 | 72,066.133 | False | 0.700 | 50,446.293 | False | True |
| 2018 | default | 71,808.973 | 71,808.973 | False | 1.000 | 71,808.973 | False | True |
| 2018 | tight | 50,266.281 | 71,808.973 | False | 0.700 | 50,266.281 | False | True |
| 2019 | default | 72,212.949 | 72,212.949 | False | 1.000 | 72,212.949 | False | True |
| 2019 | tight | 50,549.065 | 72,212.949 | False | 0.700 | 50,549.065 | False | True |
| 2020 | default | 72,155.829 | 72,155.829 | False | 1.000 | 72,155.829 | False | True |
| 2020 | tight | 50,509.080 | 72,155.829 | False | 0.700 | 50,509.080 | False | True |

## 2. Win counts and capture ratios (2016-2019, n=4)

| scenario | strategy | n_years | win_count_vs_b1 | win_count_vs_b1_scaled | mean_capture_ratio_w | mean_profit_per_1000m3 |
|---|---|---|---|---|---|---|
| default | B1 | 4 | nan | nan | 0.550 | 2,241.053 |
| default | B1_SCALED | 4 | nan | nan | 0.550 | 2,241.053 |
| default | B2 | 4 | 4.000 | 4.000 | 0.889 | 3,541.877 |
| default | B3 | 4 | 2.000 | 2.000 | 0.891 | 4,713.306 |
| default | MODEL_B | 4 | 3.000 | 3.000 | 0.804 | 3,362.799 |
| default | ORACLE | 4 | nan | nan | 1.000 | 4,113.288 |
| default | OURS | 4 | 3.000 | 3.000 | 0.883 | 3,937.730 |
| tight | B1 | 4 | nan | nan | 0.550 | 2,241.053 |
| tight | B1_SCALED | 4 | nan | nan | 0.500 | 2,241.053 |
| tight | B2 | 4 | 3.000 | 4.000 | 0.910 | 4,051.132 |
| tight | B3 | 4 | 2.000 | 4.000 | 0.891 | 4,713.306 |
| tight | MODEL_B | 4 | 2.000 | 3.000 | 0.790 | 3,605.050 |
| tight | ORACLE | 4 | nan | nan | 1.000 | 4,530.613 |
| tight | OURS | 4 | 3.000 | 3.000 | 0.881 | 4,373.573 |

## 3. Budget-level capture ratio (vs ORACLE, same definition as Phase 7)

| scenario | strategy | capture_ratio |
|---|---|---|
| default | B1 | 0.554 |
| default | B1_SCALED | 0.554 |
| default | B2 | 0.875 |
| default | B3 | 0.575 |
| default | MODEL_B | 0.616 |
| default | ORACLE | 1.000 |
| default | OURS | 0.686 |
| tight | B1 | 0.707 |
| tight | B1_SCALED | 0.495 |
| tight | B2 | 0.894 |
| tight | B3 | 0.733 |
| tight | MODEL_B | 0.611 |
| tight | ORACLE | 1.000 |
| tight | OURS | 0.705 |

## 4. B2 vs ORACLE allocation

| year | scenario | identical_alloc | max_abs_diff_ha | b2_realized_profit | oracle_realized_profit |
|---|---|---|---|---|---|
| 2016 | default | False | 5.0000 | 411,274 | 480,492 |
| 2016 | tight | False | 5.0000 | 333,832 | 393,529 |
| 2017 | default | False | 1.5816 | 208,866 | 215,769 |
| 2017 | tight | True | 0.0000 | 173,651 | 173,651 |
| 2018 | default | False | 2.7059 | 212,083 | 213,937 |
| 2018 | tight | False | 1.0879 | 158,709 | 165,687 |
| 2019 | default | False | 5.0000 | 192,911 | 261,100 |
| 2019 | tight | False | 5.0000 | 154,668 | 185,438 |
