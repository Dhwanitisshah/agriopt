# Decision backtest findings (Phase 7)

- **2020 has no realized outcome at all**: Maharashtra's yield_clean.parquet stops at 2019 for every crop, so all realized-profit comparisons below cover 2016-2019 (n=4 years), not the full 5 decision years -- planning for 2020 still ran (it only needs data through 2019), it's just unscored.
- **OURS did NOT beat B1 in 2019 (default scenario)**: realized profit Rs 151,565 vs B1's Rs 183,253. See the allocation/price data for that year in backtest_rows.csv and prices_monthly.parquet to trace which crop's forecast missed -- reported here rather than glossed over.
- **MODEL_B did NOT beat B1 in 2019 (default scenario)**: realized profit Rs 129,957 vs B1's Rs 183,253. See the allocation/price data for that year in backtest_rows.csv and prices_monthly.parquet to trace which crop's forecast missed -- reported here rather than glossed over.
- **OURS did NOT beat B1 in 2019 (tight scenario)**: realized profit Rs 115,966 vs B1's Rs 183,253. See the allocation/price data for that year in backtest_rows.csv and prices_monthly.parquet to trace which crop's forecast missed -- reported here rather than glossed over.
- **MODEL_B did NOT beat B1 in 2016 (tight scenario)**: realized profit Rs 223,796 vs B1's Rs 260,303. See the allocation/price data for that year in backtest_rows.csv and prices_monthly.parquet to trace which crop's forecast missed -- reported here rather than glossed over.
- **MODEL_B did NOT beat B1 in 2019 (tight scenario)**: realized profit Rs 103,457 vs B1's Rs 183,253. See the allocation/price data for that year in backtest_rows.csv and prices_monthly.parquet to trace which crop's forecast missed -- reported here rather than glossed over.
- **default scenario, OURS**: capture ratio 0.69 vs ORACLE, won 3.0/4 years vs B1, mean signed forecast gap Rs 32,720 (realized - planned).
- **default scenario, MODEL_B**: capture ratio 0.62 vs ORACLE, won 3.0/4 years vs B1, mean water saved vs B1 19,844 m3.
- **tight scenario, OURS**: capture ratio 0.70 vs ORACLE, won 3.0/4 years vs B1, mean signed forecast gap Rs 32,412 (realized - planned).
- **tight scenario, MODEL_B**: capture ratio 0.61 vs ORACLE, won 2.0/4 years vs B1, mean water saved vs B1 34,226 m3.

**Statistical caveat (stated plainly, not buried)**: every sign-test / Wilcoxon p-value in backtest_summary.md is computed on n=4 paired years. Statistical power at n=4 is essentially nonexistent -- these are exploratory/directional signals only, not evidence that AgriOpt beats (or fails to beat) B1 in any statistically meaningful sense. Do not cite a low p-value here as proof.
