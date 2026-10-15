# Literature and references

Every reference below was checked against a bibliographic database (Crossref) or the publisher /
official site while this pack was written. Items that could only be partly checked say so. BibTeX
entries are in `references.bib` (same keys as in brackets here).

How to cite: use the style your college asks for ([COLLEGE FORMAT]). The BibTeX file works with IEEE
and Springer styles.

---

## A. Optimization methods

**[deb2002nsga2]** Deb, K., Pratap, A., Agarwal, S., Meyarivan, T. (2002). A fast and elitist multiobjective
genetic algorithm: NSGA-II. *IEEE Transactions on Evolutionary Computation*, 6(2), 182-197.
DOI: 10.1109/4235.996017.
*Summary:* Introduces NSGA-II, a genetic algorithm that finds a whole set of best trade-off solutions (the
Pareto front) quickly, keeps the best solutions between generations, and spreads them out evenly.
*Used in:* Methodology (optimizer), Related Work, Viva.

**[deb2014nsga3]** Deb, K., Jain, H. (2014). An evolutionary many-objective optimization algorithm using
reference-point-based nondominated sorting approach, Part I: Solving problems with box constraints.
*IEEE Transactions on Evolutionary Computation*, 18(4), 577-601. DOI: 10.1109/TEVC.2013.2281535.
*Summary:* NSGA-III extends NSGA-II to problems with more than three objectives using a set of reference
directions. AgriOpt uses it for the four-objective risk-aware mode (profit, water, fertilizer, risk).
*Used in:* Methodology (risk-aware optimizer).

**[blank2020pymoo]** Blank, J., Deb, K. (2020). pymoo: Multi-objective optimization in Python. *IEEE Access*,
8, 89497-89509. DOI: 10.1109/ACCESS.2020.2990567.
*Summary:* The Python library the project uses for NSGA-II and NSGA-III.
*Used in:* Implementation.

**[zitzler1999hv]** Zitzler, E., Thiele, L. (1999). Multiobjective evolutionary algorithms: a comparative case
study and the strength Pareto approach. *IEEE Transactions on Evolutionary Computation*, 3(4), 257-271.
DOI: 10.1109/4235.797969.
*Summary:* Introduced the hypervolume measure of how good a Pareto front is. The project reports hypervolume
to compare NSGA-II against an exact linear-programming reference front.
*Used in:* Experiments (front quality).

**[sarker2009crop]** Sarker, R., Ray, T. (2009). An improved evolutionary algorithm for solving multi-objective
crop planning models. *Computers and Electronics in Agriculture*, 68(2), 191-199.
DOI: 10.1016/j.compag.2009.06.002.
*Summary:* Treats crop planning as a multi-objective problem (gross margin versus working capital) solved with
evolutionary algorithms. The closest published relative of AgriOpt's formulation.
*Used in:* Related Work. (Bibliographic details checked in Crossref; the paper's text was not read for this
pack, so read it before describing its method in detail.)

**[markowitz1952]** Markowitz, H. (1952). Portfolio selection. *The Journal of Finance*, 7(1), 77-91.
DOI: 10.2307/2975974.
*Summary:* The idea of measuring the risk of a mix of assets with a covariance matrix. AgriOpt's risk model
applies the same idea to a mix of crops (revenue covariance across years).
*Used in:* Methodology (risk model).

## B. Prediction models and statistics

**[breiman2001rf]** Breiman, L. (2001). Random forests. *Machine Learning*, 45(1), 5-32.
DOI: 10.1023/A:1010933404324.
*Summary:* Defines the Random Forest, an average of many decision trees. It is the yield model.
*Used in:* Methodology (yield model).

**[chen2016xgboost]** Chen, T., Guestrin, C. (2016). XGBoost: A scalable tree boosting system. In *Proceedings
of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining* (pp. 785-794).
DOI: 10.1145/2939672.2939785.
*Summary:* The gradient-boosted tree method used as the machine-learning price model (and compared with
Random Forest for yield).
*Used in:* Methodology (price model).

**[diebold1995dm]** Diebold, F. X., Mariano, R. S. (1995). Comparing predictive accuracy. *Journal of Business &
Economic Statistics*, 13(3), 253-263. DOI: 10.1080/07350015.1995.10524599.
*Summary:* A statistical test of whether one forecast is really more accurate than another or the difference
could be luck.
*Used in:* Experiments (price significance).

