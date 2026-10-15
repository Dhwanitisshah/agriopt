# Region comparison: net-irrigation water basis by IMD subdivision (Phase 8.1)

Compares the recommended allocation (OURS, NSGA-II + pseudo-weights) at the `current` water/`market` price scenario, across region=`maharashtra` (state-wide, area-weighted -- reports/results/optim_strategies_net.md, Phase 8), region=`marathwada` (drought-prone, semi-arid) and region=`konkan` (high-rainfall coastal) -- see docs/water.md section 8 for the net irrigation numbers behind these allocations.

## Net irrigation requirement, region contrast (normal scenario, mm)

| crop | maharashtra | marathwada | konkan |
|---|---|---|---|
| cotton | 433.4 | 505.1 | 399.5 |
| jowar | 515.7 | 515.8 | 526.9 |
| maize | 91.5 | 171.1 | 48.7 |
| rice | 266.5 | 321.5 | 236.8 |
| soybean | 66.5 | 121.5 | 36.8 |
| sugarcane | 1318.3 | 1443.9 | 1210.5 |
| tur | 136.2 | 142.9 | 137.0 |
| wheat | 515.7 | 515.8 | 526.9 |

## OURS allocation summary, current water x market price

- **marathwada**: OURS profit=248237 Rs, water=38863 m3, fert=914 kg, n_crops=3, food_share=0.63
- **konkan**: OURS profit=253235 Rs, water=31905 m3, fert=963 kg, n_crops=3, food_share=0.60

## E3 strategies: profit & water, current x market -- maharashtra (Phase 8 net) vs marathwada vs konkan

| region | strategy | profit (Rs) | water_m3 |
|---|---|---|---|
| maharashtra (state-wide) | B1 | 182833 | 54532 |
| marathwada | B1 | 182833 | 60606 |
| konkan | B1 | 182833 | 51788 |
| maharashtra (state-wide) | B2 | 364071 | 54532 |
| marathwada | B2 | 361474 | 60606 |
| konkan | B2 | 376334 | 51788 |
| maharashtra (state-wide) | B3 | 182833 | 21520 |
| marathwada | B3 | 182833 | 24744 |
| konkan | B3 | 182833 | 19639 |
| maharashtra (state-wide) | OURS | 258265 | 36519 |
| marathwada | OURS | 248237 | 38863 |
| konkan | OURS | 253235 | 31905 |

## Equal water budget: the same absolute m3 in every region

Budget = 0.7x / 1.0x of the STATE-WIDE normal-year B1 net-irrigation footprint, identical for every region (unlike the per-region tables above, whose budgets shrink where rain is plentiful). Market prices. `dry` = the real observed year nearest the region's 20th percentile of usable rain (agriopt.data.rainfall.dry_year). B1's hectares are the same everywhere, so any B1 change is the region's rain.

### rainfall=normal, water=current (54,532 m3 everywhere)

| region | B1 profit | B1 water | B2 profit | OURS profit | OURS water | OURS vs B1 | B1 feasible |
|---|---|---|---|---|---|---|---|
| maharashtra | 182,833 | 54,532 | 364,071 | 258,265 | 36,519 | +41.3% | True |
| konkan | 182,833 | 51,788 | 392,747 | 273,010 | 34,840 | +49.3% | True |
| madhya_maharashtra | 182,833 | 57,151 | 348,704 | 244,796 | 35,308 | +33.9% | False |
| marathwada | 182,833 | 60,606 | 331,215 | 224,101 | 33,461 | +22.6% | False |
| vidarbha | 182,833 | 56,959 | 349,169 | 239,686 | 34,690 | +31.1% | False |

### rainfall=normal, water=tight (38,172 m3 everywhere)

| region | B1 profit | B1 water | B2 profit | OURS profit | OURS water | OURS vs B1 | B1 feasible |
|---|---|---|---|---|---|---|---|
| maharashtra | 182,833 | 54,532 | 274,256 | 194,509 | 24,198 | +6.4% | False |
| konkan | 182,833 | 51,788 | 294,397 | 209,420 | 24,550 | +14.5% | False |
| madhya_maharashtra | 182,833 | 57,151 | 263,730 | 185,544 | 24,729 | +1.5% | False |
| marathwada | 182,833 | 60,606 | 249,722 | 180,092 | 25,446 | -1.5% | False |
| vidarbha | 182,833 | 56,959 | 261,913 | 179,451 | 23,686 | -1.8% | False |

### rainfall=dry, water=current (54,532 m3 everywhere)

| region | B1 profit | B1 water | B2 profit | OURS profit | OURS water | OURS vs B1 | B1 feasible |
|---|---|---|---|---|---|---|---|
| maharashtra | 182,833 | 59,080 | 347,399 | 243,869 | 36,237 | +33.4% | False |
| konkan | 182,833 | 54,884 | 375,613 | 266,943 | 35,683 | +46.0% | False |
| madhya_maharashtra | 182,833 | 61,050 | 332,447 | 231,074 | 33,831 | +26.4% | False |
| marathwada | 182,833 | 65,308 | 307,369 | 211,288 | 34,912 | +15.6% | False |
| vidarbha | 182,833 | 61,593 | 323,232 | 217,331 | 34,924 | +18.9% | False |

### rainfall=dry, water=tight (38,172 m3 everywhere)

| region | B1 profit | B1 water | B2 profit | OURS profit | OURS water | OURS vs B1 | B1 feasible |
|---|---|---|---|---|---|---|---|
| maharashtra | 182,833 | 59,080 | 259,165 | 182,882 | 24,470 | +0.0% | False |
| konkan | 182,833 | 54,884 | 281,296 | 201,978 | 24,950 | +10.5% | False |
| madhya_maharashtra | 182,833 | 61,050 | 252,333 | 179,573 | 25,852 | -1.8% | False |
| marathwada | 182,833 | 65,308 | 230,292 | 162,350 | 24,635 | -11.2% | False |
| vidarbha | 182,833 | 61,593 | 236,879 | 163,793 | 24,653 | -10.4% | False |


## Findings

- Marathwada's own (drier) normal-year effective rainfall pushes rice's net irrigation to 322mm vs 266mm state-wide (+21%) -- Marathwada's season-window rainfall covers noticeably less of rice's FAO TM3 need than the state-wide average, making rice relatively more water-expensive there.
- Konkan's high monsoon rainfall keeps rice's net irrigation at 237mm (essentially just RICE_EXTRA_MM's puddling-water floor -- see docs/water.md 8.2), the lowest of the 3 regions shown, since Konkan's own Kharif-season Peff comfortably exceeds rice's total water need.
- B1 (current mix)'s own net-irrigation water footprint under region=marathwada is +11.1% vs the state-wide maharashtra figure -- since B1's crop mix is fixed, this change is driven entirely by how much of the SAME crop mix's water need that region's own rainfall covers.
- B1 (current mix)'s own net-irrigation water footprint under region=konkan is -5.0% vs the state-wide maharashtra figure -- since B1's crop mix is fixed, this change is driven entirely by how much of the SAME crop mix's water need that region's own rainfall covers.
- All `*_region` outputs (net_irrigation_by_region.{csv,md}, optim_strategies_marathwada.{csv,md}, optim_strategies_konkan.{csv,md}, region_comparison.md) are NEW files -- no Phase 1-8 output (including the `*_net` files) was modified.
