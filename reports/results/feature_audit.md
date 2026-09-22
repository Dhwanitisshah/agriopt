# Feature audit

## Data-quality: singleton extreme-outlier rows dropped before modeling
3 row(s) dropped (see `flag_singleton_extreme_outliers` in `agriopt.models.yield_model`): the ONLY observation for their (state, crop, season) group, at >20x the crop's national median yield -- e.g. Maharashtra Maize/Autumn/1997 at 989.87 t/ha, physically impossible. Multi-year patterns (e.g. Chhattisgarh Bajra consistently 30-70x other states' median across 13 years) are NOT touched.

| crop | season | year | state | area_ha | yield |
|---|---|---|---|---|---|
| Tobacco | Rabi | 2015 | Puducherry | 209.0 | 30.170 |
| Cotton(lint) | Whole Year | 1997 | Maharashtra | 31292.0 | 95.994 |
| Maize | Autumn | 1997 | Maharashtra | 21.0 | 989.870 |

## fertilizer_per_ha / pesticide_per_ha: year-proxy check
Within-year coefficient of variation (std/mean) across all (state, crop, season) rows. CV < 0.01 is treated as "effectively a single national rate per year" -- i.e. a year proxy carrying no information beyond what the `year` feature already provides.

| column | mean within-year std | mean within-year mean | mean within-year CV | year proxy? |
|---|---|---|---|---|
| fertilizer_per_ha | 3.91404e-09 | 135.764 | 2.84458e-11 | True |
| pesticide_per_ha | 2.33908e-17 | 0.27375 | 8.3218e-17 | True |

**Verdict: fertilizer_per_ha and pesticide_per_ha are YEAR PROXIES (near-zero within-year variance) -> EXCLUDED from the main feature set (year is kept).**

## Row counts: train (<=2015) vs test (>=2016)

| crop | all-India train | all-India test | Maharashtra train | Maharashtra test |
|---|---|---|---|---|
| rice | 951 | 246 | 38 | 8 |
| wheat | 438 | 107 | 19 | 4 |
| jowar | 408 | 105 | 38 | 8 |
| soybean | 265 | 84 | 18 | 4 |
| cotton | 381 | 94 | 18 | 4 |
| sugarcane | 499 | 106 | 19 | 4 |
| tur | 398 | 110 | 19 | 4 |
| maize | 769 | 205 | 55 | 12 |
