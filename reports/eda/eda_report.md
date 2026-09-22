# Yield dataset audit
Source: `C:\Users\Dhwanit Shah\Desktop\agriopt\data\raw\yield\crop_yield.csv`
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
| onion | Whole Year | 1 |

**Weak-data crops** (total Maharashtra rows < 10): ['onion']

## c) Leakage check 1: Yield vs Production/Area
- Rows compared (Area > 0): 19689
- max abs diff |Yield - Production/Area|: 3733.99
- mean abs diff: 5.931
- Yield is not exactly Production/Area; Production is still dropped from the cleaned frame as a conservative leakage precaution (Yield is the modeling target).

## d) Leakage check 2: Fertilizer/Pesticide vs Area
- corr(Fertilizer, Area) = 0.9733
- corr(Pesticide, Area) = 0.9735
- **Both correlations > 0.8 -> Fertilizer/Pesticide are farm-level totals, not per-hectare rates. Converted to `fertilizer_per_ha`/`pesticide_per_ha` and raw totals dropped.**

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
