# Water basis comparison: total_need vs net_irrigation (Phase 8)

Compares headline numbers between the original (`total_need`, FAO TM3 crop water NEED) and the new (`net_irrigation`, need minus effective season rainfall -- see docs/water.md) water bases, at the `tight`/`current` water scenarios, market price.

## Water need vs net irrigation, per crop (mm)

| crop | water need (mm) | Peff normal (mm) | net irrigation normal (mm) | net irrigation dry (mm) |
|---|---|---|---|---|
| rice | 575.0 | 695.6 | 0.0 | 0.0 |
| wheat | 550.0 | 34.2 | 515.8 | 546.6 |
| jowar | 550.0 | 34.2 | 515.8 | 546.6 |
| soybean | 575.0 | 695.6 | 0.0 | 0.0 |
| cotton | 1000.0 | 720.2 | 279.8 | 382.7 |
| sugarcane | 2000.0 | 753.1 | 1246.9 | 1374.8 |
| tur | 400.0 | 720.2 | 0.0 | 0.0 |
| maize | 650.0 | 695.6 | 0.0 | 35.3 |

## E3 strategies: profit & water, tight/current x market (total_need vs net_irrigation)

| water | strategy | profit (total_need) | profit (net_irrigation) | water_m3 (total_need) | water_m3 (net_irrigation) |
|---|---|---|---|---|---|
| tight | B1 | 166259 | 166259 | 74274 | 25980 |
| tight | B2 | 298892 | 349191 | 51992 | 18186 |
| tight | B3 | 166259 | 166259 | 31586 | 0 |
| tight | OURS | 186715 | 247837 | 36372 | 10348 |
| current | B1 | 166259 | 166259 | 74274 | 25980 |
| current | B2 | 443722 | 423747 | 74274 | 25980 |
| current | B3 | 166259 | 166259 | 31586 | 0 |
| current | OURS | 291925 | 305166 | 52242 | 15122 |

## Backtest: win rate / capture_ratio_w / profit-per-1000m3, net irrigation basis

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

## Findings

- Rainfed kharif crops (rice, soybean, tur, maize) drop to 0mm net irrigation under normal monsoon rainfall (from their full FAO TM3 need) -- monsoon rainfall alone covers essentially all of their season water need, confirmed by the numbers above, not just assumed.
- Rabi crops (wheat, jowar) barely benefit: net irrigation (516mm) is still 94% of their total need (550mm) -- the Nov-Mar dry season provides almost no effective rainfall relief in this dataset.
- Sugarcane's net irrigation need (1247mm) covers 62% of its total need (2000mm) -- LOWER than wheat/jowar's 94%, since sugarcane's whole-year season captures some monsoon-month rainfall that a pure-Rabi crop never sees. Its irrigation burden does not exceed total need (by construction) but remains the largest of any crop in absolute m3/ha under BOTH bases -- see docs/water.md section 6 for the full numbers.
- B1 (current mix)'s own water footprint changes by -65.0% moving from total_need to net_irrigation water -- since B1's crop mix is fixed, this change is driven entirely by how much of its existing crops' water need monsoon rainfall already covers.
- All `_net` outputs (optim_strategies_net.*, risk_strategies_net.*, backtest_summary_net.md, backtest_fairness_net.csv, backtest_rows_net.csv) are NEW files -- no Phase 1-7.1 output was modified (verified: git status shows only new files added by this phase, plus the additive water_basis parameters).
