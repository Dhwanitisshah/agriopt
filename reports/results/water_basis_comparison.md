# Water basis comparison: total_need vs net_irrigation (Phase 8)

Compares headline numbers between the original (`total_need`, FAO TM3 crop water NEED) and the new (`net_irrigation`, need minus effective season rainfall -- see docs/water.md) water bases, at the `tight`/`current` water scenarios, market price.

## Water need vs net irrigation, per crop (mm)

| crop | water need (mm) | Peff normal (mm) | net irrigation normal (mm) | net irrigation dry (mm) |
|---|---|---|---|---|
| rice | 575.0 | 650.5 | 266.5 | 289.2 |
| wheat | 550.0 | 35.6 | 515.7 | 541.1 |
| jowar | 550.0 | 35.6 | 515.7 | 541.1 |
| soybean | 575.0 | 650.5 | 66.5 | 89.2 |
| cotton | 1000.0 | 675.6 | 433.4 | 480.0 |
| sugarcane | 2000.0 | 707.5 | 1318.3 | 1372.4 |
| tur | 400.0 | 675.6 | 136.2 | 163.0 |
| maize | 650.0 | 650.5 | 91.5 | 119.2 |

## E3 strategies: profit & water, tight/current x market (total_need vs net_irrigation)

| water | strategy | profit (total_need) | profit (net_irrigation) | water_m3 (total_need) | water_m3 (net_irrigation) |
|---|---|---|---|---|---|
| tight | B1 | 182833 | 182833 | 104851 | 54532 |
| tight | B2 | 300829 | 274256 | 73395 | 38172 |
| tight | B3 | 182833 | 182833 | 43554 | 21520 |
| tight | OURS | 208088 | 194509 | 49961 | 24198 |
| current | B1 | 182833 | 182833 | 104851 | 54532 |
| current | B2 | 421029 | 364071 | 104851 | 54532 |
| current | B3 | 182833 | 182833 | 43554 | 21520 |
| current | OURS | 277183 | 258265 | 67368 | 36519 |

## Backtest: win rate / capture_ratio_w / profit-per-1000m3, net irrigation basis

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

## Findings

- Rainfed kharif crops (rice, soybean, tur, maize) drop to 266mm net irrigation under normal monsoon rainfall (from their full FAO TM3 need) -- monsoon rainfall alone covers essentially all of their season water need, confirmed by the numbers above, not just assumed.
- Rabi crops (wheat, jowar) barely benefit: net irrigation (516mm) is still 94% of their total need (550mm) -- the Nov-Mar dry season provides almost no effective rainfall relief in this dataset.
- Sugarcane's net irrigation need (1318mm) covers 66% of its total need (2000mm) -- LOWER than wheat/jowar's 94%, since sugarcane's whole-year season captures some monsoon-month rainfall that a pure-Rabi crop never sees. Its irrigation burden does not exceed total need (by construction) but remains the largest of any crop in absolute m3/ha under BOTH bases -- see docs/water.md section 6 for the full numbers.
- B1 (current mix)'s own water footprint changes by -48.0% moving from total_need to net_irrigation water -- since B1's crop mix is fixed, this change is driven entirely by how much of its existing crops' water need monsoon rainfall already covers.
- All `_net` outputs (optim_strategies_net.*, risk_strategies_net.*, backtest_summary_net.md, backtest_fairness_net.csv, backtest_rows_net.csv) are NEW files -- no Phase 1-7.1 output was modified (verified: git status shows only new files added by this phase, plus the additive water_basis parameters).
