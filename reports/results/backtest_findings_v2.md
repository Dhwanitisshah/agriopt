# Decision backtest v2 findings (Phase 7.1)

## Fairness verdict

- B1 (current_mix) is water-INFEASIBLE in the tight scenario for years [2016, 2017, 2018, 2019, 2020] (uses more water than its own budget allows) -- confirmed via evaluate()'s feasible flag AND a direct water_m3 vs budget_m3 comparison. B1_SCALED corrects this by scaling B1's hectares down proportionally until water_m3 <= budget.
- After water-scaling, B1_SCALED never violates the food-share constraint in any year/scenario.
- **tight scenario, OURS**: won 0.0/4 vs raw B1, 4.0/4 vs B1_SCALED (the fair, water-feasible baseline); mean capture_ratio_w (water-matched) = 0.97; mean profit per 1,000 m3 water = Rs 9,271.
- **tight scenario, MODEL_B**: won 0.0/4 vs raw B1, 3.0/4 vs B1_SCALED (the fair, water-feasible baseline); mean capture_ratio_w (water-matched) = 0.86; mean profit per 1,000 m3 water = Rs 8,084.

## B2 == ORACLE

- Identical allocation (within 0.0001 ha) in 8/8 year/scenario combos. Both are profit-max LPs over the SAME feasible region (water_m3_ha/fert_kg_ha/seasons_occupied are physical, not forecast-dependent) -- they differ only through which crop the objective vector (profit_ha) favors, so when forecast and realized profit_ha rank crops identically (same top crop(s) hit their max_share*land_ha cap, same runner-up ordering), the LPs land on the same vertex.

## Mechanism (decomposition)

- **B1_SCALED, tight scenario, summed 2016-2019**: largest net effects by crop: cotton (Rs 65,518, driven by yield_effect); soybean (Rs -12,262, driven by price_effect).
  cost_effect summed |value| = Rs 0.000000 (exactly 0 by construction -- see decompose_profit's docstring).
- **OURS, tight scenario, summed 2016-2019**: largest net effects by crop: tur (Rs 113,773, driven by yield_effect); rice (Rs 13,824, driven by yield_effect).
  cost_effect summed |value| = Rs 0.000000 (exactly 0 by construction -- see decompose_profit's docstring).
- **MODEL_B, tight scenario, summed 2016-2019**: largest net effects by crop: rice (Rs 32,923, driven by price_effect); tur (Rs 26,848, driven by yield_effect).
  cost_effect summed |value| = Rs 0.000000 (exactly 0 by construction -- see decompose_profit's docstring).
