# Yield dataset audit
Source: `C:\Users\Dhwanit Shah\Desktop\agriopt\data\raw\yield\crop_yield.csv`

## 8th crop selection (onion had 1 Maharashtra row; replaced)

| crop | n_rows | n_years | year_min | year_max |
|---|---|---|---|---|
| Maize | 68 | 23 | 1997 | 2019 |
| Groundnut | 44 | 22 | 1998 | 2019 |
| Bajra | 23 | 23 | 1997 | 2019 |
| Gram | 23 | 23 | 1997 | 2019 |

**Chosen 8th crop: Maize** (most Maharashtra rows and year coverage among the candidates).
## a) Overview
- Shape: 19689 rows x 10 columns
- Dtypes:
  - `Crop`: str
  - `Crop_Year`: int64
  - `Season`: str
  - `State`: str
  - `Area`: float64
  - `Production`: int64
  - `Annual_Rainfall`: float64
  - `Fertilizer`: float64
  - `Pesticide`: float64
  - `Yield`: float64
- Null counts:
  - `Crop`: 0
  - `Crop_Year`: 0
  - `Season`: 0
  - `State`: 0
  - `Area`: 0
  - `Production`: 0
  - `Annual_Rainfall`: 0
  - `Fertilizer`: 0
  - `Pesticide`: 0
  - `Yield`: 0
- Year range: 1997-2020
- #States: 30
- #Crops: 55

## b) Maharashtra rows per target crop per season

| crop | season | n_rows |
|---|---|---|
| rice | Kharif | 23 |
| rice | Summer | 23 |
| wheat | Rabi | 23 |
| jowar | Kharif | 23 |
| jowar | Rabi | 23 |
| soybean | Kharif | 22 |
| cotton | Kharif | 22 |
| cotton | Whole Year | 1 |
| sugarcane | Kharif | 2 |
| sugarcane | Whole Year | 21 |
| tur | Kharif | 23 |
| maize | Autumn | 1 |
| maize | Kharif | 23 |
| maize | Rabi | 23 |
| maize | Summer | 21 |

**Weak-data crops** (total Maharashtra rows < 10): none

## c) Leakage check 1: Yield vs Production/Area
- Rows compared (Area > 0): 19689
- max abs diff |Yield - Production/Area|: 3733.99
- mean abs diff: 5.931
- Yield is not exactly Production/Area; Production is still dropped from the cleaned frame as a conservative leakage precaution (Yield is the modeling target).

## d) Leakage check 2: Fertilizer/Pesticide vs Area
- corr(Fertilizer, Area) = 0.9733
- corr(Pesticide, Area) = 0.9735
- **Both correlations > 0.8 -> Fertilizer/Pesticide are farm-level totals, not per-hectare rates. Converted to `fertilizer_per_ha`/`pesticide_per_ha` and raw totals dropped.**

## Unit audit
ratio = Yield / (Production/Area), computed on Maharashtra rows (Area > 0) per target crop. A ratio near 1 confirms Yield and Production/Area are internally self-consistent (same underlying basis) -- it does NOT by itself prove which real-world quantity (e.g. paddy vs milled rice, lint bales vs tonnes) that basis represents. See `docs/units.md` for the full reasoning behind `YIELD_TO_SALEABLE_QTL_PER_HA`.

| crop | n | ratio_median | ratio_IQR | Yield median | Production median |
|---|---|---|---|---|---|
| rice | 46 | 0.9644 | [0.7301, 1.0195] | 1.9970 | 994311.5 |
| wheat | 23 | 0.9533 | [0.9454, 0.9677] | 1.3887 | 1308500.0 |
| jowar | 46 | 1.0944 | [0.9509, 1.2448] | 0.8941 | 1691200.0 |
| soybean | 22 | 1.0792 | [1.0293, 1.1815] | 1.2416 | 2373250.0 |
| cotton | 23 | 1.0593 | [0.9866, 1.1832] | 1.4544 | 4617500.0 |
| sugarcane | 23 | 0.8819 | [0.8411, 0.9160] | 69.6215 | 64159300.0 |
| tur | 23 | 0.8927 | [0.8532, 0.9325] | 0.6394 | 814600.0 |
| maize | 68 | 0.8780 | [0.8232, 0.9587] | 1.6323 | 217850.0 |

All target-crop ratios fall within (0.5, 2.0) of 1 -- consistent with (does not contradict) the milled-rice and cotton-bales assumptions below. Cotton's Production magnitude (median ~4.6M for Maharashtra alone) is only plausible as **bales**, not tonnes (India's total national lint production is ~30-34M bales/yr), which supports treating cotton Yield as bales/ha rather than tonnes/ha.

### Assumptions used for Yield -> quintals of marketed product (see `agriopt.config`)
- **rice**: dataset Yield is MILLED RICE t/ha (ASSUMPTION). paddy t/ha = Yield / RICE_OUTTURN (0.67); marketed product = paddy.
- **cotton**: dataset Yield is LINT COTTON bales/ha (ASSUMPTION). lint_kg/ha = Yield * BALE_KG (170); kapas_kg/ha = lint_kg/ha / GINNING_OUTTURN (0.34); marketed product = kapas.
- **all others** (wheat, jowar, soybean, sugarcane, tur, maize): tonnes/ha -> quintals/ha (x10), no product-form conversion.

## e) Data quality: outliers, invalid areas, duplicates

### Per-crop yield outliers (IQR, 1.5x whiskers)

