# Information ablation (Phase 5.1, Experiment 4)

Each variant DECIDES an allocation using its own (degraded) view of crop params, then that allocation is EVALUATED under FULL params -- this measures the real cost of deciding with worse information, not just how the params themselves differ. B2/B3 (exact LP solvers, identical feasible region across variants) are compared by profit loss vs the FULL decision; OURS (NSGA-II, a heuristic) is compared by Pareto dominance on (profit, water, fert), since a raw profit-loss number would conflate 'worse information' with 'NSGA-II didn't fully converge.'

## B2 (profit-max LP) and B3 (same-profit-min-water LP)

| variant | water_scenario | strategy | profit_under_full | profit_loss_rs_vs_full | profit_loss_pct_vs_full | water_m3 | fert_kg | allocation_l1_dist_ha | feasible |
|---|---|---|---|---|---|---|---|---|---|
| FULL | tight | B2 | 298892.24 | 0.00 | 0.00 | 51991.93 | 777.62 | 0.00 | True |
| FULL | tight | B3 | 166258.97 | 0.00 | 0.00 | 31586.17 | 566.32 | 0.00 | True |
| NO_ML_YIELD | tight | B2 | 298892.24 | 0.00 | 0.00 | 51991.93 | 777.62 | 0.00 | True |
| NO_ML_YIELD | tight | B3 | 160152.41 | 6106.55 | 3.67 | 30646.67 | 556.59 | 0.05 | True |
| MSP_PRICE | tight | B2 | 292090.33 | 6801.91 | 2.28 | 51991.93 | 522.72 | 6.23 | True |
| MSP_PRICE | tight | B3 | 227597.69 | -61338.72 | -36.89 | 42069.67 | 419.97 | 6.75 | True |
| MEAN_PRICE | tight | B2 | 292090.33 | 6801.91 | 2.28 | 51991.93 | 522.72 | 6.23 | True |
| MEAN_PRICE | tight | B3 | 194113.35 | -27854.38 | -16.75 | 36918.07 | 366.63 | 6.49 | True |
| NO_COST | tight | B2 | 261525.98 | 37366.26 | 12.50 | 51991.93 | 512.28 | 8.18 | True |
| NO_COST | tight | B3 | 229371.00 | -63112.04 | -37.96 | 47044.85 | 461.05 | 8.60 | True |
| FULL | current | B2 | 443722.32 | 0.00 | 0.00 | 74274.19 | 1008.35 | 0.00 | True |
| FULL | current | B3 | 166258.97 | 0.00 | 0.00 | 31586.17 | 566.32 | 0.00 | True |
| NO_ML_YIELD | current | B2 | 443722.32 | 0.00 | 0.00 | 74274.19 | 1008.35 | 0.00 | True |
| NO_ML_YIELD | current | B3 | 160152.41 | 6106.55 | 3.67 | 30646.67 | 556.59 | 0.05 | True |
| MSP_PRICE | current | B2 | 436920.42 | 6801.91 | 1.53 | 74274.19 | 753.45 | 6.22 | True |
| MSP_PRICE | current | B3 | 227597.69 | -61338.72 | -36.89 | 42069.67 | 419.97 | 6.75 | True |
| MEAN_PRICE | current | B2 | 436920.42 | 6801.91 | 1.53 | 74274.19 | 753.45 | 6.22 | True |
| MEAN_PRICE | current | B3 | 194113.35 | -27854.38 | -16.75 | 36918.07 | 366.63 | 6.49 | True |
| NO_COST | current | B2 | 406356.06 | 37366.26 | 8.42 | 74274.19 | 743.01 | 8.18 | True |
| NO_COST | current | B3 | 229371.00 | -63112.04 | -37.96 | 47044.85 | 461.05 | 8.60 | True |

## OURS (NSGA-II): dominance vs the FULL decision

| variant | water_scenario | strategy | profit_under_full | dominated_by_full | profit_pct_vs_full | water_pct_vs_full | fert_pct_vs_full | allocation_l1_dist_ha | feasible |
|---|---|---|---|---|---|---|---|---|---|
| FULL | tight | OURS | 201712.50 | False | 0.00 | 0.00 | 0.00 | 0.00 | True |
| NO_ML_YIELD | tight | OURS | 201358.13 | False | -0.18 | -1.60 | -4.78 | 2.58 | True |
| MSP_PRICE | tight | OURS | 201686.14 | False | -0.01 | 0.52 | -31.73 | 5.03 | True |
| MEAN_PRICE | tight | OURS | 205709.42 | False | 1.98 | 1.54 | -30.96 | 4.99 | True |
| NO_COST | tight | OURS | 174661.87 | False | -13.41 | 1.49 | -32.81 | 6.73 | True |
| FULL | current | OURS | 304411.81 | False | 0.00 | 0.00 | 0.00 | 0.00 | True |
| NO_ML_YIELD | current | OURS | 307414.13 | False | 0.99 | 1.81 | 8.39 | 0.83 | True |
| MSP_PRICE | current | OURS | 276134.43 | True | -9.29 | 0.05 | 1.69 | 2.33 | True |
| MEAN_PRICE | current | OURS | 298959.77 | False | -1.79 | -0.12 | 1.08 | 0.50 | True |
| NO_COST | current | OURS | 272552.07 | False | -10.47 | -0.34 | -1.98 | 2.47 | True |

## Findings

- **B2 (exact profit-max LP), by profit loss**: **NO_COST** costs the most (+10.5% vs the FULL-information decision, mean over water scenarios). All B2 losses are >=0 by construction (asserted in code) -- the FULL decision is the true profit-max over an identical feasible region, so any other variant's B2 decision can only do as well or worse once judged under FULL params.
  - MEAN_PRICE: mean profit loss +1.9%, mean allocation shift 6.22 ha.
  - MSP_PRICE: mean profit loss +1.9%, mean allocation shift 6.22 ha.
  - NO_COST: mean profit loss +10.5%, mean allocation shift 8.18 ha.
  - NO_ML_YIELD: mean profit loss +0.0%, mean allocation shift 0.00 ha.

- **B3 (same-profit-min-water LP)**, mean profit loss / allocation shift per variant (not guaranteed >=0 -- each variant targets its OWN B1 profit level, not FULL's):
  - MEAN_PRICE: mean profit loss -16.8%, mean allocation shift 6.49 ha.
  - MSP_PRICE: mean profit loss -36.9%, mean allocation shift 6.75 ha.
  - NO_COST: mean profit loss -38.0%, mean allocation shift 8.60 ha.
  - NO_ML_YIELD: mean profit loss +3.7%, mean allocation shift 0.05 ha.

- **OURS (NSGA-II)**: the FULL decision Pareto-dominates the variant's decision (on profit/water/fert, under FULL params) in 1/8 variant x water-scenario combinations. Where it isn't dominated, the variant's NSGA-II plan traded one objective against another rather than simply losing on all three -- see the deltas above.

Plain language: **cost-of-cultivation data matters most to the DECISION** -- B2 (the exact solver, so this reading is not a heuristic artifact) loses the most profit (+10.5%) when cost is dropped to zero, more than when yield comes from a historical mean instead of the ML model, or when price is set to MSP/mean-price instead of the forecast. The ML yield model and the price forecast matter less to the final allocation than the reference cost table does.
