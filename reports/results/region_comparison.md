# Region comparison: net-irrigation water basis by IMD subdivision (Phase 8.1)

Compares the recommended allocation (OURS, NSGA-II + pseudo-weights) at the `current` water/`market` price scenario, across region=`maharashtra` (state-wide, area-weighted -- reports/results/optim_strategies_net.md, Phase 8), region=`marathwada` (drought-prone, semi-arid) and region=`konkan` (high-rainfall coastal) -- see docs/water.md section 8 for the net irrigation numbers behind these allocations.

## Net irrigation requirement, region contrast (normal scenario, mm)

| crop | maharashtra | marathwada | konkan |
|---|---|---|---|
| cotton | 324.4 | 432.5 | 93.6 |
| jowar | 514.4 | 514.1 | 525.2 |
| maize | 0.0 | 107.3 | 0.0 |
| rice | 200.0 | 232.3 | 200.0 |
| soybean | 0.0 | 32.3 | 0.0 |
| sugarcane | 1292.5 | 1401.1 | 1056.7 |
| tur | 0.0 | 0.0 | 0.0 |
| wheat | 514.4 | 514.1 | 525.2 |

## OURS allocation summary, current water x market price

- **marathwada**: OURS profit=253960 Rs, water=20845 m3, fert=770 kg, n_crops=4, food_share=0.83
- **konkan**: OURS profit=232078 Rs, water=13365 m3, fert=696 kg, n_crops=6, food_share=0.75

## E3 strategies: profit & water, current x market -- maharashtra (Phase 8 net) vs marathwada vs konkan

| region | strategy | profit (Rs) | water_m3 |
|---|---|---|---|
| maharashtra (state-wide) | B1 | 166259 | 25980 |
| marathwada | B1 | 166259 | 34054 |
| konkan | B1 | 166259 | 22259 |
| maharashtra (state-wide) | B2 | 423747 | 25980 |
| marathwada | B2 | 378105 | 34054 |
| konkan | B2 | 344150 | 22259 |
| maharashtra (state-wide) | B3 | 166259 | 0 |
| marathwada | B3 | 166259 | 10709 |
| konkan | B3 | 166259 | 7127 |
| maharashtra (state-wide) | OURS | 305166 | 15122 |
| marathwada | OURS | 253960 | 20845 |
| konkan | OURS | 232078 | 13365 |

## Findings

- Marathwada's own (drier) normal-year effective rainfall pushes rice's net irrigation to 232mm vs 200mm state-wide (+16%) -- Marathwada's season-window rainfall covers noticeably less of rice's FAO TM3 need than the state-wide average, making rice relatively more water-expensive there.
- Konkan's high monsoon rainfall keeps rice's net irrigation at 200mm (essentially just RICE_EXTRA_MM's puddling-water floor -- see docs/water.md 8.2), the lowest of the 3 regions shown, since Konkan's own Kharif-season Peff comfortably exceeds rice's total water need.
- B1 (current mix)'s own net-irrigation water footprint under region=marathwada is +31.1% vs the state-wide maharashtra figure -- since B1's crop mix is fixed, this change is driven entirely by how much of the SAME crop mix's water need that region's own rainfall covers.
- B1 (current mix)'s own net-irrigation water footprint under region=konkan is -14.3% vs the state-wide maharashtra figure -- since B1's crop mix is fixed, this change is driven entirely by how much of the SAME crop mix's water need that region's own rainfall covers.
- All `*_region` outputs (net_irrigation_by_region.{csv,md}, optim_strategies_marathwada.{csv,md}, optim_strategies_konkan.{csv,md}, region_comparison.md) are NEW files -- no Phase 1-8 output (including the `*_net` files) was modified.