| crop | n | n_outliers | lower_bound | upper_bound |
|---|---|---|---|---|
| Maize | 975 | 62 | -0.4898 | 4.734 |
| Wheat | 545 | 40 | -0.5593 | 4.308 |
| Dry chillies | 419 | 36 | -1.917 | 5.259 |
| Sannhamp | 160 | 35 | -0.7342 | 1.873 |
| Groundnut | 725 | 34 | -0.15 | 2.77 |
| Tobacco | 364 | 33 | -1.956 | 4.999 |
| Peas & beans (Pulses) | 369 | 27 | -0.2093 | 2.184 |
| Turmeric | 337 | 24 | -4.372 | 9.976 |
| Arhar/Tur | 508 | 24 | 0.05746 | 1.558 |
| Rapeseed &Mustard | 528 | 22 | -0.2902 | 1.729 |
| Ragi | 498 | 22 | -0.4229 | 2.76 |
| Castor seed | 300 | 22 | -0.3505 | 1.586 |
| Jowar | 513 | 21 | -0.09677 | 2.128 |
| Arecanut | 162 | 21 | -0.2668 | 2.95 |
| Bajra | 524 | 21 | -0.8319 | 3.237 |
| Coriander | 199 | 17 | -0.1921 | 1.128 |
| Ginger | 323 | 16 | -9.124 | 19.67 |
| Black pepper | 126 | 16 | -0.9142 | 2.117 |
| Horse-gram | 371 | 15 | -0.0846 | 0.9589 |
| Cashewnut | 134 | 14 | -0.2269 | 1.275 |
| Urad | 733 | 14 | -0.1491 | 1.253 |
| Soyabean | 349 | 14 | 0.035 | 2.108 |
| other oilseeds | 126 | 14 | -0.2452 | 1.739 |
| Barley | 297 | 13 | -0.5899 | 3.597 |
| Cardamom | 74 | 13 | -0.01022 | 0.1816 |
| Other  Rabi pulses | 355 | 13 | -0.1815 | 1.596 |
| Garlic | 250 | 12 | -5.116 | 12.38 |
| Potato | 628 | 11 | -5.725 | 28.83 |
| Cotton(lint) | 476 | 10 | -1.447 | 4.403 |
| Onion | 454 | 9 | -9.797 | 31.59 |
| Masoor | 324 | 9 | 0.07048 | 1.284 |
| Rice | 1197 | 9 | -0.009583 | 4.374 |
| Niger seed | 192 | 8 | -0.2317 | 0.9849 |
| Other Cereals | 146 | 8 | -0.2533 | 1.814 |
| Moong(Green Gram) | 740 | 8 | -0.1752 | 1.185 |
| Guar seed | 63 | 8 | 0.4234 | 1.113 |
| Sunflower | 441 | 7 | -0.3752 | 2.144 |
| Small millets | 485 | 7 | -0.2033 | 1.686 |
| Gram | 490 | 6 | -0.03861 | 1.664 |
| Sugarcane | 605 | 6 | -29.15 | 134.7 |
| Sesamum | 685 | 5 | -0.2345 | 1.111 |
| Oilseeds total | 29 | 5 | -0.07288 | 2.775 |
| Linseed | 308 | 4 | -0.1126 | 1.027 |
| Other Kharif pulses | 382 | 4 | -0.2966 | 1.669 |
| Banana | 245 | 2 | -32.32 | 85.16 |
| Sweet potato | 273 | 2 | -6.127 | 24.53 |
| Cowpea(Lobia) | 134 | 1 | -0.6413 | 2.174 |
| Khesari | 75 | 1 | 0.1616 | 1.393 |
| Jute | 181 | 1 | -10.54 | 22.75 |
| Coconut | 172 | 1 | -3104 | 2.103e+04 |
| Mesta | 210 | 1 | -7.114 | 17.29 |
| Other Summer Pulses | 10 | 1 | 0.06901 | 1.251 |
| Moth | 110 | 0 | -0.3656 | 1.251 |
| Safflower | 169 | 0 | -0.2262 | 1.339 |
| Tapioca | 201 | 0 | -19.08 | 50.65 |

### Zero/negative areas
- 0 rows with Area <= 0 (dropped from the cleaned frame; per-hectare rates are undefined otherwise).

### Duplicates
- 0 rows involved in exact duplicates (kept once in the cleaned frame).

## f) Plots
- `yield_distribution_by_crop.png`
- `yield_over_years_by_crop.png`
- `correlation_heatmap.png`

## Cleaned output
- `C:\Users\Dhwanit Shah\Desktop\agriopt\data\processed\yield_clean.parquet`: 19689 rows (all-India, `Production` dropped, per-hectare rates, `is_target_crop` flag).

## Price coverage (CEDA primary + Kaggle secondary, merged)
Source: `C:\Users\Dhwanit Shah\Desktop\agriopt\data\processed\prices_monthly.parquet` (built by `scripts/03_fetch_ceda_prices.py`).

| crop | min_month | max_month | n_months | n_missing_months | last_month | flag |
|---|---|---|---|---|---|---|
| rice | 2001-06-01 | 2025-10-01 | 285 | 8.0 | 2025-10-01 |  |
| wheat | 2001-03-01 | 2025-10-01 | 296 | 0.0 | 2025-10-01 |  |
| jowar | 2001-03-01 | 2025-10-01 | 295 | 1.0 | 2025-10-01 |  |
| soybean | 2001-05-01 | 2025-10-01 | 294 | 0.0 | 2025-10-01 |  |
| cotton | 2002-12-01 | 2025-10-01 | 263 | 12.0 | 2025-10-01 |  |
| sugarcane | - | - | 0 | - | - | **no mandi series (sugarcane: FRP admin price)** |
| tur | 2001-12-01 | 2025-10-01 | 278 | 9.0 | 2025-10-01 |  |
| maize | 2001-04-01 | 2025-10-01 | 294 | 1.0 | 2025-10-01 |  |
