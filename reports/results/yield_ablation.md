# Yield model ablation (E1.2)

| model | all_india_MAE | all_india_RMSE | all_india_R2 | all_india_MAPE | maharashtra_MAE | maharashtra_RMSE | maharashtra_R2 | maharashtra_MAPE |
|---|---|---|---|---|---|---|---|---|
| RandomForest (main) | 10.397 | 148.996 | 0.969 | 28.358 | **0.506** | 2.735 | 0.938 | **34.447** |
| RandomForest + area_ha(log) | 10.574 | 150.575 | 0.969 | 29.295 | 0.578 | 2.784 | 0.936 | 39.094 |
| RandomForest - rainfall | **9.663** | **139.153** | **0.973** | **26.782** | 0.553 | **2.711** | **0.939** | 35.472 |
| RandomForest - year | 13.976 | 200.160 | 0.945 | 34.092 | 0.627 | 3.009 | 0.925 | 43.103 |