**[harvey1997hln]** Harvey, D., Leybourne, S., Newbold, P. (1997). Testing the equality of prediction mean
squared errors. *International Journal of Forecasting*, 13(2), 281-291. DOI: 10.1016/S0169-2070(96)00719-4.
*Summary:* A small-sample correction to the Diebold-Mariano test, which AgriOpt applies.
*Used in:* Experiments (price significance).

**[lei2018conformal]** Lei, J., G'Sell, M., Rinaldo, A., Tibshirani, R. J., Wasserman, L. (2018).
Distribution-free predictive inference for regression. *Journal of the American Statistical Association*,
113(523), 1094-1111. DOI: 10.1080/01621459.2017.1307116.
*Summary:* Split conformal prediction: a simple way to put an uncertainty band around any model's prediction
with a guaranteed coverage rate. The yield intervals use this recipe.
*Used in:* Methodology (yield uncertainty).

**[angelopoulos2023conformal]** Angelopoulos, A. N., Bates, S. (2023). Conformal prediction: a gentle
introduction. *Foundations and Trends in Machine Learning*, 16(4), 494-591. DOI: 10.1561/2200000101.
(Preprint: arXiv:2107.07511.)
*Summary:* A readable tutorial on conformal prediction, good for explaining it to non-specialists.
*Used in:* Methodology (yield uncertainty), Viva. (Details confirmed from the arXiv listing and the journal
reference it gives; the DOI itself was not opened.)

**[lundberg2017shap]** Lundberg, S. M., Lee, S.-I. (2017). A unified approach to interpreting model predictions.
In *Advances in Neural Information Processing Systems 30* (NIPS 2017). arXiv:1705.07874.
*Summary:* SHAP values, used to show which inputs drive the model (figure
`reports/results/shap_summary_xgb.png`, which is for the XGBoost model, not the deployed Random Forest).
*Used in:* Results (optional).

**[hyndman2021fpp3]** Hyndman, R. J., Athanasopoulos, G. (2021). *Forecasting: Principles and Practice*
(3rd ed.). OTexts, Melbourne. Free online: https://otexts.com/fpp3/
*Summary:* Standard textbook; explains the "naive" and "seasonal naive" forecasts used as baselines.
*Used in:* Methodology (price model), Viva.

## C. Agriculture: yield prediction, water and fertilizer

**[vanklompenburg2020yield]** van Klompenburg, T., Kassahun, A., Catal, C. (2020). Crop yield prediction using
machine learning: a systematic literature review. *Computers and Electronics in Agriculture*, 177, 105709.
DOI: 10.1016/j.compag.2020.105709.
*Summary:* Reviews 50 machine-learning studies on yield prediction; temperature, rainfall and soil type are the
most used inputs. Good background for the literature review.
*Used in:* Literature review.

**[jeong2016rf]** Jeong, J. H., Resop, J. P., Mueller, N. D., et al. (2016). Random forests for global and
regional crop yield predictions. *PLOS ONE*, 11(6), e0156571. DOI: 10.1371/journal.pone.0156571.
*Summary:* Shows Random Forests predict crop yields well at global and regional scale, supporting the choice
of Random Forest for the yield model.
*Used in:* Literature review, Methodology.

**[allen1998fao56]** Allen, R. G., Pereira, L. S., Raes, D., Smith, M. (1998). *Crop evapotranspiration:
Guidelines for computing crop water requirements*. FAO Irrigation and Drainage Paper 56. FAO, Rome.
ISBN 92-5-104219-5. https://www.fao.org/3/X0490E/x0490e00.htm
*Summary:* The standard method for crop water requirements. AgriOpt itself uses the simpler FAO TM3 tables
(next entry); cite FAO-56 as the general background.
*Used in:* Methodology (water), Literature review.

**[brouwer1986tm3]** Brouwer, C., Heibloem, M. (1986). *Irrigation Water Management: Irrigation Water Needs*.
FAO Training Manual No. 3. FAO, Rome. https://www.fao.org/4/S2022E/s2022e00.htm
*Summary:* The source of the crop water-need ranges (mm) the project uses, and of the water needed to prepare
paddy fields.
*Used in:* Methodology (water).

**[dastane1978rain]** Dastane, N. G. *Effective rainfall in irrigated agriculture*. FAO Irrigation and Drainage
Paper 25, FAO, Rome. https://www.fao.org/4/X5560E/X5560E00.htm
*Summary:* Background for the effective-rainfall formula (USDA-SCS method) used to decide how much of the rain
a crop can really use. Year: the FAO online edition shows (c) FAO 1978; library catalogues list 1974 - use the
year your citation style requires after checking the FAO page.
*Used in:* Methodology (water).

