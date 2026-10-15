# Decision backtest v2 findings (Phase 7.1)

## Fairness verdict

- B1 (current_mix) violates a constraint (water budget or minimum food share) in the tight scenario for years [2016, 2017, 2018, 2019, 2020] -- confirmed via evaluate()'s feasible flag. B1_SCALED is the allocation closest to B1 (fewest hectares moved, an LP) that satisfies every constraint; it moves 1.36 ha on average.
- B1_SCALED satisfies the food-share constraint in every year/scenario, by construction.
- **tight scenario, OURS**: won 1.0/4 vs raw B1, 3.0/4 vs B1_SCALED (the fair, water-feasible baseline); mean capture_ratio_w (water-matched) = 0.88; mean profit per 1,000 m3 water = Rs 3,951.
- **tight scenario, MODEL_B**: won 2.0/4 vs raw B1, 3.0/4 vs B1_SCALED (the fair, water-feasible baseline); mean capture_ratio_w (water-matched) = 0.81; mean profit per 1,000 m3 water = Rs 3,489.

## B2 == ORACLE

- Identical allocation (within 0.0001 ha) in 0/8 year/scenario combos. Both are profit-max LPs over the SAME feasible region (water_m3_ha/fert_kg_ha/seasons_occupied are physical, not forecast-dependent) -- they differ only through which crop the objective vector (profit_ha) favors, so when forecast and realized profit_ha rank crops identically (same top crop(s) hit their max_share*land_ha cap, same runner-up ordering), the LPs land on the same vertex.

## Mechanism (decomposition)

- **B1_SCALED, tight scenario, summed 2016-2019**: largest net effects by crop: cotton (Rs 54,987, driven by yield_effect); soybean (Rs -23,474, driven by price_effect).
  cost_effect summed |value| = Rs 0.000000 (exactly 0 by construction -- see decompose_profit's docstring).
- **OURS, tight scenario, summed 2016-2019**: largest net effects by crop: tur (Rs 143,519, driven by yield_effect); rice (Rs 25,624, driven by price_effect).
  cost_effect summed |value| = Rs 0.000000 (exactly 0 by construction -- see decompose_profit's docstring).
- **MODEL_B, tight scenario, summed 2016-2019**: largest net effects by crop: tur (Rs 77,373, driven by yield_effect); rice (Rs 41,089, driven by yield_effect).
  cost_effect summed |value| = Rs 0.000000 (exactly 0 by construction -- see decompose_profit's docstring).
