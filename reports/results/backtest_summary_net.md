# Backtest fairness/water-matched-oracle summary, NET IRRIGATION water basis (Phase 8)

Reruns Phase 7.1's fairness metrics (B1_SCALED, profit per 1,000 m3 of water, capture_ratio_w vs the water-matched oracle ORACLE_W) with every params_df built under water_basis="net_irrigation" instead of the original FAO TM3 total-need basis -- see docs/water.md and reports/results/water_basis_comparison.md for the interpretation.

## Win summary (per-year win rate + mean capture_ratio_w + mean profit/1000m3 of NET irrigation water)

| scenario | strategy | n_years | win_count_vs_b1 | win_count_vs_b1_scaled | mean_capture_ratio_w | mean_profit_per_1000m3 |
|---|---|---|---|---|---|---|
| default | B1 | 4 | - | - | 0.531 | 5604.532 |
| default | B1_SCALED | 4 | - | - | 0.531 | 5604.532 |
| default | B2 | 4 | 3.000 | 3.000 | 0.820 | 8438.275 |
| default | B3 | 4 | 2.000 | 2.000 | 0.818 | 20486.149 |
| default | MODEL_B | 4 | 2.000 | 2.000 | 0.647 | 9858.612 |
| default | ORACLE | 4 | - | - | 1.000 | 13707.942 |
| default | OURS | 4 | 3.000 | 3.000 | 0.778 | 14296.810 |
| tight | B1 | 4 | - | - | 0.531 | 5604.532 |
| tight | B1_SCALED | 4 | - | - | 0.402 | 5604.532 |
| tight | B2 | 4 | 3.000 | 3.000 | 0.796 | 10945.128 |
| tight | B3 | 4 | 2.000 | 3.000 | 0.818 | 20486.149 |
| tight | MODEL_B | 4 | 2.000 | 3.000 | 0.642 | 12325.882 |
| tight | ORACLE | 4 | - | - | 1.000 | 15540.636 |
| tight | OURS | 4 | 2.000 | 4.000 | 0.718 | 17720.662 |

## Budget-level capture ratio (total realized profit / ORACLE's total realized profit)

| strategy | default | tight |
|---|---|---|
| B1 | 0.540 | 0.573 |
| B1_SCALED | 0.540 | 0.401 |
| B2 | 0.815 | 0.786 |
| B3 | 0.487 | 0.516 |
| MODEL_B | 0.527 | 0.505 |
| ORACLE | 1.000 | 1.000 |
| OURS | 0.683 | 0.638 |
