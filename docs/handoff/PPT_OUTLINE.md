# PPT outline (14 slides, about 12-15 minutes)

Written for: students building the slides. Bullets are short on purpose (max 8 words each). Speaker notes are
what to say. Image paths are inside `docs/handoff/figures/` (captions in `FIGURES.md`). Numbers are from
`KEY_NUMBERS.md` (row codes in brackets). Fill in `[TEAM NAMES]`, `[GUIDE NAME]`, `[INSTITUTION NAME]`.

---

### Slide 1 - Title
- **AgriOpt: Water-aware crop planning for Maharashtra**
- `[TEAM NAMES]` | Guide: `[GUIDE NAME]` | `[INSTITUTION NAME]`
- Image: none (or the logo of your college)
- Notes: Introduce yourselves. One line: "We built a tool that suggests how a farmer should split land between crops,
  using less water without losing profit."

### Slide 2 - The problem
- Farmers choose crops by habit
- Water is limited and uneven
- Profit-only advice picks thirsty crops
- Trade-offs are hard to see
- Image: none (add a photo of a Maharashtra farm if you have a licensed one)
- Notes: Maharashtra grows cotton, soybean, sugarcane, rice and more. Sugarcane earns well but needs about
  2,000 mm of water. A farmer needs to see profit, water, fertilizer and risk together.

### Slide 3 - Our idea
- Recommend hectares per crop
- Balance profit, water, fertilizer, risk
- Respect land and food-crop limits
- Test it on past years
- Image: `fig02_how_it_works.png`
- Notes: Walk left to right: data, models, per-hectare economics, optimizer, cached results, web app.

### Slide 4 - Data we used
- Yield: 19,689 rows, 1997-2020 [B1]
- Mandi prices: 7 crops, 2001-2025 [B4]
- Rainfall: IMD, last 30 years [B5]
- Cost, MSP, water need, fertilizer
- Image: `reports/eda/yield_over_years_by_crop.png`
- Notes: All public sources. Sugarcane has no market price, so we use the government's fixed price (FRP).
  Be upfront: costs are all-India figures.

### Slide 5 - Predicting yield and price
- Yield: Random Forest (many trees)
- Price: last price vs XGBoost
- Last-price forecast was never worse [C1]
- Yield model ~ a 3-year average [C3]
- Image: `fig07_yield_vs_baseline.png`
- Notes: This is a negative result and we say so. The yield model beats a 3-year average on 3 of 8 crops.
  Simple price forecasts are hard to beat. This is why the backtest matters.

### Slide 6 - Turning forecasts into profit per hectare
- Profit = yield x price - cost
- Sugarcane: 15-month crop, annualised
- Sugarcane price: Rs 355 - Rs 75 = Rs 280/qtl
- Sugarcane ~Rs 61,000/ha, rice ~Rs 24,000/ha
- Image: none (small table from `KEY_NUMBERS.md` section 3)
- Notes: One function builds these numbers for the app and the tests. Jowar earns only about Rs 1,200/ha, so
  it is rarely chosen.

### Slide 7 - The optimizer
- NSGA-II finds many best trade-offs
- Exact math (LP) checks it
- Final plan is polished onto the exact front
- Image: `fig04_pareto_front.png`
- Notes: Each dot is a possible plan. Moving right earns more but uses more water. Blue star = our recommended
  plan; red square = the current crop mix, which sits far from the best frontier.

### Slide 8 - What the plan looks like
- Current mix: 8 crops, spread out
- AgriOpt: about 3 crops
- More rice, wheat, some sugarcane
- Image: `fig05_allocation_by_crop.png`
- Notes: The bars are hectares per crop (a crop that lives in both seasons counts once, so a bar can exceed
  10 ha). B2 is the profit-max plan; B3 is "same profit, least water".

### Slide 9 - Honest test: the backtest
- Plan each year from past data only
- Then score against what happened
- Years 2016-2019 (four years)
- 10 ha model farm
- Image: `fig06_backtest_profit_by_year.png`
- Notes: "Leak-free" means we never use future information. The grey/top lines are oracles that know the future,
  the upper limit. Only four years because yield data end in 2019.

### Slide 10 - Headline result
- Profit: Rs 230,769 vs Rs 229,479 [A2]
- Water: 38.9% less [A3]
- 1.7x profit per unit water [A4]
- Image: `fig03_headline_water_profit.png`
- Notes: Say it carefully: "same profit, much less water". We do not claim higher profit. The profit-max plan
  earns more (Rs 288,084) but uses all the water [A7].

### Slide 11 - Different regions, same water
- Same water budget in every region
- Konkan best, Marathwada lowest [E2]
- Dry year hits Marathwada hardest [E3]
- Image: `fig08_regions_equal_budget.png`
- Notes: An earlier version gave rainy regions smaller budgets, which flipped the result. Equal budgets is the
  fair comparison.

### Slide 12 - Live demo
- Open the live app (link below)
- Click a farmer preset
- Check the Trade-offs and Backtest tabs
- Images: `fig12_app_recommendation.png`, `fig13_app_tradeoffs.png`, `fig14_app_regional.png`
- Notes - **what to click** (live: https://agriopt-bmuud9kclfctcmxrb3abce.streamlit.app):
  1. On the left, under "Farmer profile", click **"Medium mixed"**. The Recommendation tab shows hectares per
     crop, profit, water, fertilizer, food share and profit risk, plus a plain-English sentence.
  2. Open the **Trade-offs** tab: the Pareto chart with the recommended plan (star) and the current mix (red square).
  3. Open **Strategy comparison** to compare the four plans side by side.
  4. Open **Backtest (2016-2019)** to show the year-by-year results.
  5. Move the **Water budget** slider down and press **Run**: show how the plan changes.
  6. Optional: switch **Risk-aware** on (label it "experimental").
  Have the screenshots (`fig12`-`fig14`) ready in case the internet fails; free apps can take a minute to wake up.

### Slide 13 - Limitations (be upfront)
- Only four scored years
- All-India costs, not Maharashtra's
- Yield model barely beats an average
- Risk-aware mode is experimental
- Image: none
- Notes: Examiners respect honesty. Say: the sign is right (same profit, less water) but four years is not
  proof. Risk-aware mode puts 75-78% of profit on sugarcane in some presets [D6], so we do not recommend it yet.

### Slide 14 - Future work and conclusion
- Maharashtra-specific cost per hectare
- Better yield model
- Two-stage planning (May / October)
- Field trials with farmers
- Image: none (or `fig01_architecture.png` as a closing summary)
- Notes: Conclusion in one sentence: "AgriOpt keeps profit about the same as the current crop mix while using
  about 36-39% less water, and it is honest about what it cannot yet do." Thank the guide. Questions.

---

## Design tips

- One message per slide. Put the number big (the headline slide shows +0.6% and -38.9%).
- Use the same two colours as the figures (blue = AgriOpt, grey = current mix).
- Put the repository link and the live demo link on the last slide.
- Do not paste tables of more than 5 rows; link to `reports/results/` instead.
- If a figure has small text (`fig04`, `fig06`), crop or zoom in PowerPoint rather than shrinking it.
