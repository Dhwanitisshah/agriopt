# Price model significance: Diebold-Mariano tests (Phase 9 / E2.3)

HLN-corrected Diebold-Mariano test, absolute-error loss (d_t = |e_naive| - |e_other|; positive dm_stat means the OTHER model has smaller average absolute error than Naive), HAC variance with h-1 lags. p < 0.05 is treated as significant. See `agriopt.stats.dm_test` for the implementation.

## Pooled (across all 7 PRICE_CROPS)

| horizon | comparison | n | dm_stat | p_value | verdict |
|---|---|---|---|---|---|
| 3 | Naive vs XGBoost | 315 | -1.911 | 0.0569 | No significant difference between Naive and XGBoost at h=3 (p=0.057). |
| 3 | Naive vs Seasonal-Naive | 315 | -4.731 | 0.0000 | Naive significantly more accurate than Seasonal-Naive at h=3, p=0.000. |
| 6 | Naive vs XGBoost | 294 | -2.173 | 0.0306 | Naive significantly more accurate than XGBoost at h=6, p=0.031. |
| 6 | Naive vs Seasonal-Naive | 294 | -3.352 | 0.0009 | Naive significantly more accurate than Seasonal-Naive at h=6, p=0.001. |
| 12 | Naive vs XGBoost | 252 | -2.340 | 0.0201 | Naive significantly more accurate than XGBoost at h=12, p=0.020. |
| 12 | Naive vs Seasonal-Naive | 252 | 0.000 | 1.0000 | No significant difference between Naive and Seasonal-Naive at h=12 (p=1.000). |

## Per-crop

