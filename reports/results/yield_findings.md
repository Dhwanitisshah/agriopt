# Yield model findings (Phase 1 / Phase 2 fix)

> **Update (economics review, Task 8).** The pooled Maharashtra MAE/R^2 below mix crops in different units
> (t/ha, bales/ha, milled-rice equivalent), so they mostly measure which crops have large numbers; the pooled R^2 has
> been dropped. On the 8 decision crops, in the optimizer's units and one step ahead (RF refit each year vs baselines,
> 2016-2019, n=4 per crop), the RandomForest **beats a last-3-year state mean on only 3/8 crops** (rice, wheat, soybean)
> and loses on jowar, cotton, sugarcane, tur and maize; against the best of three naive baselines it loses on 7/8. The
> sentence below that every ML model beats both baselines refers to the pooled figure only. See
> `yield_decision_crops.md`.

- **Model selected on validation, not test.** Best model family chosen by Maharashtra MAE on the validation window (fit <2013, evaluate 2013-2015): **RandomForest** (validation Maharashtra MAE=0.3786; next best: Baseline-Mean=0.4005, Baseline-Last=0.4034, XGBoost=0.4062, Ridge=1.3512).
- Validation-based selection agrees with what test-based selection would have picked (RandomForest) -- the fix changes the *methodology* (no more test-set leakage into model selection) without changing the outcome here.
- Test-set metrics reported below are for **RandomForest** (pooled Maharashtra test MAE=0.506, in mixed units; all-India test MAE=10.397) -- computed purely for reporting, played no role in selecting it.
- All-India test MAE would have picked a different model (Baseline-Last) than Maharashtra MAE (RandomForest) -- all-India MAE is dominated by scale effects from huge-magnitude, non-target crops (e.g. Coconut yield up to ~5000 t/ha), so a model can win on that metric while doing poorly for our actual crops/region.
- Every ML model (Ridge/RandomForest/XGBoost) beats both baselines on Maharashtra MAE -- yield is a fairly stable, group-predictable quantity given (state, crop, season) history, so this is not surprising either way.
- Hardest Maharashtra crop by MAPE: **tur** (31.4%). Easiest: **sugarcane** (5.1%).
- fertilizer_per_ha/pesticide_per_ha were EXCLUDED from the main feature set (see feature_audit.md) -- they were found to be a year proxy (near-zero within-year variance), so year alone covers that signal.
- Ablation (RandomForest): adding area_ha(log) changed all-India MAE from 10.397 to 10.574; dropping rainfall changed it to 9.663; dropping year changed it to 13.976 (see yield_ablation.md for the full breakdown, all-India + Maharashtra).
- Regional generalization (RandomForest): training WITHOUT Maharashtra rows gives Maharashtra test MAE=0.750, vs 0.506 when Maharashtra is included (a real drop in accuracy when the model has never seen Maharashtra data -- relevant for how much local calibration the optimizer's yield model will eventually need).
- MAPE is computed on original-scale yield per crop; crops with naturally low absolute yield (e.g. pulses like tur) can show higher MAPE for the same absolute error than high-yield crops (e.g. sugarcane), since MAPE divides by the (small) true value -- read MAE alongside MAPE, not MAPE alone.
- This is the yield model only: predicted yield feeds the optimizer's profit objective only after conversion to quintals of marketed product via YIELD_TO_SALEABLE_QTL_PER_HA (rice/cotton unit assumptions, docs/units.md) and multiplication by a price forecast (see reports/results/price_findings.md).
