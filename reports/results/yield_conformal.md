# Yield conformal prediction intervals (Phase 9 / E1.5)

Split conformal, log1p(yield)-space (this repo's `log_yield` convention -- log1p, not plain log; monotonic, so the coverage guarantee transfers unchanged to the exponentiated original-unit interval). RandomForest fit on year<=2012 (all-India, n=12463), calibrated on 2013-2015 residuals (all-India, n=2938), nominal level 90%. Applied to the Maharashtra 2016-2020 test set (n=152).

| crop | q source | q (log1p) | coverage | nominal | mean width (orig units) | n |
|---|---|---|---|---|---|---|
| ALL | overall | 0.3285 | 0.941 | 0.90 | 2.53 | 152 |
| rice | per_crop | 0.1810 | 1.000 | 0.90 | 1.05 | 8 |
| wheat | per_crop | 0.2967 | 1.000 | 0.90 | 1.57 | 4 |
| jowar | per_crop | 0.2697 | 1.000 | 0.90 | 1.09 | 8 |
| soybean | per_crop | 0.3307 | 1.000 | 0.90 | 1.62 | 4 |
| cotton | per_crop | 0.3664 | 0.750 | 0.90 | 2.00 | 4 |
| sugarcane | per_crop | 0.7714 | 1.000 | 0.90 | 123.19 | 4 |
| tur | per_crop | 0.1717 | 0.750 | 0.90 | 0.58 | 4 |
| maize | per_crop | 0.4089 | 1.000 | 0.90 | 2.40 | 12 |

## Findings

- Overall empirical coverage (0.941) is within 5 points of the nominal 0.90 level -- the calibration set (all-India 2013-2015) generalizes reasonably to the Maharashtra 2016-2020 test set for this purpose.
- Per-crop miscalibration (>5pt off nominal): rice, wheat, jowar, soybean, cotton, sugarcane, tur, maize -- per-crop n is small (see the table), so these are noisier than the overall figure.
