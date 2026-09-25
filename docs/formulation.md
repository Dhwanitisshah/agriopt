# AgriOpt: multi-objective crop planning formulation

Implemented in `src/agriopt/optim/` (`params.py`, `problem.py`, `solvers.py`,
`baselines.py`) and run by `scripts/30_run_optimizer.py`.

## Decision variables

`x_i >= 0` = hectares allocated to crop `i`, for `i` in the 8 canonical crops
(`agriopt.config.CROPS`), each capped at `x_i <= max_share * LAND` (default
`max_share=0.5`).

## Objectives (pymoo minimize-form: f1 = -Profit, f2 = Water, f3 = Fert)

**Profit** (maximized -- `f1 = -Profit`)

```
Profit = sum_i x_i * (Qhat_i * Phat_i - C_i)
```

- `Qhat_i` = `expected_yield_saleable(i)["value"]`, quintal/ha of `i`'s
  MARKETED product (see `docs/units.md` for the rice/cotton unit conversions)
- `Phat_i` = `expected_price(i, horizon=12, msp_floor=...)["value_rs_per_qtl"]`
  -- either the market forecast or `max(forecast, MSP)` depending on
  `Scenario.price_mode` (`"market"` | `"msp_floor"`)
- `C_i` = `cost_rs_per_ha(i, Qhat_i)` = `cost_rs_per_qtl_i * Qhat_i`
  (`crop_reference.csv`, all-India A2+FL cost per quintal of marketed
  product -- see `docs/reference_data.md`)

**Water** (minimized -- `f2 = Water`)

```
Water = sum_i x_i * W_i,   W_i = water_mm(i) * 10   [m^3/ha]
```

- `water_mm(i)` = midpoint of `crop_reference.csv`'s `water_mm_min`/`water_mm_max`
  (FAO TM3 crop water need range; tur uses the FAO TM3 "beans" proxy)
- **Limitation (Phase 1-7 default)**: `Scenario.water_basis` defaults to
  `"total_need"` -- FAO TM3's TOTAL crop water NEED over the growing season,
  not NET IRRIGATION requirement (which would subtract effective rainfall
  received during the season). For rainfed/partially-rainfed crops this
  overstates the water that would actually need to come from irrigation.
  Treat `WATER_BUDGET_M3` scenarios as a **water-need budget**, not a
  literal canal/well supply figure, under this default basis.
- **Phase 8 fix**: passing `water_basis="net_irrigation"` computes `W_i`
  from `agriopt.data.rainfall.net_irrigation_mm()` instead -- crop water
  need minus effective season rainfall (IMD sub-divisional monthly
  rainfall, USDA-SCS/CROPWAT effective-rainfall formula) -- giving a real
  net-irrigation-requirement figure. See `docs/water.md` and
  `reports/results/water_basis_comparison.md`. The default stays
  `"total_need"` so every Phase 1-7.1 result is unaffected.

**Fertilizer** (minimized -- `f3 = Fert`)

```
Fert = sum_i x_i * fert_total_kg_ha(i),   fert_total_kg_ha(i) = N_i + P_i + K_i
```

(`crop_reference.csv: fert_n_kg_ha, fert_p_kg_ha, fert_k_kg_ha` -- 2003/04
all-India actual-use figures for 7/8 crops, ICAR-IISS recommended dose for
soybean; see `docs/reference_data.md` for the full caveat.)

## Constraints (G <= 0 form)

- **Kharif land**: `sum_{i occupies kharif} x_i <= LAND`
- **Rabi land**: `sum_{i occupies rabi} x_i <= LAND`
- **Water budget**: `Water <= WATER_BUDGET_M3`
- **Food security**: `sum_{i in FOOD_CROPS} x_i >= food_share_min * LAND`
  (default `food_share_min=0.3`), `FOOD_CROPS = agriopt.config.FOOD_CROPS =
  [rice, wheat, jowar, tur, maize]`
- **Per-crop cap**: `x_i <= max_share * LAND` (default 0.5), enforced as the
  variable's upper bound, not a separate constraint row
- **Non-negativity**: `x_i >= 0` (variable lower bound)

`LAND`, `WATER_BUDGET_M3`, `food_share_min`, `max_share`, `price_mode` are
scenario inputs (`agriopt.optim.problem.Scenario`), not hardcoded constants.

