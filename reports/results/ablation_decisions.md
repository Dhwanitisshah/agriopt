# Information ablation (Phase 5.1, Experiment 4)

Each variant DECIDES an allocation using its own (degraded) view of crop params, then that allocation is EVALUATED under FULL params -- this measures the real cost of deciding with worse information, not just how the params themselves differ. B2/B3 (exact LP solvers, identical feasible region across variants) are compared by profit loss vs the FULL decision; OURS (NSGA-II, a heuristic) is compared by Pareto dominance on (profit, water, fert), since a raw profit-loss number would conflate 'worse information' with 'NSGA-II didn't fully converge.'

## B2 (profit-max LP) and B3 (same-profit-min-water LP)

| variant | water_scenario | strategy | profit_under_full | profit_loss_rs_vs_full | profit_loss_pct_vs_full | water_m3 | fert_kg | allocation_l1_dist_ha | feasible |
|---|---|---|---|---|---|---|---|---|---|
| FULL | tight | B2 | 211581.69 | 0.00 | 0.00 | 50509.08 | 1136.31 | 0.00 | True |
| FULL | tight | B3 | 129794.13 | 0.00 | 0.00 | 31312.82 | 632.67 | 0.00 | True |
| NO_ML_YIELD | tight | B2 | 179306.05 | 32275.63 | 15.25 | 50509.08 | 507.36 | 14.36 | True |
| NO_ML_YIELD | tight | B3 | 112071.29 | 17722.84 | 13.65 | 32914.38 | 325.17 | 9.05 | True |
| MSP_PRICE | tight | B2 | 179306.05 | 32275.63 | 15.25 | 50509.08 | 507.36 | 14.36 | True |
| MSP_PRICE | tight | B3 | 138961.58 | -9167.45 | -7.06 | 39951.32 | 398.04 | 9.49 | True |
| MEAN_PRICE | tight | B2 | 170169.59 | 41412.09 | 19.57 | 50509.08 | 496.92 | 15.86 | True |
| MEAN_PRICE | tight | B3 | 139325.60 | -9531.47 | -7.34 | 42437.50 | 413.34 | 11.14 | True |
| NO_COST | tight | B2 | 181544.24 | 30037.45 | 14.20 | 50509.08 | 784.49 | 9.30 | True |
| NO_COST | tight | B3 | 168772.04 | -38977.91 | -30.03 | 47224.48 | 744.90 | 5.01 | True |
| FULL | current | B2 | 296092.58 | 0.00 | 0.00 | 72155.83 | 1443.70 | 0.00 | True |
| FULL | current | B3 | 129794.13 | 0.00 | 0.00 | 31312.82 | 632.67 | 0.00 | True |
| NO_ML_YIELD | current | B2 | 262024.94 | 34067.64 | 11.51 | 72155.83 | 731.51 | 15.77 | True |
| NO_ML_YIELD | current | B3 | 112071.29 | 17722.84 | 13.65 | 32914.38 | 325.17 | 9.05 | True |
| MSP_PRICE | current | B2 | 262024.94 | 34067.64 | 11.51 | 72155.83 | 731.51 | 15.77 | True |
| MSP_PRICE | current | B3 | 138961.58 | -9167.45 | -7.06 | 39951.32 | 398.04 | 9.49 | True |
| MEAN_PRICE | current | B2 | 252888.48 | 43204.10 | 14.59 | 72155.83 | 721.07 | 17.27 | True |
| MEAN_PRICE | current | B3 | 139325.60 | -9531.47 | -7.34 | 42437.50 | 413.34 | 11.14 | True |
| NO_COST | current | B2 | 259287.99 | 36804.59 | 12.43 | 72155.83 | 882.87 | 13.57 | True |
| NO_COST | current | B3 | 168772.04 | -38977.91 | -30.03 | 47224.48 | 744.90 | 5.01 | True |

## OURS (NSGA-II): dominance vs the FULL decision

| variant | water_scenario | strategy | profit_under_full | dominated_by_full | profit_pct_vs_full | water_pct_vs_full | fert_pct_vs_full | allocation_l1_dist_ha | feasible |
|---|---|---|---|---|---|---|---|---|---|
| FULL | tight | OURS | 149023.78 | False | 0.00 | 0.00 | 0.00 | 0.00 | True |
| NO_ML_YIELD | tight | OURS | 136733.62 | False | -8.25 | 6.53 | -48.40 | 9.38 | True |
| MSP_PRICE | tight | OURS | 128079.69 | False | -14.05 | 4.36 | -54.95 | 10.93 | True |
| MEAN_PRICE | tight | OURS | 120529.95 | False | -19.12 | 3.72 | -55.39 | 11.87 | True |
| NO_COST | tight | OURS | 123402.13 | False | -17.19 | 0.89 | -35.68 | 10.60 | True |
| FULL | current | OURS | 213309.41 | False | 0.00 | 0.00 | 0.00 | 0.00 | True |
| NO_ML_YIELD | current | OURS | 194240.90 | False | -8.94 | 3.04 | -49.02 | 12.65 | True |
| MSP_PRICE | current | OURS | 180078.38 | False | -15.58 | -2.32 | -52.86 | 13.33 | True |
| MEAN_PRICE | current | OURS | 177459.20 | False | -16.81 | -0.84 | -52.48 | 14.18 | True |
| NO_COST | current | OURS | 183862.55 | False | -13.80 | -1.54 | -39.23 | 10.54 | True |

## Findings

- **B2 (exact profit-max LP), by profit loss**: **MEAN_PRICE** costs the most (+17.1% vs the FULL-information decision, mean over water scenarios). All B2 losses are >=0 by construction (asserted in code) -- the FULL decision is the true profit-max over an identical feasible region, so any other variant's B2 decision can only do as well or worse once judged under FULL params.
  - MEAN_PRICE: mean profit loss +17.1%, mean allocation shift 16.56 ha.
  - MSP_PRICE: mean profit loss +13.4%, mean allocation shift 15.06 ha.
  - NO_COST: mean profit loss +13.3%, mean allocation shift 11.44 ha.
  - NO_ML_YIELD: mean profit loss +13.4%, mean allocation shift 15.06 ha.

- **B3 (same-profit-min-water LP)**, mean profit loss / allocation shift per variant (not guaranteed >=0 -- each variant targets its OWN B1 profit level, not FULL's):
  - MEAN_PRICE: mean profit loss -7.3%, mean allocation shift 11.14 ha.
  - MSP_PRICE: mean profit loss -7.1%, mean allocation shift 9.49 ha.
  - NO_COST: mean profit loss -30.0%, mean allocation shift 5.01 ha.
  - NO_ML_YIELD: mean profit loss +13.7%, mean allocation shift 9.05 ha.

- **OURS (NSGA-II)**: the FULL decision Pareto-dominates the variant's decision (on profit/water/fert, under FULL params) in 0/8 variant x water-scenario combinations. Where it isn't dominated, the variant's NSGA-II plan traded one objective against another rather than simply losing on all three -- see the deltas above.

Plain language: this table shows which single piece of information -- the ML yield model, the price forecast, or the cost-of-cultivation figures -- the exact-solver (B2) decision depends on most; see the per-variant mean profit loss above for which one dominates in this run.
