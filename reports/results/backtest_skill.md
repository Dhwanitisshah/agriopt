# Backtest validity: look-ahead, sugarcane, and where the forecast loses (2016-2019, n=4)

Mean realized profit per year (Rs, 10 ha) over the four decision years with an outcome. `default` water budget = B1's own water footprint, `tight` = 0.7x. **n=4: read as four case studies, not as statistics.**

## headline (May info, all crops)

| scenario | B1 | B2 | B3 | OURS | MODEL_B | ORACLE_PRICE | ORACLE_YIELD | ORACLE | b2_alloc_differs_from_oracle | gap_closed_by_price_foresight | gap_closed_by_yield_foresight |
|---|---|---|---|---|---|---|---|---|---|---|---|
| default | 229,479 | 288,084 | 220,337 | 230,769 | 259,420 | 306,144 | 322,864 | 339,253 | 4/4 | 35% | 68% |
| tight | 229,479 | 259,036 | 228,429 | 200,645 | 197,695 | 272,355 | 282,188 | 295,022 | 4/4 | 37% | 64% |

## legacy look-ahead (rabi prices read in October)

| scenario | B1 | B2 | B3 | OURS | MODEL_B | ORACLE_PRICE | ORACLE_YIELD | ORACLE | b2_alloc_differs_from_oracle | gap_closed_by_price_foresight | gap_closed_by_yield_foresight |
|---|---|---|---|---|---|---|---|---|---|---|---|
| default | 229,479 | 288,084 | 216,736 | 232,036 | 255,849 | 306,144 | 322,864 | 339,253 | 4/4 | 35% | 68% |
| tight | 229,479 | 259,036 | 216,736 | 208,052 | 194,870 | 272,355 | 284,083 | 295,022 | 4/4 | 37% | 70% |

## no sugarcane (May info)

| scenario | B1 | B2 | B3 | OURS | MODEL_B | ORACLE_PRICE | ORACLE_YIELD | ORACLE | b2_alloc_differs_from_oracle | gap_closed_by_price_foresight | gap_closed_by_yield_foresight |
|---|---|---|---|---|---|---|---|---|---|---|---|
| default | 223,307 | 284,212 | 212,957 | 224,466 | 233,498 | 283,900 | 301,476 | 317,630 | 4/4 | -1% | 52% |
| tight | 223,307 | 252,365 | 220,348 | 201,222 | 191,612 | 259,155 | 285,207 | 290,120 | 3/4 | 18% | 87% |

## What this shows

- **default water, look-ahead**: reading rabi prices in October instead of May moves OURS's mean realized profit by +1,267 Rs/yr and B2's by +0 Rs/yr (positive = the look-ahead flattered the result).
- **tight water, look-ahead**: reading rabi prices in October instead of May moves OURS's mean realized profit by +7,407 Rs/yr and B2's by +0 Rs/yr (positive = the look-ahead flattered the result).
- **default water, forecast skill**: B2's allocation differs from ORACLE's in 4/4 cells (all crops) and 4/4 cells without sugarcane; B2 captures 85% of ORACLE (all crops) vs 89% without sugarcane. Knowing only the realized prices closes 35% of the gap, knowing only the realized yields 68% (the two overlap).
- **tight water, forecast skill**: B2's allocation differs from ORACLE's in 4/4 cells (all crops) and 3/4 cells without sugarcane; B2 captures 88% of ORACLE (all crops) vs 87% without sugarcane. Knowing only the realized prices closes 37% of the gap, knowing only the realized yields 64% (the two overlap).
