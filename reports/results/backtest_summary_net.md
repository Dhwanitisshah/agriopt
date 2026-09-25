# Backtest fairness/water-matched-oracle summary, NET IRRIGATION water basis (Phase 8)

Reruns Phase 7.1's fairness metrics (B1_SCALED, profit per 1,000 m3 of water, capture_ratio_w vs the water-matched oracle ORACLE_W) with every params_df built under water_basis="net_irrigation" instead of the original FAO TM3 total-need basis -- see docs/water.md and reports/results/water_basis_comparison.md for the interpretation.

## Win summary (per-year win rate + mean capture_ratio_w + mean profit/1000m3 of NET irrigation water)

| scenario | strategy | n_years | win_count_vs_b1 | win_count_vs_b1_scaled | mean_capture_ratio_w | mean_profit_per_1000m3 |
|---|---|---|---|---|---|---|
| default | B1 | 4 | - | - | 0.576 | 15464.283 |
| default | B1_SCALED | 4 | - | - | 0.576 | 15464.283 |
| default | B2 | 4 | 4.000 | 4.000 | 0.954 | 25512.065 |
| default | B3 | 4 | 3.000 | 3.000 | 0.954 | 205430.347 |
| default | MODEL_B | 4 | 4.000 | 4.000 | 0.819 | 31496.269 |
| default | ORACLE | 4 | - | - | 1.000 | 26806.778 |
| default | OURS | 4 | 4.000 | 4.000 | 0.920 | 35329.910 |
| tight | B1 | 4 | - | - | 0.576 | 15464.283 |
| tight | B1_SCALED | 4 | - | - | 0.461 | 15464.283 |
| tight | B2 | 4 | 4.000 | 4.000 | 0.948 | 31668.315 |
| tight | B3 | 4 | 3.000 | 4.000 | 0.954 | 205430.347 |
| tight | MODEL_B | 4 | 2.000 | 4.000 | 0.796 | 40899.716 |
| tight | ORACLE | 4 | - | - | 1.000 | 33550.016 |
| tight | OURS | 4 | 3.000 | 4.000 | 0.872 | 47444.753 |

## Budget-level capture ratio (total realized profit / ORACLE's total realized profit)

| strategy | default | tight |
|---|---|---|
| B1 | 0.577 | 0.658 |
| B1_SCALED | 0.577 | 0.461 |
| B2 | 0.951 | 0.943 |
| B3 | 0.573 | 0.654 |
| MODEL_B | 0.671 | 0.676 |
| ORACLE | 1.000 | 1.000 |
| OURS | 0.761 | 0.739 |
