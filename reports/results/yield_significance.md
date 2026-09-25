# Yield model significance (Phase 9 / E1.4)

Maharashtra test set (year >= 2016), n=152 rows. Models refit on year<=2015.

## Wilcoxon signed-rank test on absolute errors (paired by test row)

| comparison | n | mean abs-err diff | statistic | p-value | verdict |
|---|---|---|---|---|---|
| RandomForest vs XGBoost | 152 | -0.1481 | 4403.50 | 0.0095 | RandomForest has significantly lower absolute error than XGBoost (p=0.009). |
| RandomForest vs Baseline-Mean | 152 | -2.1607 | 5420.00 | 0.4686 | No significant difference between RandomForest and Baseline-Mean (p=0.469). |
| RandomForest vs Ridge | 152 | -0.8766 | 2511.00 | 0.0000 | RandomForest has significantly lower absolute error than Ridge (p=0.000). |

## Bootstrap 95% CI for MAE (2000 resamples, seed=42)

| model | MAE | 95% CI low | 95% CI high |
|---|---|---|---|
| RandomForest | 0.5058 | 0.2192 | 1.0256 |
| XGBoost | 0.6539 | 0.3291 | 1.1842 |
| Ridge | 1.3823 | 0.5739 | 2.3925 |
| Baseline-Mean | 2.6665 | 0.8358 | 4.8686 |

## Findings

- 2/3 RF-vs-X comparisons are significant at p<0.05.
- RandomForest has significantly lower absolute error than XGBoost (p=0.009).
- No significant difference between RandomForest and Baseline-Mean (p=0.469).
- RandomForest has significantly lower absolute error than Ridge (p=0.000).
- n=152 Maharashtra test rows -- small-sample caveat applies (same spirit as the Phase 7 backtest's n=4/5-year caveat): a handful of crop-years dominate the paired differences.
