# Viva questions and honest answers (30)

Written for: team members facing examiners. Answers are short on purpose - say them in your own words.
Numbers are from `KEY_NUMBERS.md` (row codes in brackets). When unsure, say "that is a limitation we list"
rather than guessing. Never claim more than the backtest shows.

---

## The project in one minute

**1. What does your project do?**
It recommends how a Maharashtra farmer should split land between eight crops, balancing profit, water,
fertilizer and optionally risk, within land, water and food-crop limits. In a four-year backtest it kept profit
about the same as the current regional crop mix while using about 39% less water [A2, A3].

**2. What is new or useful about it?**
It puts yield forecasts, price forecasts, government cost data, a water model and an optimizer in one open,
reproducible tool, and it tests the result honestly on past years. The usefulness is making the profit-water
trade-off visible, not a claim of higher profit.

## Results and honesty

**3. Why doesn't it beat the current mix on profit?**
It was never built only to maximise profit. It trades profit against water and fertilizer, and its planning
numbers are based on forecast prices, which are optimistic (planned +51.6% vs realized +0.6%) [A6]. A pure
profit-maximising plan does earn more (₹288,084 vs ₹230,769 per year) but uses the full water budget [A7].

**4. Is +0.6% profit a win?**
No - it is a tie, and we call it a tie. The point is the water: 38.9% less for the same profit [A3]. In two of the
four years AgriOpt earned more, in two less (`reports/results/backtest_summary_v2.md`, section 5).

**5. Why only four backtest years?**
Maharashtra's yield data in our dataset ends in 2019, so 2016-2019 are the only years we can score. With four years
no statistical test can reach the 5% level, so we report year-by-year differences instead and call it directional
evidence, not proof. A longer backtest is future work.

**6. Isn't your test just luck then?**
Four years cannot rule out luck. Two things help: the test never uses future information, and the result agrees
in direction with the planning model (less water, similar-or-better profit per unit of water). We state this as
a limitation.

**7. Your yield model is barely better than a 3-year average. Why use it?**
That is true: it beats a 3-year average on only 3 of 8 crops (rice, wheat, soybean) [C3]. We report it rather than
hide it. We kept it because it is trained on all-India data and also supports uncertainty intervals, and because
it was the best of the models we compared on validation data. The
backtest shows yield error is where money is lost (64-68% of the gap to perfect foresight [C4]), so improving it
is our top future task after cost data.

**8. Why does a simple "last price" forecast beat XGBoost?**
Market prices change slowly month to month, so the last price is a strong forecast, and we only have about
20 years of monthly data - not much for a machine-learning model. The two are not statistically different once we
treat crops as moving together (p = 0.07-0.08) [C2], so we use the simpler one.

**9. What are the "oracles" in your backtest?**
Imaginary planners who know the future: one knows both yields and prices (the upper bound), one only prices, one
only yields. They show how much profit is lost to forecast error and where: mostly yields.

## Data and assumptions

**10. Why all-India costs for Maharashtra?**
State-wise cost per hectare was not available to us in a usable form. We use all-India cost per quintal times
Maharashtra yield; for several crops the cost is derived from the published MSP margin, so margins are partly set
by policy. This is our biggest data limitation and the first thing we would fix (CACP state tables).

**11. Why sugarcane? Why does it appear so often?**
Sugarcane has the highest profit per hectare in the model (₹61,141 vs ₹24,328 for rice) and is a major
cash crop in Maharashtra. It needs a lot of water, so the water-aware plans use only a little of it. Its price is the
fixed government FRP (no market series), which understates its risk.

**12. How do you treat sugarcane's long growing period?**
It stays about 15 months, so its yield, water and fertilizer are scaled to a one-year basis; its price is FRP
minus ₹75 per quintal for harvesting and transport (₹280).

**13. What is net irrigation and how did you compute it?**
The water a crop needs minus the rain it can actually use, added month by month, so a very wet July does not
cover a dry September. Crop need comes from FAO tables and rain from IMD data. We spread the seasonal need
evenly over the season because we had no monthly profile - an assumption we state [E1].

**14. Why eight crops and a 10 ha farm?**
The eight are major Maharashtra crops that have usable yield and price data; 10 ha is a convenient model farm. Results
scale with farm size, but we did not test real farms.