**[fao2005fert]** FAO (2005). *Fertilizer use by crop in India* (compiled by R. K. Tewatia and T. K. Chanda,
Fertiliser Association of India). Land and Water Development Division, FAO, Rome.
https://www.fao.org/4/a0257e/A0257E00.htm
*Summary:* Source of the fertilizer-dose figures (kg per hectare) for 7 of the 8 crops (2003/04 all-India use).
*Used in:* Data sources, Limitations (the figures are old).

## D. Data and institutional sources (cite as "data sources", not as papers)

**[ceda_agmarknet]** CEDA, Ashoka University. *CEDA Agri Market Data / Agmarknet API* (daily mandi prices, from
the Ministry of Agriculture's Agmarknet). https://agmarknet.ceda.ashoka.edu.in and https://api.ceda.ashoka.edu.in/
*Used for:* the price model (monthly modal price, Rs/quintal). *Used in:* Data sources.

**[imd_rainfall]** India Meteorological Department (IMD) sub-divisional monthly rainfall 1901-2015, as published
on Kaggle (`rajanand/rainfall-in-india`). *Used for:* effective rainfall and net irrigation.
*Note:* the Kaggle page itself was not opened while writing this pack (a mirror listing confirmed IMD as the
source and 1901-2015 as the span). The data check done in the project (all four Maharashtra subdivisions
present, complete months) is in `docs/water.md` section 1.

**[iitm_areas]** Indian Institute of Tropical Meteorology (IITM), Pune. *IITM Indian regional/subdivisional
monthly rainfall data set* (file iitm-subdivrf.txt; subdivision areas used to area-weight the state average).
https://www.tropmet.res.in/data/data-archival/rain/iitm-subdivrf.txt (file exists; confirmed).
*Used in:* Methodology (water), `docs/water.md` section 8.1.

**[kaggle_yield]** Kaggle dataset `akshatgupta7/crop-yield-in-indian-states-dataset` (area, production, yield by
state, crop, season, year; 1997-2020). Named in `scripts/00_download.ps1`. *Used for:* the yield model.
*Note:* the original source of the numbers is the Government of India's agricultural statistics; the Kaggle
page itself was not opened for this pack, so describe it as "a Kaggle compilation" and check the page's
stated source before the final report.

**[kaggle_mandi]** Kaggle dataset `arjunyadav99/indian-agricultural-mandi-prices-20232025` (secondary price
source; only rice and wheat of the 8 crops). Named in `scripts/00_download.ps1`.

**[cacp]** Commission for Agricultural Costs and Prices (CACP), Government of India. *Price Policy* reports
(separate reports for Kharif crops, Rabi crops and sugarcane). The CACP advises the government on MSP; its
reports contain the cost-of-cultivation tables. (Existence of the report series confirmed through a public
library copy of "Price Policy for Kharif Crops: The Marketing Season 2017-18", ruralindiaonline.org; the
official CACP site was not reachable during checking.)
*Used in:* Data sources, Limitations, Future work (state-wise costs).

**[pib_msp_2025]** Press Information Bureau (PIB), Government of India. Cabinet approval of MSP for Kharif
crops, marketing season 2025-26 (PRID 2131983, as cited in `data/reference/crop_reference.csv`).
*Note:* the PIB page returned an access error during checking, so the cost-of-production figures could not be
read there. Press coverage confirms the date (28 May 2025), the paddy MSP of Rs 2,369/quintal and the policy of
MSP = 1.5 x cost, **but two outlets disagree on paddy's cost figure** (Rs 1,579 vs Rs 1,310 per quintal).
Open the PIB release yourself before quoting any cost number in the report.

**[ccea_frp_2025]** Cabinet Committee on Economic Affairs (CCEA). Fair and Remunerative Price of sugarcane,
sugar season 2025-26: Rs 355 per quintal at 10.25% recovery (announced 30 April 2025), with a production cost
of Rs 173 per quintal quoted by the government. (Confirmed through several news reports citing the release;
the PIB release itself was not opened.)

---

## Dropped (could not be verified)

- None of the 20 papers/books above was dropped, but see the notes marked "not opened" or "confirm": Angelopoulos & Bates (DOI not opened), Dastane (year), the Kaggle pages and the PIB release.
- No reference was invented. If you add one, verify title, authors, year, venue and DOI/URL first.
- The README cites a ChiniMandi article for the sugarcane harvesting-and-transport deduction (Rs 75/quintal).
  It is a trade-news page, not a scientific source; cite it only as "trade press" and state the figure is an
  assumption for the Pune/Nashik divisions in 2023-24.
