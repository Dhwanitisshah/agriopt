# Price dataset audit (Kaggle mandi CSV -- secondary source)
Source: `C:\Users\Dhwanit Shah\Desktop\agriopt\data\raw\prices\Agriculture_price_dataset.csv`

Actual raw columns: `['STATE', 'District Name', 'Market Name', 'Commodity', 'Variety', 'Grade', 'Min_Price', 'Max_Price', 'Modal_Price', 'Price Date']`

Unit: Rs/quintal (Min_Price, Max_Price, Modal_Price).

This is the SECONDARY price source (see `price_report` vs `eda_report.md` "Price coverage" for the CEDA-primary, merged view). It only fills months CEDA lacks.

## Commodity coverage
- The entire dataset (all states) contains only 5 distinct commodities: ['Onion', 'Potato', 'Rice', 'Tomato', 'Wheat']
- Of the 8 AgriOpt target crops, Kaggle price data exists for: ['Rice', 'Wheat']
- **No price coverage at all (neither CEDA nor Kaggle) for**: ['sugarcane']. See admin_price_rs_per_qtl (FRP) in crop_reference.csv instead.

## Maharashtra coverage for available Kaggle target commodities

| commodity | n_rows | min_date | max_date | n_markets | n_missing_dates | n_distinct_dates |
|---|---|---|---|---|---|---|
| Wheat | 9084 | 2023-06-06 | 2024-02-06 | 141 | 0 | 245 |
| Rice | 491 | 2025-04-06 | 2025-06-06 | 17 | 0 | 61 |
