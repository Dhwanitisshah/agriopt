# Yield model on the 8 decision crops (saleable qtl/ha)

Why not the pooled table: `yield_results.csv` pools every Maharashtra crop in whatever unit the Kaggle file uses (t/ha, bales/ha, milled-rice equivalent), so its pooled MAE and R^2 mostly reflect which crops have large numbers -- the pooled R^2 is dropped. Below, only the 8 crops the optimizer allocates, in the optimizer's units, with a last-3-year state-mean baseline. **n=4 test years (2016-2019) per crop: directional only.**

## one-step-ahead (refit each year)

| crop | n | RF MAE | RF MAPE % | last-3-yr MAE | last-3-yr MAPE % | best baseline (MAE) | RF skill vs last-3-yr | RF beats last-3-yr? |
|---|---|---|---|---|---|---|---|---|
| rice | 4 | 3.22 | 14.8 | 3.80 | 17.3 | All-years mean (1.76) | +15% | yes |
| wheat | 4 | 1.38 | 8.6 | 1.86 | 11.3 | All-years mean (1.85) | +26% | yes |
| jowar | 4 | 1.94 | 26.9 | 1.61 | 21.3 | All-years mean (1.57) | -20% | **NO -- RF loses** |
| soybean | 4 | 1.13 | 9.1 | 2.30 | 18.6 | All-years mean (0.39) | +51% | yes |
| cotton | 4 | 3.43 | 28.0 | 3.19 | 25.8 | Last-3-year mean (3.19) | -7% | **NO -- RF loses** |
| sugarcane | 4 | 20.16 | 3.0 | 10.29 | 1.5 | Last-3-year mean (10.29) | -96% | **NO -- RF loses** |
| tur | 4 | 3.05 | 33.7 | 2.84 | 30.9 | All-years mean (2.59) | -7% | **NO -- RF loses** |
| maize | 4 | 5.72 | 31.4 | 5.38 | 30.9 | All-years mean (4.63) | -6% | **NO -- RF loses** |

RF loses to the last-3-year mean on **5/8** crops (jowar, cotton, sugarcane, tur, maize) and to the best of the three baselines on 7/8. Mean MAPE over the 8 crops: RF 19.4% vs last-3-year mean 19.7%.

MAPE % by method:

| crop | RandomForest | Last year | Last-3-year mean | All-years mean |
|---|---|---|---|---|
| rice | 14.8 | 13.7 | 17.3 | 8.9 |
| wheat | 8.6 | 18.9 | 11.3 | 11.3 |
| jowar | 26.9 | 35.1 | 21.3 | 20.7 |
| soybean | 9.1 | 14.6 | 18.6 | 3.3 |
| cotton | 28.0 | 44.6 | 25.8 | 29.1 |
| sugarcane | 3.0 | 6.2 | 1.5 | 4.5 |
| tur | 33.7 | 48.0 | 30.9 | 27.0 |
| maize | 31.4 | 29.3 | 30.9 | 24.8 |

## fixed origin (trained <= 2015)

| crop | n | RF MAE | RF MAPE % | last-3-yr MAE | last-3-yr MAPE % | best baseline (MAE) | RF skill vs last-3-yr | RF beats last-3-yr? |
|---|---|---|---|---|---|---|---|---|
| rice | 4 | 4.03 | 17.3 | 3.68 | 15.4 | All-years mean (1.76) | -10% | **NO -- RF loses** |
| wheat | 4 | 1.32 | 8.3 | 3.18 | 20.0 | All-years mean (2.03) | +58% | yes |
| jowar | 4 | 1.90 | 24.5 | 1.66 | 21.2 | All-years mean (1.58) | -15% | **NO -- RF loses** |
| soybean | 4 | 0.90 | 7.4 | 2.76 | 22.5 | All-years mean (0.39) | +67% | yes |
| cotton | 4 | 3.24 | 25.2 | 4.27 | 34.9 | All-years mean (3.98) | +24% | yes |
| sugarcane | 4 | 33.94 | 5.1 | 23.02 | 3.5 | Last-3-year mean (23.02) | -47% | **NO -- RF loses** |
| tur | 4 | 3.11 | 31.4 | 3.79 | 40.7 | All-years mean (2.65) | +18% | yes |
| maize | 4 | 6.04 | 33.2 | 4.47 | 24.9 | Last-3-year mean (4.47) | -35% | **NO -- RF loses** |

RF loses to the last-3-year mean on **4/8** crops (rice, jowar, sugarcane, maize) and to the best of the three baselines on 6/8. Mean MAPE over the 8 crops: RF 19.1% vs last-3-year mean 22.9%.

MAPE % by method:

| crop | RandomForest | Last year | Last-3-year mean | All-years mean |
|---|---|---|---|---|
| rice | 17.3 | 16.0 | 15.4 | 8.8 |
| wheat | 8.3 | 33.2 | 20.0 | 12.5 |
| jowar | 24.5 | 29.7 | 21.2 | 20.6 |
| soybean | 7.4 | 45.1 | 22.5 | 3.3 |
| cotton | 25.2 | 55.7 | 34.9 | 32.1 |
| sugarcane | 5.1 | 11.4 | 3.5 | 4.9 |
| tur | 31.4 | 57.1 | 40.7 | 27.3 |
| maize | 33.2 | 32.4 | 24.9 | 23.5 |