### Season occupancy (`agriopt.optim.params.seasons_occupied`)

Each crop's hectares count against the Kharif and/or Rabi land constraint(s)
based on `agriopt.config.MAIN_SEASON`, mapped Kharif->kharif, Rabi->rabi,
**except** sugarcane, cotton, and tur, which occupy **both** seasons
regardless of their MAIN_SEASON:
- **sugarcane**: `MAIN_SEASON="Whole Year"` isn't Kharif or Rabi to begin
  with -- it's a long-duration crop genuinely in the ground across both
  seasons, so it's mapped to `{kharif, rabi}` explicitly.
- **cotton, tur**: `MAIN_SEASON="Kharif"`, but both are long-duration
  Kharif-sown crops that stay in the ground into the Rabi season in
  Maharashtra -- this is a deliberate override of the MAIN_SEASON mapping,
  not a data-driven one (see `agriopt.optim.params.BOTH_SEASON_CROPS`).

Resulting occupancy: kharif = {rice, soybean, cotton, sugarcane, tur, maize},
rabi = {wheat, jowar, cotton, sugarcane, tur}.

## Baselines (`agriopt.optim.baselines`)

1. **B1 current-mix** — historical Maharashtra area share (mean of each
   crop's last 5 available years in `yield_clean.parquet`, summed across
   seasons), scaled uniformly down (if needed) so both season totals fit
   within `LAND`. **Not** force-fixed against the water/food constraints --
   `evaluate()` reports feasibility as-is; a scenario where B1 violates
   water or food is reported, not silently corrected.
2. **B2 profit-max** — LP maximizing Profit subject to all constraints
   (`scipy.optimize.linprog`, HiGHS).
3. **B3 same-profit-min-water** — LP minimizing Water subject to
   `Profit >= B1's profit` plus all other constraints (an epsilon-constraint
   solve, `solvers.solve_lp_eps`).
4. **OURS nsga2_recommended** — one solution picked from the NSGA-II Pareto
   front via pymoo pseudo-weights.

## Algorithm

- **NSGA-II** (pymoo `NSGA2`), vectorized `Problem` (not element-wise, for
  speed: 200 generations x pop 100 = 20,000 evals, each a handful of dot
  products over 8 variables)
- Population size: 100, Generations: 200
- Seeds 0-4 used for the NSGA-II-vs-LP quality comparison (E3.2); seed 42
  (`agriopt.config.RANDOM_SEED`) for the single recommended run (E3.1/E3.3)
- **Recommended point**: `solvers.recommend()`, pymoo pseudo-weights
  (`pymoo.mcdm.pseudo_weights.PseudoWeights`) on minimize-form F, default
  weights `(0.5, 0.3, 0.2)` for (profit, water, fert)
- **Exact reference front** (`solvers.exact_front_lp`): since this problem
  is fully linear, an epsilon-constraint LP sweep over `n=50` profit levels
  (min feasible -> max feasible), minimizing water at each level and then
  (fixing water at that minimum) minimizing fertilizer, gives an *exact*
  lexicographic profit>water>fert reference front to compare NSGA-II
  against (hypervolume, IGD -- see `reports/results/optim_front_quality.md`)

## Risk metric (reported, not optimized)

```
profit_risk = sqrt(sum_i (x_i * profit_std_i)^2)
```

`profit_std_i = yield_qtl_ha_i * std(monthly modal price, last 36 months)`
(0 for sugarcane, which has no mandi series). This treats each crop's price
risk as **independent** of every other crop's (no covariance term) --
almost certainly wrong in practice, since monsoon-driven crops' prices tend
to move together, but it's a simple, clearly-labeled *reported* metric in
`evaluate()`'s output, never an optimization objective or constraint.

## Status

Phases 0-2 built the data/yield/price pipeline this formulation consumes;
Phase 3 implements it. Known limitations carried forward: sugarcane has no
mandi price series (FRP instead); the rice/cotton unit conversions
(`docs/units.md`) and most reference-data figures (`docs/reference_data.md`
-- all-India not Maharashtra-specific costs, 2003/04-vintage fertilizer
data) are flagged ASSUMPTION/limitation, not verified ground truth. New in
Phase 3: the water objective is total crop water need, not net irrigation
(see above); `profit_risk` assumes independent crop price risk.