**15. What is the current mix (B1)?**
The historical share of each crop in Maharashtra over the last five years, turned into hectares on the model
farm and built season by season so it uses all its land. It is the "what farmers do now" reference. When water
is cut it breaks the water limit, so we also compare with the closest feasible version (B1_SCALED).

## Methods

**16. What is a Pareto front and why NSGA-II?**
When goals conflict (more profit needs more water), there is no single best plan, but there is a set of
best compromises - the Pareto front. NSGA-II is a standard genetic algorithm that finds that whole set in one
run, so the farmer can see the trade-offs and pick one with a slider.

**17. If linear programming is exact, why use NSGA-II?**
For the standard three-objective problem all objectives are linear, so LP gives exact answers - and we use LP to
check NSGA-II and to polish the recommended plan onto the exact front (raw NSGA-II was 0.1-2.0% below it) [D4].
NSGA-II is kept because it returns the whole front in one run for the trade-off chart, and because the
risk-aware mode is non-linear, where LP does not apply.

**18. What does the risk-aware mode do and why is it experimental?**
It adds a fourth goal, risk, measured from 18-21 years of yearly revenue swings and how crops move together, and
minimises risk per rupee of profit. It is experimental because in the app's medium and large presets it puts
75-78% of profit on sugarcane, whose measured risk is understated by its fixed price [D6], and its recommended
plan moves about 0.7 ha per crop between random seeds [D8]. We do not recommend it for real decisions yet.

**19. Why "risk per rupee of profit"?**
Measured in absolute rupees, an empty field has zero risk, so an optimizer could look "safe" by leaving land
unplanted. Dividing by profit removes that loophole.

**20. What does "leak-free" or "no look-ahead" mean?**
Each year's plan uses only information that existed on 1 May of that year: yield model fitted on earlier years,
last known market prices, historical costs. Earlier we accidentally let winter-crop prices from October into a
May decision; we found and removed it (`reports/results/backtest_skill.md` shows it made AgriOpt look slightly
better).

**21. What are the conformal intervals?**
A recipe that puts an uncertainty band around a prediction with a guaranteed hit rate. Our 90% bands actually
covered 94.1% of Maharashtra test cases overall, but only 75% for cotton and tur [C5].

## Software and delivery

**22. How does the app work, and why a pre-built data file?**
The trained yield model is about 528 MB. One offline script runs the models and optimizer for all preset farms and
saves a single data file; the web app only reads it, so it starts fast and runs on free hosting.

**23. How did you check the software is correct?**
An automated test suite, including checks that costs are per hectare (not per quintal), that every returned plan
satisfies the constraints, that the app runs on the exact deployed software versions, and that the published
tables still match what the code computes from the stored data.

**24. Did you ever find mistakes in your own work?**
Yes, in a review after the first version: costs per quintal had been subtracted as if per hectare (so "profit"
was nearly revenue), sugarcane's 15-month cycle was not annualised, and several comparisons were unfair to the
baseline. We fixed them and re-ran everything; the old numbers are listed as "do not use" in `KEY_NUMBERS.md`
section 7, and the full history is in `reports/results/CHANGELOG_fixes.md`. Saying this is a strength.

## Scope and future

**25. Could a real farmer use this today?**
As a planning aid for discussion, yes; as a recommendation to follow blindly, no. It is state-level, uses
all-India costs, has no field validation, and ignores farmer constraints we cannot see (labour, soil, loans,
market access).

**26. What about food security?**
A constraint keeps food crops (rice, wheat, jowar, tur, maize) at least 30% of the cropped area; the
current-mix reference sits at 45%.

**27. Does it consider prices falling if many farmers follow it?**
No. Prices are taken as given; a market-feedback effect is outside the model and is a limitation.

**28. Why not deep learning?**
We have about two decades of yearly data per crop and state - far too little for deep learning to help. The
results show even Random Forest barely beats a 3-year average.

**29. Who chooses the weights between profit, water and fertilizer?**
The user, with the Profit-Sustainability slider; the default weights are 0.5 / 0.3 / 0.2.

**30. What would you do with more time?**
(1) Maharashtra-specific cost per hectare. (2) A better yield model using weather and district data. (3) A two-step
plan (commit monsoon crops in May, decide winter crops in October). (4) A longer backtest. (5) Field trials with
farmers and extension officers.

---

### If you are asked something not covered

Answer: "We did not test that; it is a limitation / future work." Do not improvise numbers. Offer to show the
file in `reports/results/`.
