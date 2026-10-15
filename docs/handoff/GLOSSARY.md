# Glossary (plain language)

Written for: non-coders. Use these explanations the first time a term appears in the report, paper or slides.

## Farming and policy terms

- **Kharif** - the monsoon crop season (roughly June to October). Rice, soybean, cotton, tur, maize.
- **Rabi** - the winter crop season (roughly November to March). Wheat, jowar (in this project).
- **Hectare (ha)** - 10,000 square metres; about 2.5 acres.
- **Quintal (qtl)** - 100 kilograms. Prices and costs are quoted per quintal.
- **Mandi** - a wholesale agricultural market. "Modal price" = the most common price on a day or month there.
- **MSP (Minimum Support Price)** - the price the government announces for 23 crops, at which it will buy.
  Based on the Commission for Agricultural Costs and Prices' advice.
- **FRP (Fair and Remunerative Price)** - the minimum price sugar mills must pay for sugarcane. Sugarcane has no
  MSP; this project uses FRP (Rs 355/quintal for 2025-26).
- **H&T deduction** - harvesting and transport cost taken off the sugarcane price (Rs 75/quintal here), because
  the farmer does not receive it.
- **CACP** - Commission for Agricultural Costs and Prices, the government body that studies costs and advises on MSP/FRP.
- **A2+FL cost** - a standard cost-of-cultivation measure: paid-out costs (A2) plus the value of unpaid family
  labour (FL). Used in this project (per quintal, all-India).
- **Net irrigation** - the water a crop needs minus the rain it can use, i.e. what must come from irrigation.
- **Effective rainfall** - the part of rain a crop can actually use (the rest runs off or drains away).
- **Food-crop share** - minimum fraction of the cropped area that must be food crops (30% by default).
- **Cropping seasons for long crops** - cotton, tur and sugarcane stay in the ground into the second season,
  so they use land in both seasons in the model.

## Optimisation terms

- **Objective** - something to improve (more profit, less water).
- **Constraint** - a rule that must hold (land limit, water budget, minimum food share).
- **Multi-objective optimisation** - choosing a plan when several goals conflict.
- **Pareto front** - the set of plans where you cannot improve one goal without making another worse. The
  "menu" of best trade-offs.
- **NSGA-II** - a genetic algorithm (it "evolves" plans over many generations) that finds a whole Pareto front.
- **NSGA-III** - a variant for more than three objectives; used here for the four-objective risk-aware mode.
- **LP (linear programming)** - an exact maths method for problems where everything is a straight-line
  relationship. Here it checks NSGA-II and polishes its answer.
- **Hypervolume / IGD** - two scores for how good and how well-spread a Pareto front is.
- **Pseudo-weights** - a way to pick one plan from the front that matches the user's preferred balance
  (profit, water, fertilizer).
- **Risk-aware mode** - the experimental mode that also tries to lower risk.
- **Covariance / correlation** - how much two crops' revenues move together (+1 = always together).
- **Risk per rupee of profit** - portfolio risk divided by expected profit; stops the model from looking "safe" by
  leaving land empty.

## Prediction and statistics terms

- **Random Forest** - a model that averages many decision trees. Our yield model.
- **XGBoost** - a boosted-tree model. One of our price models.
- **Naive forecast** - predict that the next price equals the last known price. **Seasonal-naive** - same month last year.
- **Baseline** - a simple reference every fancy model must beat.
- **MAE / MAPE** - average error (in the same units / in percent). Lower is better.
- **Conformal interval** - an uncertainty band around a prediction with a guaranteed hit rate (we target 90%).
- **Diebold-Mariano test** - a test of whether one forecast is really more accurate than another or just lucky.
  A p-value below 0.05 is usually called "significant".
- **p-value** - the chance of seeing a difference this big if there were really none. Small = unlikely to be luck.
- **Bootstrap** - re-shuffling the data many times to see how much a result could vary.
- **Look-ahead bias** - accidentally using information from the future when making a past decision; makes results
  look better than real.
- **Leak-free** - a test designed so no future information is used.

## Names used in the result files

- **Current mix = B1** - the historical share of crops in Maharashtra, on the model farm.
- **B1_SCALED** - the closest version of B1 that obeys the water and food limits.
- **B2** - the plan that maximises profit only.
- **B3** - the plan that keeps B1's profit with the least water.
- **OURS (AgriOpt)** - the recommended plan from NSGA-II, polished by LP.
- **MODEL_B** - the risk-aware plan from NSGA-III.
- **ORACLE** - an imaginary planner who knows the true yields and prices; **ORACLE_PRICE** knows only prices,
  **ORACLE_YIELD** only yields. They show the best possible and where forecasts lose money.
- **Backtest** - pretending to be in the past: plan with only the information then available, then check what
  actually happened.
- **Capture ratio** - a plan's realized profit divided by the oracle's (1.0 = as good as perfect foresight).
- **Default / tight water** - default budget = the current mix's own water use; tight = 70% of it.
- **Preset** - a ready-made farmer example in the app (small rainfed, medium mixed, large irrigated, drought year,
  Marathwada drought).
- **Cache** - the single pre-computed data file (`data/processed/crop_params_cache.json`) the app reads, so it never loads the
  big trained models.
- **Planning-time vs realized** - "planned" numbers use forecasts; "realized" numbers use what actually happened.
  Only realized numbers should be quoted as evidence.
