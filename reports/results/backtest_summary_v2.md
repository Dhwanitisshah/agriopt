# Decision backtest v2: fairness, water-matched oracle, decomposition (Phase 7.1)

## 1. B1 feasibility and B1_SCALED fairness

| year | scenario | budget_m3 | b1_water_m3 | b1_feasible | b1_hectares_moved | b1_scaled_water_m3 | b1_scaled_feasible | b1_scaled_food_share_violated |
|---|---|---|---|---|---|---|---|---|
| 2016 | default | 105,497.109 | 105,497.109 | True | 0.000 | 105,497.109 | True | False |
| 2016 | tight | 73,847.976 | 105,497.109 | False | 2.684 | 73,847.976 | True | False |
| 2017 | default | 105,072.763 | 105,072.763 | True | 0.000 | 105,072.763 | True | False |
| 2017 | tight | 73,550.934 | 105,072.763 | False | 2.716 | 73,550.934 | True | False |
| 2018 | default | 104,980.450 | 104,980.450 | True | 0.000 | 104,980.450 | True | False |
| 2018 | tight | 73,486.315 | 104,980.450 | False | 2.724 | 73,486.315 | True | False |
| 2019 | default | 105,092.064 | 105,092.064 | True | 0.000 | 105,092.064 | True | False |
| 2019 | tight | 73,564.445 | 105,092.064 | False | 2.711 | 73,564.445 | True | False |
| 2020 | default | 104,850.601 | 104,850.601 | True | 0.000 | 104,850.601 | True | False |
| 2020 | tight | 73,395.421 | 104,850.601 | False | 2.728 | 73,395.421 | True | False |

## 2. Win counts and capture ratios (2016-2019, n=4)

| scenario | strategy | n_years | win_count_vs_b1 | win_count_vs_b1_scaled | mean_realized_profit | mean_capture_ratio_w | mean_profit_per_1000m3 |
|---|---|---|---|---|---|---|---|
| default | B1 | 4 | nan | nan | 229,478.567 | 0.656 | 2,180.663 |
| default | B1_SCALED | 4 | nan | nan | 229,478.567 | 0.656 | 2,180.663 |
| default | B2 | 4 | 2.000 | 2.000 | 288,084.437 | 0.868 | 2,738.775 |
| default | B3 | 4 | 2.000 | 2.000 | 220,336.578 | 0.893 | 3,934.997 |
| default | MODEL_B | 4 | 3.000 | 3.000 | 259,420.237 | 0.864 | 3,553.311 |
| default | ORACLE | 4 | nan | nan | 339,253.200 | 1.000 | 3,802.003 |
| default | OURS | 4 | 2.000 | 2.000 | 230,768.817 | 0.871 | 3,714.011 |
| tight | B1 | 4 | nan | nan | 229,478.567 | 0.656 | 2,180.663 |
| tight | B1_SCALED | 4 | nan | nan | 154,454.543 | 0.514 | 2,096.577 |
| tight | B2 | 4 | 3.000 | 4.000 | 259,036.394 | 0.890 | 3,516.715 |
| tight | B3 | 3 | 2.000 | 3.000 | 228,428.910 | 0.944 | 4,363.473 |
| tight | MODEL_B | 4 | 2.000 | 3.000 | 197,694.837 | 0.810 | 3,488.674 |
| tight | ORACLE | 4 | nan | nan | 295,021.856 | 1.000 | 4,094.456 |
| tight | OURS | 4 | 1.000 | 3.000 | 200,644.839 | 0.884 | 3,950.960 |

## 3. Budget-level capture ratio (vs ORACLE, same definition as Phase 7)

| scenario | strategy | capture_ratio |
|---|---|---|
| default | B1 | 0.676 |
| default | B1_SCALED | 0.676 |
| default | B2 | 0.849 |
| default | B3 | 0.649 |
| default | MODEL_B | 0.765 |
| default | ORACLE | 1.000 |
| default | OURS | 0.680 |
| tight | B1 | 0.778 |
| tight | B1_SCALED | 0.524 |
| tight | B2 | 0.878 |
| tight | B3 | 0.581 |
| tight | MODEL_B | 0.670 |
| tight | ORACLE | 1.000 |
| tight | OURS | 0.680 |

## 4. B2 vs ORACLE allocation

| year | scenario | identical_alloc | max_abs_diff_ha | b2_realized_profit | oracle_realized_profit |
|---|---|---|---|---|---|
| 2016 | default | False | 5.0000 | 361,689 | 480,492 |
| 2016 | tight | False | 5.0000 | 414,760 | 480,492 |
| 2017 | default | False | 4.8823 | 249,640 | 270,949 |
| 2017 | tight | False | 1.7301 | 210,701 | 218,252 |
| 2018 | default | False | 3.0507 | 281,174 | 283,264 |
| 2018 | tight | False | 2.9976 | 215,389 | 217,442 |
| 2019 | default | False | 5.0000 | 259,835 | 322,309 |
| 2019 | tight | False | 5.0000 | 195,296 | 263,902 |

## 5. Per-year realized-profit delta (Rs): OURS / MODEL_B minus each baseline

Four paired years cannot support a significance test (smallest attainable two-sided sign or Wilcoxon p at n=4 is 0.125), so no p-values are reported; each year's delta is shown.

| scenario | challenger | vs | 2016 | 2017 | 2018 | 2019 | mean | years won |
|---|---|---|---|---|---|---|---|---|
| default | OURS | B1 | -17,167 | +31,094 | +69,435 | -78,202 | +1,290 | 2/4 |
| default | OURS | B1_SCALED | -17,167 | +31,094 | +69,435 | -78,202 | +1,290 | 2/4 |
| default | OURS | B2 | -13,539 | -60,187 | -79,277 | -76,260 | -57,316 | 0/4 |
| default | OURS | B3 | +21,956 | -10,581 | +42,839 | -12,485 | +10,432 | 2/4 |
| default | MODEL_B | B1 | +71,860 | +53,249 | +72,964 | -78,306 | +29,942 | 3/4 |
| default | MODEL_B | B1_SCALED | +71,860 | +53,249 | +72,964 | -78,306 | +29,942 | 3/4 |
| default | MODEL_B | B2 | +75,488 | -38,032 | -75,748 | -76,364 | -28,664 | 1/4 |
| default | MODEL_B | B3 | +110,982 | +11,573 | +46,368 | -12,589 | +39,084 | 3/4 |
| tight | OURS | B1 | -23,735 | -3,680 | +23,238 | -111,159 | -28,834 | 1/4 |
| tight | OURS | B1_SCALED | +82,552 | +40,340 | +71,679 | -9,810 | +46,190 | 3/4 |
| tight | OURS | B2 | -73,177 | -56,021 | -59,689 | -44,679 | -58,392 | 0/4 |
| tight | OURS | B3 | +15,388 | -45,355 | -3,358 | - | -11,108 | 1/3 |
| tight | MODEL_B | B1 | -50,631 | +6,877 | +30,360 | -113,740 | -31,784 | 2/4 |
| tight | MODEL_B | B1_SCALED | +55,656 | +50,897 | +78,801 | -12,392 | +43,240 | 3/4 |
| tight | MODEL_B | B2 | -100,074 | -45,464 | -52,567 | -47,260 | -61,342 | 0/4 |
| tight | MODEL_B | B3 | -11,509 | -34,798 | +3,764 | - | -14,181 | 1/3 |
