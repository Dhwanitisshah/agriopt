# Information ablation (Phase 5.1, Experiment 4)

Each variant DECIDES an allocation using its own (degraded) view of crop params, then that allocation is EVALUATED under FULL params -- this measures the real cost of deciding with worse information, not just how the params themselves differ. B2/B3 (exact LP solvers, identical feasible region across variants) are compared by profit loss vs the FULL decision; OURS (NSGA-II, a heuristic) is compared by Pareto dominance on (profit, water, fert), since a raw profit-loss number would conflate 'worse information' with 'NSGA-II didn't fully converge.'

## B2 (profit-max LP) and B3 (same-profit-min-water LP)

| variant | water_scenario | strategy | profit_under_full | profit_loss_rs_vs_full | profit_loss_pct_vs_full | water_m3 | fert_kg | allocation_l1_dist_ha | feasible |
|---|---|---|---|---|---|---|---|---|---|
| FULL | tight | B2 | 300829.44 | 0.00 | 0.00 | 73395.42 | 1456.54 | 0.00 | True |
| FULL | tight | B3 | 182833.11 | 0.00 | 0.00 | 43553.98 | 963.45 | 0.00 | True |
| NO_ML_YIELD | tight | B2 | 266761.81 | 34067.64 | 11.32 | 73395.42 | 744.35 | 15.77 | True |
| NO_ML_YIELD | tight | B3 | 152379.47 | 30453.64 | 16.66 | 43462.65 | 434.40 | 12.66 | True |
| MSP_PRICE | tight | B2 | 266761.81 | 34067.64 | 11.32 | 73395.42 | 744.35 | 15.77 | True |
| MSP_PRICE | tight | B3 | 201824.44 | -18991.33 | -10.39 | 56401.93 | 568.38 | 13.47 | True |
| MEAN_PRICE | tight | B2 | 257625.35 | 43204.10 | 14.36 | 73395.42 | 733.91 | 17.27 | True |
| MEAN_PRICE | tight | B3 | 206524.52 | -23691.41 | -12.96 | 60022.82 | 595.44 | 15.19 | True |
| NO_COST | tight | B2 | 263739.95 | 37089.49 | 12.33 | 73395.42 | 888.50 | 13.74 | True |
| NO_COST | tight | B3 | 255437.80 | -72604.69 | -39.71 | 71083.79 | 877.99 | 12.05 | True |
| FULL | current | B2 | 421029.37 | 0.00 | 0.00 | 104850.60 | 1782.26 | 0.00 | True |
| FULL | current | B3 | 182833.11 | 0.00 | 0.00 | 43553.98 | 963.45 | 0.00 | True |
| NO_ML_YIELD | current | B2 | 402861.88 | 18167.49 | 4.32 | 104850.60 | 1283.11 | 9.82 | True |
| NO_ML_YIELD | current | B3 | 152379.47 | 30453.64 | 16.66 | 43462.65 | 434.40 | 12.66 | True |
| MSP_PRICE | current | B2 | 370326.32 | 50703.05 | 12.04 | 104850.60 | 1143.54 | 16.29 | True |
| MSP_PRICE | current | B3 | 201824.44 | -18991.33 | -10.39 | 56401.93 | 568.38 | 13.47 | True |
| MEAN_PRICE | current | B2 | 383606.40 | 37422.97 | 8.89 | 104850.60 | 1156.32 | 14.96 | True |
| MEAN_PRICE | current | B3 | 206524.52 | -23691.41 | -12.96 | 60022.82 | 595.44 | 15.19 | True |
| NO_COST | current | B2 | 383606.40 | 37422.97 | 8.89 | 104850.60 | 1156.32 | 14.96 | True |
| NO_COST | current | B3 | 255437.80 | -72604.69 | -39.71 | 71083.79 | 877.99 | 12.05 | True |

## OURS (NSGA-II): dominance vs the FULL decision

| variant | water_scenario | strategy | profit_under_full | dominated_by_full | profit_pct_vs_full | water_pct_vs_full | fert_pct_vs_full | allocation_l1_dist_ha | feasible |
|---|---|---|---|---|---|---|---|---|---|
| FULL | tight | OURS | 208962.99 | False | 0.00 | 0.00 | 0.00 | 0.00 | True |
| NO_ML_YIELD | tight | OURS | 187646.24 | False | -10.20 | 5.37 | -51.78 | 13.99 | True |
| MSP_PRICE | tight | OURS | 187821.15 | False | -10.12 | 5.47 | -51.74 | 13.99 | True |
| MEAN_PRICE | tight | OURS | 179297.84 | False | -14.20 | 5.79 | -52.54 | 15.50 | True |
| NO_COST | tight | OURS | 185950.14 | False | -11.01 | 6.14 | -38.61 | 12.06 | True |
| FULL | current | OURS | 290096.78 | False | 0.00 | 0.00 | 0.00 | 0.00 | True |
| NO_ML_YIELD | current | OURS | 284040.65 | False | -2.09 | 7.90 | -31.53 | 11.26 | True |
| MSP_PRICE | current | OURS | 265643.22 | False | -8.43 | 2.13 | -35.51 | 11.40 | True |
| MEAN_PRICE | current | OURS | 253138.83 | False | -12.74 | 0.01 | -37.54 | 12.40 | True |
| NO_COST | current | OURS | 238715.04 | False | -17.71 | -6.14 | -35.92 | 10.65 | True |

## Findings

- **B2 (exact profit-max LP), by profit loss**: **MSP_PRICE** costs the most (+11.7% vs the FULL-information decision, mean over water scenarios). All B2 losses are >=0 by construction (asserted in code) -- the FULL decision is the true profit-max over an identical feasible region, so any other variant's B2 decision can only do as well or worse once judged under FULL params.
  - MEAN_PRICE: mean profit loss +11.6%, mean allocation shift 16.11 ha.
  - MSP_PRICE: mean profit loss +11.7%, mean allocation shift 16.03 ha.
  - NO_COST: mean profit loss +10.6%, mean allocation shift 14.35 ha.
  - NO_ML_YIELD: mean profit loss +7.8%, mean allocation shift 12.79 ha.

- **B3 (same-profit-min-water LP)**, mean profit loss / allocation shift per variant (not guaranteed >=0 -- each variant targets its OWN B1 profit level, not FULL's):
  - MEAN_PRICE: mean profit loss -13.0%, mean allocation shift 15.19 ha.
  - MSP_PRICE: mean profit loss -10.4%, mean allocation shift 13.47 ha.
  - NO_COST: mean profit loss -39.7%, mean allocation shift 12.05 ha.
  - NO_ML_YIELD: mean profit loss +16.7%, mean allocation shift 12.66 ha.

- **OURS (NSGA-II)**: the FULL decision Pareto-dominates the variant's decision (on profit/water/fert, under FULL params) in 0/8 variant x water-scenario combinations. Where it isn't dominated, the variant's NSGA-II plan traded one objective against another rather than simply losing on all three -- see the deltas above.

Plain language: this table shows which single piece of information -- the ML yield model, the price forecast, or the cost-of-cultivation figures -- the exact-solver (B2) decision depends on most; see the per-variant mean profit loss above for which one dominates in this run.
