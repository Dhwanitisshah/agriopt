# AgriOpt: multi-objective crop planning formulation

## Decision variables

`x_i >= 0` = hectares allocated to crop `i`, for `i` in the 8 canonical crops
(`agriopt.config.CROPS`).

## Objectives

**Maximize Profit**

```
Profit = sum_i x_i * (Qhat_i * Phat_i - C_i)
```

- `Yhat_i` = predicted dataset-basis yield, t/ha (or bales/ha for cotton)
- `Qhat_i = YIELD_TO_SALEABLE_QTL_PER_HA[i](Yhat_i)` = predicted yield converted
  to quintal/ha of the crop's MARKETED product (see `docs/units.md` -- for
  most crops this is `Yhat_i * 10`, but rice converts milled-rice t/ha to
  paddy quintal/ha and cotton converts lint bales/ha to kapas quintal/ha)
- `Phat_i` = predicted price of the marketed product, Rs/quintal (rice uses
  the paddy price series; cotton uses the kapas/raw-cotton series)
- `C_i` = cost of cultivation, Rs/ha (`crop_reference.csv: cost_rs_per_ha`)

**Minimize Water**

```
Water = sum_i x_i * W_i
```

- `W_i` = crop water need, mm (`crop_reference.csv: water_mm_min`..`water_mm_max`
  midpoint, or a scenario-selected value within that FAO TM3 range)

**Minimize Fertilizer**

```
Fert = sum_i x_i * (N_i + P_i + K_i)
```

- `N_i, P_i, K_i` = kg/ha recommended dose (`crop_reference.csv:
  fert_n_kg_ha, fert_p_kg_ha, fert_k_kg_ha`)

## Constraints

- Land: `sum_i x_i <= LAND`
- Water budget: `Water <= WATER_BUDGET`
- Food security: `sum_{i in FOOD_CROPS} x_i >= 0.3 * LAND`, where
  `FOOD_CROPS = agriopt.config.FOOD_CROPS = [rice, wheat, jowar, tur, maize]`
  (cereals/pulses among the 8 target crops; maize joined after the
  onion -> maize swap in Phase 0.5)
- Diversification cap: `x_i <= 0.5 * LAND` for every crop `i`
- Non-negativity: `x_i >= 0`

`LAND` and `WATER_BUDGET` are scenario inputs supplied by the UI/caller, not
hardcoded constants.

## Baselines (for comparison against the optimized frontier)

1. **Current-mix** — historical Maharashtra area share per crop (from
   `yield_clean.parquet`, `state == "Maharashtra"`), scaled to `LAND`.
2. **Yield-max** — all land to the single highest-predicted-yield crop
   (subject to the constraints above).
3. **Profit-max** — all land to the single highest-predicted-profit-per-ha
   crop (subject to the constraints above).

## Algorithm

- **NSGA-II** (pymoo `NSGA2`)
- Population size: 100
- Generations: 200
- Seed: 42 (`agriopt.config.RANDOM_SEED`)
- **Recommended point**: selected from the final Pareto front via pymoo's
  pseudo-weights (`pymoo.mcdm.pseudo_weights`), not a single fixed weighting
  of the objectives.

## Status

This document describes the intended formulation for later phases. Phase 0 /
0.5 do not implement the yield model, price model, or optimizer — see
`reports/eda/eda_report.md` and `reports/eda/price_report.md` for what the
underlying data actually supports. In particular: sugarcane has no mandi
price series at all (government FRP instead, see `admin_price_rs_per_qtl` in
`crop_reference.csv`, currently a TODO placeholder); `tur` has no FAO TM3
water figure; and the rice/cotton unit conversions in `docs/units.md` are
flagged ASSUMPTION pending verification.
