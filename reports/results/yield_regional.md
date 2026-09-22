# Regional generalization preview (E1.3)

| model | all_india_MAE | all_india_RMSE | all_india_R2 | all_india_MAPE | maharashtra_MAE | maharashtra_RMSE | maharashtra_R2 | maharashtra_MAPE | rice_MAE | rice_MAPE | wheat_MAE | wheat_MAPE | jowar_MAE | jowar_MAPE | soybean_MAE | soybean_MAPE | cotton_MAE | cotton_MAPE | sugarcane_MAE | sugarcane_MAPE | tur_MAE | tur_MAPE | maize_MAE | maize_MAPE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| RandomForest (Maharashtra included) | 10.397 | 148.996 | 0.969 | **28.358** | **0.506** | **2.735** | **0.938** | **34.447** | **0.206** | **11.377** | 0.132 | 8.299 | 0.184 | 24.599 | **0.090** | **7.364** | 0.649 | 25.183 | **3.394** | **5.116** | 0.311 | 31.411 | **0.430** | **26.149** |
| RandomForest (Maharashtra excluded) | **10.285** | **147.929** | **0.970** | 29.861 | 0.750 | 2.902 | 0.930 | 79.584 | 0.549 | 32.126 | **0.121** | **7.668** | **0.132** | **19.176** | 0.171 | 13.864 | **0.592** | **24.432** | 7.159 | 10.486 | **0.164** | **20.828** | 0.446 | 29.642 |
