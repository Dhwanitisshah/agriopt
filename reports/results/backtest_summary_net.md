# Backtest fairness/water-matched-oracle summary, NET IRRIGATION water basis (Phase 8)

Reruns Phase 7.1's fairness metrics (B1_SCALED, profit per 1,000 m3 of water, capture_ratio_w vs the water-matched oracle ORACLE_W) with every params_df built under water_basis="net_irrigation" instead of the original FAO TM3 total-need basis -- see docs/water.md and reports/results/water_basis_comparison.md for the interpretation.

## Win summary (per-year win rate + mean capture_ratio_w + mean profit/1000m3 of NET irrigation water)

| scenario | strategy | n_years | win_count_vs_b1 | win_count_vs_b1_scaled | mean_capture_ratio_w | mean_profit_per_1000m3 | mean_realized_profit |
|---|---|---|---|---|---|---|---|
| default | B1 | 4 | - | - | 0.673 | 4173.753 | 229478.567 |
| default | B1_SCALED | 4 | - | - | 0.673 | 4173.753 | 229478.567 |
| default | B2 | 4 | 4.000 | 4.000 | 0.875 | 5164.226 | 283740.787 |
| default | B3 | 4 | 1.000 | 1.000 | 0.839 | 12649.215 | 190462.463 |
| default | MODEL_B | 4 | 3.000 | 3.000 | 0.801 | 7717.897 | 229875.750 |
| default | ORACLE | 4 | - | - | 1.000 | 8066.970 | 331011.738 |
| default | OURS | 4 | 2.000 | 2.000 | 0.871 | 8933.081 | 240047.344 |
| tight | B1 | 4 | - | - | 0.673 | 4173.753 | 229478.567 |
| tight | B1_SCALED | 4 | - | - | 0.586 | 4818.836 | 185519.132 |
| tight | B2 | 4 | 3.000 | 3.000 | 0.827 | 6514.676 | 250746.102 |
| tight | B3 | 4 | 1.000 | 3.000 | 0.839 | 12649.215 | 190462.463 |
| tight | MODEL_B | 4 | 3.000 | 3.000 | 0.802 | 9128.136 | 200347.967 |
| tight | ORACLE | 4 | - | - | 1.000 | 9011.509 | 303971.128 |
| tight | OURS | 4 | 1.000 | 3.000 | 0.824 | 9478.456 | 209076.631 |

## Budget-level capture ratio (total realized profit / ORACLE's total realized profit)

| strategy | default | tight |
|---|---|---|
| B1 | 0.693 | 0.755 |
| B1_SCALED | 0.693 | 0.610 |
| B2 | 0.857 | 0.825 |
| B3 | 0.575 | 0.627 |
| MODEL_B | 0.694 | 0.659 |
| ORACLE | 1.000 | 1.000 |
| OURS | 0.725 | 0.688 |