| horizon | crop | comparison | n | dm_stat | p_value | verdict |
|---|---|---|---|---|---|---|
| 3 | rice | Naive vs XGBoost | 45 | -1.685 | 0.0992 | No significant difference between Naive and XGBoost at h=3 (p=0.099). |
| 3 | wheat | Naive vs XGBoost | 45 | -1.903 | 0.0636 | No significant difference between Naive and XGBoost at h=3 (p=0.064). |
| 3 | jowar | Naive vs XGBoost | 45 | -1.804 | 0.0780 | No significant difference between Naive and XGBoost at h=3 (p=0.078). |
| 3 | soybean | Naive vs XGBoost | 45 | -0.896 | 0.3753 | No significant difference between Naive and XGBoost at h=3 (p=0.375). |
| 3 | cotton | Naive vs XGBoost | 45 | -1.169 | 0.2488 | No significant difference between Naive and XGBoost at h=3 (p=0.249). |
| 3 | tur | Naive vs XGBoost | 45 | -0.638 | 0.5269 | No significant difference between Naive and XGBoost at h=3 (p=0.527). |
| 3 | maize | Naive vs XGBoost | 45 | 0.366 | 0.7163 | No significant difference between Naive and XGBoost at h=3 (p=0.716). |
| 3 | rice | Naive vs Seasonal-Naive | 45 | -1.614 | 0.1137 | No significant difference between Naive and Seasonal-Naive at h=3 (p=0.114). |
| 3 | wheat | Naive vs Seasonal-Naive | 45 | -1.828 | 0.0744 | No significant difference between Naive and Seasonal-Naive at h=3 (p=0.074). |
| 3 | jowar | Naive vs Seasonal-Naive | 45 | -2.755 | 0.0085 | Naive significantly more accurate than Seasonal-Naive at h=3, p=0.008. |
| 3 | soybean | Naive vs Seasonal-Naive | 45 | -3.200 | 0.0025 | Naive significantly more accurate than Seasonal-Naive at h=3, p=0.003. |
| 3 | cotton | Naive vs Seasonal-Naive | 45 | -2.263 | 0.0286 | Naive significantly more accurate than Seasonal-Naive at h=3, p=0.029. |
| 3 | tur | Naive vs Seasonal-Naive | 45 | -2.722 | 0.0093 | Naive significantly more accurate than Seasonal-Naive at h=3, p=0.009. |
| 3 | maize | Naive vs Seasonal-Naive | 45 | -1.455 | 0.1528 | No significant difference between Naive and Seasonal-Naive at h=3 (p=0.153). |
| 6 | rice | Naive vs XGBoost | 42 | -0.629 | 0.5328 | No significant difference between Naive and XGBoost at h=6 (p=0.533). |
| 6 | wheat | Naive vs XGBoost | 42 | -0.477 | 0.6357 | No significant difference between Naive and XGBoost at h=6 (p=0.636). |
| 6 | jowar | Naive vs XGBoost | 42 | -2.307 | 0.0262 | Naive significantly more accurate than XGBoost at h=6, p=0.026. |
| 6 | soybean | Naive vs XGBoost | 42 | -1.470 | 0.1492 | No significant difference between Naive and XGBoost at h=6 (p=0.149). |
| 6 | cotton | Naive vs XGBoost | 42 | -1.155 | 0.2549 | No significant difference between Naive and XGBoost at h=6 (p=0.255). |
| 6 | tur | Naive vs XGBoost | 42 | -0.978 | 0.3339 | No significant difference between Naive and XGBoost at h=6 (p=0.334). |
| 6 | maize | Naive vs XGBoost | 42 | -1.622 | 0.1124 | No significant difference between Naive and XGBoost at h=6 (p=0.112). |
| 6 | rice | Naive vs Seasonal-Naive | 42 | -1.075 | 0.2886 | No significant difference between Naive and Seasonal-Naive at h=6 (p=0.289). |
| 6 | wheat | Naive vs Seasonal-Naive | 42 | -0.578 | 0.5661 | No significant difference between Naive and Seasonal-Naive at h=6 (p=0.566). |
| 6 | jowar | Naive vs Seasonal-Naive | 42 | -1.650 | 0.1065 | No significant difference between Naive and Seasonal-Naive at h=6 (p=0.107). |
| 6 | soybean | Naive vs Seasonal-Naive | 42 | -2.543 | 0.0149 | Naive significantly more accurate than Seasonal-Naive at h=6, p=0.015. |
| 6 | cotton | Naive vs Seasonal-Naive | 42 | -1.756 | 0.0866 | No significant difference between Naive and Seasonal-Naive at h=6 (p=0.087). |
| 6 | tur | Naive vs Seasonal-Naive | 42 | -1.681 | 0.1003 | No significant difference between Naive and Seasonal-Naive at h=6 (p=0.100). |
| 6 | maize | Naive vs Seasonal-Naive | 42 | -1.171 | 0.2484 | No significant difference between Naive and Seasonal-Naive at h=6 (p=0.248). |
| 12 | rice | Naive vs XGBoost | 36 | -2.032 | 0.0498 | Naive significantly more accurate than XGBoost at h=12, p=0.050. |
| 12 | wheat | Naive vs XGBoost | 36 | -2.147 | 0.0388 | Naive significantly more accurate than XGBoost at h=12, p=0.039. |
| 12 | jowar | Naive vs XGBoost | 36 | 0.285 | 0.7773 | No significant difference between Naive and XGBoost at h=12 (p=0.777). |
| 12 | soybean | Naive vs XGBoost | 36 | -0.530 | 0.5995 | No significant difference between Naive and XGBoost at h=12 (p=0.600). |
| 12 | cotton | Naive vs XGBoost | 36 | -3.479 | 0.0014 | Naive significantly more accurate than XGBoost at h=12, p=0.001. |
| 12 | tur | Naive vs XGBoost | 36 | -0.922 | 0.3626 | No significant difference between Naive and XGBoost at h=12 (p=0.363). |
| 12 | maize | Naive vs XGBoost | 36 | -2.414 | 0.0212 | Naive significantly more accurate than XGBoost at h=12, p=0.021. |
| 12 | rice | Naive vs Seasonal-Naive | 36 | 0.000 | 1.0000 | No significant difference between Naive and Seasonal-Naive at h=12 (p=1.000). |
| 12 | wheat | Naive vs Seasonal-Naive | 36 | 0.000 | 1.0000 | No significant difference between Naive and Seasonal-Naive at h=12 (p=1.000). |
| 12 | jowar | Naive vs Seasonal-Naive | 36 | 0.000 | 1.0000 | No significant difference between Naive and Seasonal-Naive at h=12 (p=1.000). |
| 12 | soybean | Naive vs Seasonal-Naive | 36 | 0.000 | 1.0000 | No significant difference between Naive and Seasonal-Naive at h=12 (p=1.000). |
| 12 | cotton | Naive vs Seasonal-Naive | 36 | 0.000 | 1.0000 | No significant difference between Naive and Seasonal-Naive at h=12 (p=1.000). |
| 12 | tur | Naive vs Seasonal-Naive | 36 | 0.000 | 1.0000 | No significant difference between Naive and Seasonal-Naive at h=12 (p=1.000). |
| 12 | maize | Naive vs Seasonal-Naive | 36 | 0.000 | 1.0000 | No significant difference between Naive and Seasonal-Naive at h=12 (p=1.000). |

## Findings

- 4/6 pooled comparisons are significant at p<0.05.
- Naive vs XGBoost (pooled): significant at horizons [6, 12].
- Naive vs Seasonal-Naive (pooled): significant at horizons [3, 6].
- Per-crop tests have far fewer observations than pooled (n per crop is the number of backtest origins, not origins x crops), so per-crop p-values are noisier / less powered -- read the pooled row as the headline, per-crop rows as detail.
