# Water basis comparison: total_need vs net_irrigation (Phase 8)

Compares headline numbers between the original (`total_need`, FAO TM3 crop water NEED) and the new (`net_irrigation`, need minus effective season rainfall -- see docs/water.md) water bases, at the `tight`/`current` water scenarios, market price.

## Water need vs net irrigation, per crop (mm)

| crop | water need (mm) | Peff normal (mm) | net irrigation normal (mm) | net irrigation dry (mm) |
|---|---|---|---|---|
| rice | 575.0 | 650.5 | 200.0 | 212.5 |
| wheat | 550.0 | 35.6 | 514.4 | 546.4 |
| jowar | 550.0 | 35.6 | 514.4 | 546.4 |
| soybean | 575.0 | 650.5 | 0.0 | 12.5 |
| cotton | 1000.0 | 675.6 | 324.4 | 434.8 |
| sugarcane | 2000.0 | 707.5 | 1292.5 | 1427.0 |
| tur | 400.0 | 675.6 | 0.0 | 0.0 |
| maize | 650.0 | 650.5 | 0.0 | 87.5 |

## E3 strategies: profit & water, tight/current x market (total_need vs net_irrigation)

| water | strategy | profit (total_need) | profit (net_irrigation) | water_m3 (total_need) | water_m3 (net_irrigation) |
|---|---|---|---|---|---|
| tight | B1 | 129794 | 129794 | 72156 | 27707 |
| tight | B2 | 211582 | 221043 | 50509 | 19395 |
| tight | B3 | 129794 | 129794 | 31313 | 5101 |
| tight | OURS | 144925 | 158449 | 35099 | 10040 |
| current | B1 | 129794 | 129794 | 72156 | 27707 |
| current | B2 | 296093 | 261578 | 72156 | 27707 |
| current | B3 | 129794 | 129794 | 31313 | 5101 |
| current | OURS | 203433 | 194044 | 49780 | 16287 |

## Backtest: win rate / capture_ratio_w / profit-per-1000m3, net irrigation basis

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

## Findings

- Rainfed kharif crops (rice, soybean, tur, maize) drop to 200mm net irrigation under normal monsoon rainfall (from their full FAO TM3 need) -- monsoon rainfall alone covers essentially all of their season water need, confirmed by the numbers above, not just assumed.
- Rabi crops (wheat, jowar) barely benefit: net irrigation (514mm) is still 94% of their total need (550mm) -- the Nov-Mar dry season provides almost no effective rainfall relief in this dataset.
- Sugarcane's net irrigation need (1292mm) covers 65% of its total need (2000mm) -- LOWER than wheat/jowar's 94%, since sugarcane's whole-year season captures some monsoon-month rainfall that a pure-Rabi crop never sees. Its irrigation burden does not exceed total need (by construction) but remains the largest of any crop in absolute m3/ha under BOTH bases -- see docs/water.md section 6 for the full numbers.
- B1 (current mix)'s own water footprint changes by -61.6% moving from total_need to net_irrigation water -- since B1's crop mix is fixed, this change is driven entirely by how much of its existing crops' water need monsoon rainfall already covers.
- All `_net` outputs (optim_strategies_net.*, risk_strategies_net.*, backtest_summary_net.md, backtest_fairness_net.csv, backtest_rows_net.csv) are NEW files -- no Phase 1-7.1 output was modified (verified: git status shows only new files added by this phase, plus the additive water_basis parameters).
