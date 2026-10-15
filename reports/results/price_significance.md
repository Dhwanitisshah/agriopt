# Price model significance: Diebold-Mariano tests (Phase 9 / E2.3)

HLN-corrected Diebold-Mariano test, absolute-error loss (d_t = |e_naive| - |e_other|; positive dm_stat means the OTHER model has smaller average absolute error than Naive), HAC variance with h-1 lags. p < 0.05 is treated as significant. See `agriopt.stats.dm_test` for the implementation.

## Panel (all 7 PRICE_CROPS, time-clustered; n = origin months)

`p_value` = HLN-corrected DM on the month-averaged loss differential (h-1 HAC lags); `p_boot` = moving-block bootstrap over months (block = max(h, 6)); `p_stacked` = the earlier test that stacked crops as if independent (shown only to quantify its overstatement; do not cite).

| horizon | comparison | months | stacked obs | dm_stat | p_value | p_boot | p_stacked | verdict |
|---|---|---|---|---|---|---|---|---|
| 3 | Naive vs XGBoost | 45 | 315 | -1.819 | 0.0758 | 0.0648 | 0.0583 | No significant difference between Naive and XGBoost at h=3 (p=0.076). |
| 3 | Naive vs Seasonal-Naive | 45 | 315 | -5.920 | 0.0000 | 0.0004 | 0.0000 | Naive significantly more accurate than Seasonal-Naive at h=3, p=0.000. |
| 6 | Naive vs XGBoost | 42 | 294 | -1.792 | 0.0805 | 0.0378 | 0.0348 | No significant difference between Naive and XGBoost at h=6 (p=0.080). |
| 6 | Naive vs Seasonal-Naive | 42 | 294 | -3.362 | 0.0017 | 0.0046 | 0.0009 | Naive significantly more accurate than Seasonal-Naive at h=6, p=0.002. |
| 12 | Naive vs XGBoost | 36 | 252 | -1.860 | 0.0713 | 0.1094 | 0.0304 | No significant difference between Naive and XGBoost at h=12 (p=0.071). |
| 12 | Naive vs Seasonal-Naive | 36 | 252 | 0.000 | 1.0000 | 1.0000 | 1.0000 | No significant difference between Naive and Seasonal-Naive at h=12 (p=1.000). |

## Per-crop

