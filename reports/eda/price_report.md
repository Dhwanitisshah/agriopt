# Price dataset audit
Source: `C:\Users\Dhwanit Shah\Desktop\agriopt\data\raw\prices\Agriculture_price_dataset.csv`

Actual raw columns: `['STATE', 'District Name', 'Market Name', 'Commodity', 'Variety', 'Grade', 'Min_Price', 'Max_Price', 'Modal_Price', 'Price Date']`

Unit: Rs/quintal (Min_Price, Max_Price, Modal_Price).

## Commodity coverage
- The entire dataset (all states) contains only 5 distinct commodities: ['Onion', 'Potato', 'Rice', 'Tomato', 'Wheat']
- Of the 8 AgriOpt target crops, price data exists for: ['Onion', 'Rice', 'Wheat']
- **No price coverage at all (any state) for**: ['cotton', 'jowar', 'soybean', 'sugarcane', 'tur']. These crops cannot get a data-driven price model from this dataset; `CROP_NAME_MAP[...]['price']` is `None` for them.

## Maharashtra coverage for available target commodities

| commodity | n_rows | min_date | max_date | n_markets | n_missing_dates | n_distinct_dates |
|---|---|---|---|---|---|---|
| Onion | 26755 | 2023-06-06 | 2025-06-11 | 99 | 0 | 639 |
| Wheat | 9084 | 2023-06-06 | 2024-02-06 | 141 | 0 | 245 |
| Rice | 491 | 2025-04-06 | 2025-06-06 | 17 | 0 | 61 |

## Cleaned output
- `C:\Users\Dhwanit Shah\Desktop\agriopt\data\processed\prices_monthly.parquet`: 36 rows (crop, month, modal_price_rs_per_qtl = state-level MEDIAN, n_markets).

## Plot
- `monthly_price_by_crop.png`
