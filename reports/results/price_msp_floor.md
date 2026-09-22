# MSP floor experiment (E2.2, h=12 XGBoost)

| crop | raw_MAE | floored_MAE | raw_MAPE | floored_MAPE | floor_helps |
|---|---|---|---|---|---|
| rice | 396.9 | 300.4 | 15.5 | 11.7 | True |
| wheat | 416.8 | 111.4 | 15.9 | 4.2 | True |
| jowar | 789.8 | 842.6 | 26.3 | 32.3 | False |
| soybean | 1070.6 | 1169.2 | 25.3 | 27.5 | False |
| cotton | 2174.5 | 634.7 | 30.0 | 9.1 | True |
| tur | 3119.8 | 1410.7 | 36.4 | 17.4 | True |
| maize | 391.6 | 292.2 | 18.4 | 14.3 | True |


MSP floor helped overall: helped 5/7 crops (lower MAE with the floor applied).
