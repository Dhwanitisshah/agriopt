# Decision backtest 2016-2020: summary (Phase 7)

Maharashtra's yield_clean.parquet has no rows at all for year 2020 (any crop) -- verified against the raw data, not a code bug. Every 'realized' figure below (total/mean/worst realized profit, capture ratio, win count, forecast gap, sign/Wilcoxon tests) is therefore computed over **2016-2019 (n=4)**, not the full 5 decision years. Planned allocations and water/fert usage ARE reported for 2020 (planning only needs data <= 2019), just not scored against an outcome that doesn't exist. See `missing_realized_crops` in backtest_rows.csv and the per-year note below.

- year 2020: realized data missing for crops ['rice', 'wheat', 'jowar', 'soybean', 'cotton', 'sugarcane', 'tur', 'maize'] (ALL crops).

## Per-strategy summary, by water scenario

| scenario | strategy | n_years_realized | total_realized_profit | mean_realized_profit | worst_year_realized_profit | capture_ratio_vs_oracle | win_count_vs_b1 | mean_water_saved_vs_b1_m3 | mean_signed_forecast_gap_rs |
|---|---|---|---|---|---|---|---|---|---|
| default | B1 | 4 | 648,901 | 162,225 | 94,332 | 0.554 | - | 0.000 | 26,572 |
| default | B2 | 4 | 1,025,134 | 256,284 | 192,911 | 0.875 | 4.000 | 0.000 | 27,391 |
| default | B3 | 4 | 673,257 | 168,314 | 93,289 | 0.575 | 2.000 | 33,423 | 32,661 |
| default | OURS | 4 | 803,877 | 200,969 | 151,565 | 0.686 | 3.000 | 21,780 | 32,720 |
| default | MODEL_B | 4 | 721,101 | 180,275 | 129,957 | 0.616 | 3.000 | 19,844 | 19,574 |
| default | ORACLE | 4 | 1,171,298 | 292,824 | 213,937 | 1.000 | 4.000 | - | 0.000 |
| tight | B1 | 4 | 648,901 | 162,225 | 94,332 | 0.707 | - | 0.000 | 26,572 |
| tight | B2 | 4 | 820,860 | 205,215 | 154,668 | 0.894 | 3.000 | 21,666 | 33,667 |
| tight | B3 | 4 | 673,257 | 168,314 | 93,289 | 0.733 | 2.000 | 33,423 | 32,661 |
| tight | OURS | 4 | 647,307 | 161,827 | 105,362 | 0.705 | 3.000 | 35,641 | 32,412 |
| tight | MODEL_B | 4 | 560,833 | 140,208 | 103,457 | 0.611 | 2.000 | 34,226 | 20,725 |
| tight | ORACLE | 4 | 918,304 | 229,576 | 165,687 | 1.000 | 4.000 | - | 0.000 |

`mean_signed_forecast_gap_rs` = mean(realized - planned) profit -- positive means plans came in MORE profitable than forecast (underpromised), negative means they were overoptimistic. Signed, not absolute, because 'how optimistic was the plan' is the question being asked (absolute error would only say how big the miss was, not which direction).

## Paired tests vs B1 (realized profit), per scenario

**n=4 (or fewer) paired years per scenario -- statistical power is essentially nonexistent at this sample size. These p-values are exploratory/directional signals only, NOT evidence of a significant effect in either direction. Do not read a low p-value here as proof AgriOpt beats B1, or a high one as proof it doesn't.**

| scenario | challenger | n_years | n_wins_vs_b1 | sign_test_p | wilcoxon_stat | wilcoxon_p | mean_diff_rs |
|---|---|---|---|---|---|---|---|
| default | OURS | 4 | 3 | 0.6250 | 1.0000 | 0.2500 | 38743.9994 |
| default | MODEL_B | 4 | 3 | 0.6250 | 2.0000 | 0.3750 | 18049.7849 |
| tight | OURS | 4 | 3 | 0.6250 | 4.0000 | 0.8750 | -398.6006 |
| tight | MODEL_B | 4 | 2 | 1.0000 | 3.0000 | 0.6250 | -22017.1123 |
