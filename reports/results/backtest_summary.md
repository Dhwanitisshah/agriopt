# Decision backtest 2016-2020: summary (Phase 7)

Maharashtra's yield_clean.parquet has no rows at all for year 2020 (any crop) -- verified against the raw data, not a code bug. Every 'realized' figure below (total/mean/worst realized profit, capture ratio, win count, forecast gap, sign/Wilcoxon tests) is therefore computed over **2016-2019 (n=4)**, not the full 5 decision years. Planned allocations and water/fert usage ARE reported for 2020 (planning only needs data <= 2019), just not scored against an outcome that doesn't exist. See `missing_realized_crops` in backtest_rows.csv and the per-year note below.

- year 2020: realized data missing for crops ['rice', 'wheat', 'jowar', 'soybean', 'cotton', 'sugarcane', 'tur', 'maize'] (ALL crops).

## Per-strategy summary, by water scenario

| scenario | strategy | n_years_realized | total_realized_profit | mean_realized_profit | worst_year_realized_profit | capture_ratio_vs_oracle | win_count_vs_b1 | mean_water_saved_vs_b1_m3 | mean_signed_forecast_gap_rs |
|---|---|---|---|---|---|---|---|---|---|
| default | B1 | 4 | 1,679,251 | 419,813 | 352,051 | 0.614 | - | 0.000 | 26,617 |
| default | B2 | 4 | 2,734,239 | 683,560 | 619,069 | 1.000 | 4.000 | 0.000 | 42,502 |
| default | B3 | 4 | 1,744,192 | 436,048 | 368,647 | 0.638 | 4.000 | 28,491 | 42,852 |
| default | OURS | 4 | 1,944,240 | 486,060 | 425,264 | 0.711 | 4.000 | 20,730 | 29,266 |
| default | MODEL_B | 4 | 1,857,304 | 464,326 | 405,830 | 0.679 | 3.000 | 20,604 | 32,871 |
| default | ORACLE | 4 | 2,734,239 | 683,560 | 619,069 | 1.000 | 4.000 | - | 0.000 |
| tight | B1 | 4 | 1,679,251 | 419,813 | 352,051 | 0.860 | - | 0.000 | 26,617 |
| tight | B2 | 4 | 1,952,282 | 488,070 | 430,893 | 1.000 | 4.000 | 22,323 | 42,455 |
| tight | B3 | 4 | 1,744,192 | 436,048 | 368,647 | 0.893 | 4.000 | 28,491 | 42,852 |
| tight | OURS | 4 | 1,418,556 | 354,639 | 290,033 | 0.727 | 0.000 | 36,188 | 32,296 |
| tight | MODEL_B | 4 | 1,284,269 | 321,067 | 285,333 | 0.658 | 0.000 | 35,359 | 14,160 |
| tight | ORACLE | 4 | 1,952,282 | 488,070 | 430,893 | 1.000 | 4.000 | - | 0.000 |

`mean_signed_forecast_gap_rs` = mean(realized - planned) profit -- positive means plans came in MORE profitable than forecast (underpromised), negative means they were overoptimistic. Signed, not absolute, because 'how optimistic was the plan' is the question being asked (absolute error would only say how big the miss was, not which direction).

## Paired tests vs B1 (realized profit), per scenario

**n=4 (or fewer) paired years per scenario -- statistical power is essentially nonexistent at this sample size. These p-values are exploratory/directional signals only, NOT evidence of a significant effect in either direction. Do not read a low p-value here as proof AgriOpt beats B1, or a high one as proof it doesn't.**

| scenario | challenger | n_years | n_wins_vs_b1 | sign_test_p | wilcoxon_stat | wilcoxon_p | mean_diff_rs |
|---|---|---|---|---|---|---|---|
| default | OURS | 4 | 4 | 0.1250 | 0.0000 | 0.1250 | 66247.2750 |
| default | MODEL_B | 4 | 3 | 0.6250 | 1.0000 | 0.2500 | 44513.1346 |
| tight | OURS | 4 | 0 | 0.1250 | 0.0000 | 0.1250 | -65173.7794 |
| tight | MODEL_B | 4 | 0 | 0.1250 | 0.0000 | 0.1250 | -98745.5130 |
