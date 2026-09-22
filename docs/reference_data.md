# Reference data: cost, MSP, fertilizer, water

Source table: `data/reference/crop_reference.csv`. Loader + derived
quantities: `agriopt.data.reference` (`load_reference()`,
`cost_rs_per_ha()`, `water_mm()`, `fert_total_kg_ha()`).

All rows have `verified=True` and the same `notes`: **costs are all-India
per-quintal figures; per-hectare cost is derived in code**
(`cost_rs_per_ha(crop, saleable_qtl_per_ha) = cost_rs_per_qtl *
saleable_qtl_per_ha`) because cost-per-hectare depends on the crop's
(predicted) yield, which varies by season/year, while cost-per-quintal is a
stable input.

## Cost of cultivation + MSP

All-India A2+FL cost of cultivation and Minimum Support Price, Rs per
quintal of the crop's **marketed product** (paddy for rice, kapas for
cotton -- matching `YIELD_TO_SALEABLE_QTL_PER_HA`, see `docs/units.md`).

| crop | cost_rs_per_qtl | msp_rs_per_qtl | source |
|---|---|---|---|
| rice (paddy) | 1579 | 2369 | PIB KMS 2025-26 (PRID 2131983) |
| jowar (hybrid) | 2466 | 3699 | PIB KMS 2025-26 (PRID 2131983) |
| maize | 1508 | 2400 | PIB KMS 2025-26 (PRID 2131983) |
| tur | 5038 | 8000 | PIB KMS 2025-26 (PRID 2131983) |
| soybean | 3552 | 5328 | PIB KMS 2025-26 (PRID 2131983) |
| cotton (kapas, medium staple) | 5140 | 7710 | PIB KMS 2025-26 (PRID 2131983) |
| wheat | 1239 | 2585 | PIB RMS 2026-27; cost = MSP/2.09 (109% margin) |
| sugarcane | 173 | -- (FRP instead, see below) | CCEA FRP 2025-26, basic recovery 10.25% |

**Limitation**: rice/jowar/maize/tur/soybean/cotton cost figures come from
the same PIB Kharif Marketing Season (KMS) 2025-26 release as their MSP
(PRID 2131983), which reports cost-of-cultivation alongside the MSP
announcement. Wheat's cost was not available from an equivalent PIB Rabi
Marketing Season (RMS) 2026-27 release at the same level of detail, so it is
**derived**, not sourced directly: CACP's standard MSP-setting convention
targets cost + ~50% margin at minimum, but recent wheat MSPs have run
alongside cost at roughly a 109% margin (MSP / 2.09); this ratio is applied
to back out an estimated cost from the published MSP. This is a weaker,
derived figure -- flag it if wheat profit numbers look sensitive to cost
assumptions.

## Sugarcane: FRP, not MSP

Sugarcane has no MSP; it's sold to mills at the government-set **Fair and
Remunerative Price (FRP)**, which is also a per-quintal figure (technically
per-tonne of cane at a base recovery rate; `admin_price_rs_per_qtl=355`
here). `msp_rs_per_qtl` is blank for sugarcane by design --
`agriopt.models.price_model.expected_price("sugarcane")` returns this FRP
value directly (method `"FRP"`), not a forecast.

**Limitation**: FRP is paid per tonne of cane at a *base sugar recovery
rate* (10.25% for 2025-26 per CCEA), with a premium/discount for actual
recovery above/below that base -- the 355 figure here is the FRP at the
base rate, not necessarily what any given mill actually pays.

## Fertilizer (N, P2O5, K2O, kg/ha)

| crop | N | P2O5 | K2O | total | source | basis |
|---|---|---|---|---|---|---|
| rice | 81.7 | 24.3 | 13.1 | 119.1 | FAO 2005, Table 13 | actual_use_all_india |
| wheat | 99.6 | 30.2 | 6.9 | 136.7 | FAO 2005, Table 13 | actual_use_all_india |
| jowar | 29.2 | 14.2 | 4.1 | 47.5 | FAO 2005, Table 13 | actual_use_all_india |
| maize | 41.7 | 14.7 | 3.8 | 60.2 | FAO 2005, Table 13 | actual_use_all_india |
| tur | 20.9 | 13.3 | 2.0 | 36.2 | FAO 2005, Table 13 | actual_use_all_india |
| cotton | 89.5 | 22.6 | 4.8 | 116.9 | FAO 2005, Table 13 | actual_use_all_india |
| sugarcane | 124.8 | 44.0 | 38.3 | 207.1 | FAO 2005, Table 13 | actual_use_all_india |
| soybean | 20 | 60 | 20 | 100 | ICAR-IISS general recommendation | recommended_dose |

Full source: FAO (2005), "Fertilizer use by crop in India", Table 13.

**Limitations**:
- Seven of the eight crops' figures are **actual average all-India use**
  from the **2003/04** season (`fert_basis="actual_use_all_india"`) -- over
  two decades old, and an average, not Maharashtra-specific or a
  recommendation. Fertilizer use has almost certainly shifted since then
  (India's per-hectare NPK consumption has generally risen).
- Soybean uses a **different kind of figure**: ICAR-IISS's general
  *recommended* dose (`fert_basis="recommended_dose"`), not a historical
  usage average, because FAO (2005) Table 13 does not list soybean. Mixing
  a 2003/04 actual-use figure for most crops with a general recommendation
  for soybean means these numbers are not perfectly apples-to-apples across
  crops -- treat `fert_total_kg_ha` as an indicative input, not a precise
  Maharashtra-2025 figure.

## Water need (FAO TM3, unchanged from Phase 0/0.5)

`water_mm(crop)` returns the midpoint of `water_mm_min`/`water_mm_max`.

| crop | min | max | midpoint | source |
|---|---|---|---|---|
| rice | 450 | 700 | 575 | FAO TM3 (paddy, excl. percolation losses) |
| wheat | 450 | 650 | 550 | FAO TM3 (listed jointly as Barley/Oats/Wheat) |
| jowar | 450 | 650 | 550 | FAO TM3 (listed as Sorghum) |
| soybean | 450 | 700 | 575 | FAO TM3 |
| cotton | 700 | 1300 | 1000 | FAO TM3 |
| sugarcane | 1500 | 2500 | 2000 | FAO TM3 |
| maize | 500 | 800 | 650 | FAO TM3 |
| tur | 300 | 500 | 400 | **FAO TM3 (beans proxy)** -- new in Phase 2 |

**Limitation (tur)**: FAO TM3's crop water need table does not list tur
(pigeon pea / Arhar) directly. Phase 2 fills this gap with FAO TM3's
**"Bean"** entry (300-500mm) as a proxy -- pigeon pea is a legume with a
broadly similar water-need profile to common beans, but this is a proxy,
not a pigeon-pea-specific figure, and should be verified against a
legume-specific source before publication.

## Status

`load_reference()` now passes with no missing values for all 8 crops (water,
cost, fertilizer are fully populated; `msp_rs_per_qtl` is intentionally
blank only for sugarcane, `admin_price_rs_per_qtl` intentionally populated
only for sugarcane). Remaining caveats are documented above, not silently
hidden: all-India (not Maharashtra-specific) costs, 2003/04-vintage
fertilizer-use data for 7/8 crops, a derived (not sourced) wheat cost
figure, and a beans-proxy water figure for tur.
