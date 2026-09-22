# Units: dataset Yield -> quintals of marketed product per hectare

The Kaggle yield dataset (`crop-yield-in-indian-states-dataset`) does not
document the units behind its `Yield`/`Production` columns. This note records
what the Phase 0.5 unit audit (`reports/eda/eda_report.md`, "Unit audit"
section; logic in `agriopt.data.yield_data.unit_audit`) found, what it could
and could not prove, and the resulting conversion implemented in
`agriopt.config.YIELD_TO_SALEABLE_QTL_PER_HA`.

## What the audit checked

For each target crop, on Maharashtra rows with `Area > 0`:

```
ratio = Yield / (Production / Area)
```

Result: every target crop's `ratio` median falls in **0.88-1.09** (IQR
roughly 0.8-1.2). This means `Yield`, `Production`, and `Area` are **mutually
self-consistent** within the dataset -- `Yield` really is (approximately)
`Production / Area` in whatever basis `Production` uses, for every crop, not
just some.

## What it does NOT prove

A ratio near 1 is compatible with *any* consistent choice of real-world
quantity. It cannot tell us whether "Yield" for rice means paddy or milled
rice, or whether "Yield" for cotton means kapas (raw seed cotton), lint, or
bales of lint -- all of those would still show ratio ~= 1 as long as
`Production` was computed on the same basis as `Yield`. Resolving that
requires an external sanity check, not just internal consistency.

## Per-crop conversions

### Rice: milled rice -> paddy (ASSUMPTION)

`RICE_OUTTURN = 0.67`. Standard Indian milling outturn: 100 kg paddy yields
~67 kg milled rice. We assume the dataset's rice `Yield` is already
milled-rice-equivalent (a common convention in Indian ag-production tables),
so:

```
paddy_t_ha = Yield / RICE_OUTTURN
paddy_quintal_ha = paddy_t_ha * 10
```

Maharashtra median rice Yield is ~2.0 t/ha; as paddy that's ~3.0 t/ha, a
plausible (if slightly low, consistent with mostly-rainfed area) paddy yield
for the state. Marketed product for the price model is **paddy** (that's
what CEDA's `Paddy(Dhan)(Common)` series prices), which is why
`CROP_NAME_MAP["rice"]["ceda_commodity"]` points at the paddy series rather
than CEDA's separate milled-`Rice` commodity.

This is flagged ASSUMPTION because the unit audit's ratio~1 result is
equally compatible with `Yield` already being paddy (no conversion needed).
**Verify before paper** -- e.g. against a known-paddy reference series for
Maharashtra.

### Cotton: lint bales -> kapas (ASSUMPTION)

`GINNING_OUTTURN = 0.34`, `BALE_KG = 170`. Indian cotton production is
conventionally reported in bales (170 kg of lint each); ginning outturn
(lint as a fraction of kapas, raw seed cotton) is typically ~33-35%.

The unit audit's `Production` magnitude check supports the bales
interpretation specifically: Maharashtra's median `Production` for cotton is
~4.6 million. India's *entire national* lint cotton production is on the
order of 30-34 million bales/year; ~4.6M tonnes for one state would be
absurd (roughly the size of national production), but ~4.6M bales for
Maharashtra -- one of India's largest cotton-growing states -- is a
plausible order of magnitude. Combined with ratio~1 (so `Yield` shares
`Production`'s basis), this means the dataset's cotton `Yield` is most
plausibly **bales/ha**, not tonnes/ha as the column name might suggest.

Sanity check on the resulting real-world yield: `Yield` median 1.45
bales/ha -> 1.45 * 170 = 247 kg lint/ha -> 2.47 quintal/ha kapas after
ginning. Actual Maharashtra lint cotton yields run roughly 300-500 kg/ha, so
this lands in a believable range. (Treating `Yield` as tonnes/ha directly
would imply ~14.5 quintal/ha lint -- 3-5x too high to be plausible.)

```
lint_kg_ha = Yield_bales_ha * BALE_KG
kapas_kg_ha = lint_kg_ha / GINNING_OUTTURN
kapas_quintal_ha = kapas_kg_ha / 100
```

Marketed product = kapas (raw seed cotton, what farmers actually sell and
what CEDA's `Cotton` commodity series prices). **Verify before paper.**

### Everyone else: tonnes/ha -> quintals/ha

Wheat, jowar, soybean, sugarcane, tur, maize: no unit ambiguity found (ratio
~= 1, and the resulting t/ha `Yield` values are all in plausible ranges for
their respective crops), so:

```
quintal_ha = Yield_t_ha * 10
```

## STOP condition (not triggered)

Per the audit script's sanity check
(`scripts/01_audit_yield.py: UNIT_RATIO_SANITY_BAND = (0.5, 2.0)`): if any
crop's `ratio_median` had fallen outside 0.5-2.0x, that would mean `Yield`
and `Production/Area` disagree by more than 2x for that crop -- not
explainable by a milling/ginning factor, and a sign something is more
seriously wrong (e.g. mixed units within a single column). That did not
happen for any of the 8 target crops; all medians landed between 0.88 and
1.09.
