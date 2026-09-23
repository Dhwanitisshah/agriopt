# Information ablation (Phase 5, Experiment 4)

Each variant DECIDES an allocation (OURS = NSGA-II recommend, seed=0, default weights; B2 = profit-max LP) using its own (degraded) view of crop params, then that allocation is EVALUATED under FULL params -- this measures the real cost of deciding with worse information, not just how the params themselves differ.

| variant | water_scenario | strategy | profit_under_full | profit_pct_loss_vs_full_decision | water_m3 | fert_kg | allocation_l1_dist_ha | portfolio_risk_rs | feasible |
|---|---|---|---|---|---|---|---|---|---|
| FULL | tight | OURS | 201712.50 | 0.00 | 38213.79 | 559.14 | 0.00 | 57087.79 | True |
| FULL | tight | B2 | 298892.24 | 0.00 | 51991.93 | 777.62 | 0.00 | 60026.79 | True |
| NO_ML_YIELD | tight | OURS | 201358.13 | 0.18 | 37603.72 | 532.41 | 2.58 | 61179.62 | True |
| NO_ML_YIELD | tight | B2 | 298892.24 | 0.00 | 51991.93 | 777.62 | 0.00 | 60026.79 | True |
| MSP_PRICE | tight | OURS | 201686.14 | 0.01 | 38410.66 | 381.70 | 5.03 | 122418.23 | True |
| MSP_PRICE | tight | B2 | 292090.33 | 2.28 | 51991.93 | 522.72 | 6.23 | 126621.66 | True |
| MEAN_PRICE | tight | OURS | 205709.42 | -1.98 | 38802.36 | 386.01 | 4.99 | 119774.68 | True |
| MEAN_PRICE | tight | B2 | 292090.33 | 2.28 | 51991.93 | 522.72 | 6.23 | 126621.66 | True |
| NO_COST | tight | OURS | 174661.87 | 13.41 | 38783.15 | 375.67 | 6.73 | 184673.20 | True |
| NO_COST | tight | B2 | 261525.98 | 12.50 | 51991.93 | 512.28 | 8.18 | 190971.13 | True |
| FULL | current | OURS | 304411.81 | 0.00 | 54020.80 | 543.75 | 0.00 | 127590.08 | True |
| FULL | current | B2 | 443722.32 | 0.00 | 74274.19 | 1008.35 | 0.00 | 86304.32 | True |
| NO_ML_YIELD | current | OURS | 307414.13 | -0.99 | 54999.05 | 589.39 | 0.83 | 122303.49 | True |
| NO_ML_YIELD | current | B2 | 443722.32 | 0.00 | 74274.19 | 1008.35 | 0.00 | 86304.32 | True |
| MSP_PRICE | current | OURS | 276134.43 | 9.29 | 54047.91 | 552.94 | 2.33 | 180674.22 | True |
| MSP_PRICE | current | B2 | 436920.42 | 1.53 | 74274.19 | 753.45 | 6.22 | 143353.87 | True |
| MEAN_PRICE | current | OURS | 298959.77 | 1.79 | 53954.03 | 549.61 | 0.50 | 135341.78 | True |
| MEAN_PRICE | current | B2 | 436920.42 | 1.53 | 74274.19 | 753.45 | 6.22 | 143353.87 | True |
| NO_COST | current | OURS | 272552.07 | 10.47 | 53834.52 | 532.98 | 2.47 | 191441.09 | True |
| NO_COST | current | B2 | 406356.06 | 8.42 | 74274.19 | 743.01 | 8.18 | 203104.41 | True |

## Findings

- By profit loss (OURS, averaged over water scenarios): **NO_COST** costs the most (+11.9% vs the FULL-information decision). By decision shift: **NO_COST** moves hectares the most (4.60 ha mean L1 distance from the FULL decision).
- MEAN_PRICE: mean profit loss -0.1%, mean allocation shift 2.75 ha.
- MSP_PRICE: mean profit loss +4.7%, mean allocation shift 3.68 ha.
- NO_COST: mean profit loss +11.9%, mean allocation shift 4.60 ha.
- NO_ML_YIELD: mean profit loss -0.4%, mean allocation shift 1.70 ha.

Plain language: this table shows which single piece of information -- the ML yield model, the price forecast, or the cost-of-cultivation figures -- the recommendation depends on most. A variant with near-zero loss/shift means that information barely matters for the DECISION even if the numbers themselves change; a variant with a large loss/shift means the pipeline is leaning heavily on that particular model or data source.
