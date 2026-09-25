"""Phase 9: statistical-significance / uncertainty-quantification tooling.

Self-contained (no new heavy dependencies -- statsmodels is NOT installed in
this environment, see requirements; only numpy/scipy are used, matching the
rest of the repo). Three independent pieces:

- `dm_test`: Diebold-Mariano test with the Harvey-Leybourne-Newbold (HLN)
  small-sample correction, for comparing two forecasts' absolute-error loss.
- `conformal`: split-conformal prediction intervals (finite-sample corrected
  quantile of calibration residuals).
- `bootstrap`: a generic paired bootstrap CI for a scalar metric (MAE here).
"""
