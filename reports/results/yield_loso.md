# Leave-one-state-out generalization (Phase 9 / E1.6, extends E1.3)

Top 10 states by row count in the full (all-India) yield dataset: Karnataka, Andhra Pradesh, West Bengal, Chhattisgarh, Bihar, Madhya Pradesh, Uttar Pradesh, Tamil Nadu, Gujarat, Maharashtra. For each: RandomForest (Phase 1 protocol, hyperparameters re-derived once via `tune_rf` and shared across all 10 runs -- see ASSUMPTION in the script docstring) trained on year<=2015, either WITH the held-out state's rows (in-state-included, the normal Phase 1 model) or WITHOUT them at all (out-of-state-trained, LOSO) -- tested on the held-out state's own 2016-2020 rows in both cases.

| state | n test rows | MAE in | MAE out | degradation % | MAPE in | MAPE out | MAPE degradation % | crop Jaccard vs other states |
|---|---|---|---|---|---|---|---|---|
| Tamil Nadu | 218 | 37.068 | 34.190 | -7.8% | 48.5 | 87.4 | +80.0% | 0.818 |
| Bihar | 169 | 1.242 | 1.410 | +13.5% | 32.7 | 42.4 | +29.7% | 0.764 |
| Andhra Pradesh | 276 | 40.566 | 58.511 | +44.2% | 46.3 | 75.9 | +63.9% | 0.836 |
| Uttar Pradesh | 164 | 0.918 | 1.331 | +44.9% | 21.6 | 43.1 | +100.0% | 0.709 |
| Maharashtra | 152 | 0.506 | 0.750 | +48.4% | 34.4 | 79.6 | +131.0% | 0.545 |
| Madhya Pradesh | 160 | 2.108 | 3.562 | +69.0% | 33.6 | 112.2 | +234.1% | 0.818 |
| Gujarat | 160 | 0.955 | 2.854 | +198.7% | 19.6 | 36.8 | +87.6% | 0.564 |
| Karnataka | 276 | 12.327 | 65.203 | +428.9% | 43.1 | 118.2 | +174.4% | 0.818 |
| West Bengal | 190 | 8.916 | 67.952 | +662.1% | 15.0 | 34.7 | +131.8% | 0.764 |
| Chhattisgarh | 185 | 0.514 | 68.347 | +13200.7% | 46.2 | 197.8 | +328.4% | 0.782 |

## Findings

- Best-generalizing state (smallest MAE degradation when excluded): **Tamil Nadu** (-7.8%). Worst: **Chhattisgarh** (+13200.7%).
- Correlation between crop-mix Jaccard similarity (state vs pooled other 9 states) and MAE degradation: r=0.14 (no strong linear relationship in this small (n=10) sample -- read the scatter (yield_loso_crop_mix.png), not just r, given how few points there are).
- n=10 states is a small sample for a correlation claim -- same small-n caveat as the Phase 7 backtest and other n<20 comparisons in this repo; treat the sign/rough magnitude as suggestive, not a precise estimate.
- Maharashtra itself is included in this LOSO table (row above) and should read consistently with E1.3's Maharashtra in/out preview (yield_regional.md) -- both measure the same thing, this one across 10 states instead of just Maharashtra.
