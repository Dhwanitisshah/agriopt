# Decision backtest 2016-2020: summary (Phase 7)

Maharashtra's yield_clean.parquet has no rows at all for year 2020 (any crop) -- verified against the raw data, not a code bug. Every 'realized' figure below (total/mean/worst realized profit, capture ratio, win count, forecast gap, per-year deltas) is therefore computed over **2016-2019 (n=4)**, not the full 5 decision years. Planned allocations and water/fert usage ARE reported for 2020 (planning only needs data <= 2019), just not scored against an outcome that doesn't exist. See `missing_realized_crops` in backtest_rows.csv and the per-year note below.

- year 2020: realized data missing for crops ['rice', 'wheat', 'jowar', 'soybean', 'cotton', 'sugarcane', 'tur', 'maize'] (ALL crops).

## Per-strategy summary, by water scenario

| scenario | strategy | n_years_realized | total_realized_profit | mean_realized_profit | worst_year_realized_profit | capture_ratio_vs_oracle | win_count_vs_b1 | mean_water_saved_vs_b1_m3 | mean_signed_forecast_gap_rs |
|---|---|---|---|---|---|---|---|---|---|
| default | B1 | 4 | 917,914 | 229,479 | 132,462 | 0.676 | - | 0.000 | 38,800 |
| default | B2 | 4 | 1,152,338 | 288,084 | 249,640 | 0.849 | 2.000 | -0.000 | 8,906 |
| default | B3 | 4 | 881,346 | 220,337 | 159,058 | 0.649 | 2.000 | 45,971 | 29,658 |
| default | OURS | 4 | 923,075 | 230,769 | 183,575 | 0.680 | 2.000 | 39,553 | 28,398 |
| default | MODEL_B | 4 | 1,037,681 | 259,420 | 183,471 | 0.765 | 3.000 | 31,075 | 41,990 |
| default | ORACLE_PRICE | 4 | 1,224,576 | 306,144 | 259,835 | 0.902 | 3.000 | - | 34,043 |
| default | ORACLE_YIELD | 4 | 1,291,455 | 322,864 | 264,703 | 0.952 | 4.000 | - | -81,320 |
| default | ORACLE | 4 | 1,357,013 | 339,253 | 270,949 | 1.000 | 4.000 | - | 0.000 |
| tight | B1 | 4 | 917,914 | 229,479 | 132,462 | 0.778 | - | 0.000 | 38,800 |
| tight | B2 | 4 | 1,036,146 | 259,036 | 195,296 | 0.878 | 3.000 | 31,530 | 31,175 |
| tight | B3 | 3 | 685,287 | 228,429 | 159,058 | 0.581 | 2.000 | - | 52,947 |
| tight | OURS | 4 | 802,579 | 200,645 | 150,618 | 0.680 | 1.000 | 54,580 | 34,404 |
| tight | MODEL_B | 4 | 790,779 | 197,695 | 148,036 | 0.670 | 2.000 | 49,112 | 32,398 |
| tight | ORACLE_PRICE | 4 | 1,089,419 | 272,355 | 190,126 | 0.923 | 3.000 | - | 59,440 |
| tight | ORACLE_YIELD | 4 | 1,128,752 | 282,188 | 207,808 | 0.956 | 4.000 | - | -81,231 |
| tight | ORACLE | 4 | 1,180,087 | 295,022 | 217,442 | 1.000 | 4.000 | - | 0.000 |

`mean_signed_forecast_gap_rs` = mean(realized - planned) profit -- positive means plans came in MORE profitable than forecast (underpromised), negative means they were overoptimistic. Signed, not absolute, because 'how optimistic was the plan' is the question being asked (absolute error would only say how big the miss was, not which direction).

## Per-year realized-profit delta vs B1 (Rs), per scenario

**Four paired years (2016-2019) cannot support a significance test** -- the smallest attainable two-sided sign / Wilcoxon p-value at n=4 is 0.125 -- so none is reported. The per-year deltas below are the result; read the sign and size of each, not an aggregate.

| scenario | challenger | 2016 | 2017 | 2018 | 2019 | mean | years won |
|---|---|---|---|---|---|---|---|
| default | OURS | -17,167 | +31,094 | +69,435 | -78,202 | +1,290 | 2/4 |
| default | MODEL_B | +71,860 | +53,249 | +72,964 | -78,306 | +29,942 | 3/4 |
| tight | OURS | -23,735 | -3,680 | +23,238 | -111,159 | -28,834 | 1/4 |
| tight | MODEL_B | -50,631 | +6,877 | +30,360 | -113,740 | -31,784 | 2/4 |
