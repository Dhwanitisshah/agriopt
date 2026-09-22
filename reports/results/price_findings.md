# Price model findings (Phase 2)

- h=3: **Naive** wins on overall backtest MAE (373.6 Rs/qtl); XGBoost=454.4, Seasonal-Naive=800.5
- h=6: **Naive** wins on overall backtest MAE (512.6 Rs/qtl); XGBoost=743.2, Seasonal-Naive=783.5
- h=12: **Naive** wins on overall backtest MAE (750.9 Rs/qtl); Seasonal-Naive=750.9, XGBoost=1194.3. Naive and Seasonal-Naive are mathematically IDENTICAL at h=12 (12 months before a target 12 months out is just the origin month's own price), so any tie there is expected, not a bug.
- A naive baseline wins at one or more horizons -- commodity mandi prices are highly persistent month-to-month, so simple persistence is a strong, hard-to-beat baseline, especially with only ~20 years of monthly data pooled across 7 crops for XGBoost to learn from.
- MSP floor (E2.2, h=12 XGBoost): helped 5/7 crops (lower MAE with max(forecast, MSP) than the raw forecast) -- MSP floors are a net positive adjustment given how often mandi prices trade below MSP.
- This uses rolling-origin backtest MAE as a VALIDATION signal to select the deployed h=12 model (no further held-out test set exists beyond the backtest itself) -- the reported backtest numbers for the winning model are the same numbers used to pick it, unlike the yield model's separate validation/test split.
- Sugarcane has no mandi price series at all -- expected_price('sugarcane') always returns the government FRP (crop_reference.csv), never a forecast.
