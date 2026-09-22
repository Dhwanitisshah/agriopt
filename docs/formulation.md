# AgriOpt: multi-objective crop planning formulation

## Decision variables

`x_i >= 0` = hectares allocated to crop `i`, for `i` in the 8 canonical crops
(`agriopt.config.CROPS`).

## Objectives

**Maximize Profit**

```
Profit = sum_i x_i * (Yhat_i * 10 * Phat_i - C_i)
```

- `Yhat_i` = predicted yield, tonnes/ha
- `Yhat_i * 10` converts tonnes/ha -> quintal/ha (1 t = 10 quintal)
- `Phat_i` = predicted price, Rs/quintal
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
- Food security: `x_rice + x_wheat + x_jowar + x_tur >= 0.3 * LAND`
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

This document describes the intended formulation for later phases. Phase 0
does not implement the yield model, price model, or optimizer — see
`reports/eda/eda_report.md` and `reports/eda/price_report.md` for what the
underlying data actually supports (in particular: 5 of 8 crops currently
have no price series in the mandi dataset, and `tur` has no FAO TM3 water
figure).