| horizon | crop | comparison | n | dm_stat | p_value | verdict |
|---|---|---|---|---|---|---|
| 3 | rice | Naive vs XGBoost | 45 | -2.073 | 0.0440 | Naive significantly more accurate than XGBoost at h=3, p=0.044. |
| 3 | wheat | Naive vs XGBoost | 45 | -1.831 | 0.0739 | No significant difference between Naive and XGBoost at h=3 (p=0.074). |
| 3 | jowar | Naive vs XGBoost | 45 | -1.449 | 0.1545 | No significant difference between Naive and XGBoost at h=3 (p=0.154). |
| 3 | soybean | Naive vs XGBoost | 45 | -0.642 | 0.5240 | No significant difference between Naive and XGBoost at h=3 (p=0.524). |
| 3 | cotton | Naive vs XGBoost | 45 | -1.360 | 0.1808 | No significant difference between Naive and XGBoost at h=3 (p=0.181). |
| 3 | tur | Naive vs XGBoost | 45 | -0.543 | 0.5898 | No significant difference between Naive and XGBoost at h=3 (p=0.590). |
| 3 | maize | Naive vs XGBoost | 45 | 0.662 | 0.5116 | No significant difference between Naive and XGBoost at h=3 (p=0.512). |
| 3 | rice | Naive vs Seasonal-Naive | 45 | -1.614 | 0.1137 | No significant difference between Naive and Seasonal-Naive at h=3 (p=0.114). |
| 3 | wheat | Naive vs Seasonal-Naive | 45 | -1.828 | 0.0744 | No significant difference between Naive and Seasonal-Naive at h=3 (p=0.074). |
| 3 | jowar | Naive vs Seasonal-Naive | 45 | -2.755 | 0.0085 | Naive significantly more accurate than Seasonal-Naive at h=3, p=0.008. |
| 3 | soybean | Naive vs Seasonal-Naive | 45 | -3.200 | 0.0025 | Naive significantly more accurate than Seasonal-Naive at h=3, p=0.003. |
| 3 | cotton | Naive vs Seasonal-Naive | 45 | -2.263 | 0.0286 | Naive significantly more accurate than Seasonal-Naive at h=3, p=0.029. |
| 3 | tur | Naive vs Seasonal-Naive | 45 | -2.722 | 0.0093 | Naive significantly more accurate than Seasonal-Naive at h=3, p=0.009. |
| 3 | maize | Naive vs Seasonal-Naive | 45 | -1.455 | 0.1528 | No significant difference between Naive and Seasonal-Naive at h=3 (p=0.153). |
| 6 | rice | Naive vs XGBoost | 42 | -0.581 | 0.5641 | No significant difference between Naive and XGBoost at h=6 (p=0.564). |
| 6 | wheat | Naive vs XGBoost | 42 | -0.381 | 0.7052 | No significant difference between Naive and XGBoost at h=6 (p=0.705). |
| 6 | jowar | Naive vs XGBoost | 42 | -1.152 | 0.2558 | No significant difference between Naive and XGBoost at h=6 (p=0.256). |
| 6 | soybean | Naive vs XGBoost | 42 | -1.190 | 0.2411 | No significant difference between Naive and XGBoost at h=6 (p=0.241). |
| 6 | cotton | Naive vs XGBoost | 42 | -1.356 | 0.1826 | No significant difference between Naive and XGBoost at h=6 (p=0.183). |
| 6 | tur | Naive vs XGBoost | 42 | -0.966 | 0.3395 | No significant difference between Naive and XGBoost at h=6 (p=0.340). |
| 6 | maize | Naive vs XGBoost | 42 | -1.929 | 0.0607 | No significant difference between Naive and XGBoost at h=6 (p=0.061). |
| 6 | rice | Naive vs Seasonal-Naive | 42 | -1.075 | 0.2886 | No significant difference between Naive and Seasonal-Naive at h=6 (p=0.289). |
| 6 | wheat | Naive vs Seasonal-Naive | 42 | -0.578 | 0.5661 | No significant difference between Naive and Seasonal-Naive at h=6 (p=0.566). |
| 6 | jowar | Naive vs Seasonal-Naive | 42 | -1.650 | 0.1065 | No significant difference between Naive and Seasonal-Naive at h=6 (p=0.107). |
| 6 | soybean | Naive vs Seasonal-Naive | 42 | -2.543 | 0.0149 | Naive significantly more accurate than Seasonal-Naive at h=6, p=0.015. |
| 6 | cotton | Naive vs Seasonal-Naive | 42 | -1.756 | 0.0866 | No significant difference between Naive and Seasonal-Naive at h=6 (p=0.087). |
| 6 | tur | Naive vs Seasonal-Naive | 42 | -1.681 | 0.1003 | No significant difference between Naive and Seasonal-Naive at h=6 (p=0.100). |
| 6 | maize | Naive vs Seasonal-Naive | 42 | -1.171 | 0.2484 | No significant difference between Naive and Seasonal-Naive at h=6 (p=0.248). |
| 12 | rice | Naive vs XGBoost | 36 | -2.160 | 0.0377 | Naive significantly more accurate than XGBoost at h=12, p=0.038. |
| 12 | wheat | Naive vs XGBoost | 36 | -2.889 | 0.0066 | Naive significantly more accurate than XGBoost at h=12, p=0.007. |
| 12 | jowar | Naive vs XGBoost | 36 | 0.409 | 0.6853 | No significant difference between Naive and XGBoost at h=12 (p=0.685). |
| 12 | soybean | Naive vs XGBoost | 36 | -0.404 | 0.6884 | No significant difference between Naive and XGBoost at h=12 (p=0.688). |
| 12 | cotton | Naive vs XGBoost | 36 | -3.274 | 0.0024 | Naive significantly more accurate than XGBoost at h=12, p=0.002. |
| 12 | tur | Naive vs XGBoost | 36 | -0.952 | 0.3475 | No significant difference between Naive and XGBoost at h=12 (p=0.347). |
| 12 | maize | Naive vs XGBoost | 36 | -3.026 | 0.0046 | Naive significantly more accurate than XGBoost at h=12, p=0.005. |
| 12 | rice | Naive vs Seasonal-Naive | 36 | 0.000 | 1.0000 | No significant difference between Naive and Seasonal-Naive at h=12 (p=1.000). |
| 12 | wheat | Naive vs Seasonal-Naive | 36 | 0.000 | 1.0000 | No significant difference between Naive and Seasonal-Naive at h=12 (p=1.000). |
| 12 | jowar | Naive vs Seasonal-Naive | 36 | 0.000 | 1.0000 | No significant difference between Naive and Seasonal-Naive at h=12 (p=1.000). |
| 12 | soybean | Naive vs Seasonal-Naive | 36 | 0.000 | 1.0000 | No significant difference between Naive and Seasonal-Naive at h=12 (p=1.000). |
| 12 | cotton | Naive vs Seasonal-Naive | 36 | 0.000 | 1.0000 | No significant difference between Naive and Seasonal-Naive at h=12 (p=1.000). |
| 12 | tur | Naive vs Seasonal-Naive | 36 | 0.000 | 1.0000 | No significant difference between Naive and Seasonal-Naive at h=12 (p=1.000). |
| 12 | maize | Naive vs Seasonal-Naive | 36 | 0.000 | 1.0000 | No significant difference between Naive and Seasonal-Naive at h=12 (p=1.000). |

## Findings

- 2/6 panel comparisons are significant at p<0.05 (2 also by the block bootstrap); the stacked test would have called 4/6 significant.
- Naive vs XGBoost (panel): significant at horizons none.
- Naive vs Seasonal-Naive (panel): significant at horizons [3, 6].
- The panel test's n is the number of origin MONTHS (one cluster each), so it is far less powered than the stacked test pretended to be; per-crop tests have the same n per crop but a single series, so they are noisier still -- read the panel row as the headline, per-crop rows as detail.
