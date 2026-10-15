# Start here (for the report, paper and PPT team)

You do not need to run any code. Everything you need is in this folder (`docs/handoff/`) and in the
files it points to. If something here disagrees with an older draft, slide or message, **this folder wins**.

## What AgriOpt is (5 lines)

1. AgriOpt is a decision-support tool that suggests how a Maharashtra farmer should split land between 8 crops
   (rice, wheat, jowar, soybean, cotton, sugarcane, tur, maize).
2. It balances four things at once: profit, water used, fertilizer used, and (optionally) risk, while keeping
   a minimum share of food crops.
3. It combines a yield model, a price model and government reference data (cost, MSP, water need, rainfall).
4. It was tested with a "backtest" on 2016-2019: it keeps profit about the same as the current crop mix while
   using about 36-39% less water. **It does not claim higher profit than the current mix.**
5. It is delivered as a Streamlit web app (live demo link below).

**Live demo:** https://agriopt-bmuud9kclfctcmxrb3abce.streamlit.app
(If it shows an error, wait one minute and reload; free apps go to sleep.)

**Code and results:** the GitHub repository this folder is in.

## Who should read what

| You are writing... | Read first | Then |
|---|---|---|
| Anything (everyone) | `KEY_NUMBERS.md` | `GLOSSARY.md` |
| The project **report** | `REPORT_GUIDE.md` | `LITERATURE_AND_REFERENCES.md`, `FIGURES.md` |
| The **research paper** | `RESEARCH_PAPER_GUIDE.md` | `LITERATURE_AND_REFERENCES.md`, `references.bib` |
| The **PPT** | `PPT_OUTLINE.md` | `FIGURES.md`, `VIVA_QA.md` |
| Preparing for the **viva** | `VIVA_QA.md` | `KEY_NUMBERS.md` |

## Five rules for the whole team

1. **Use only numbers from `KEY_NUMBERS.md`.** Each one lists its source file. Do not copy numbers from old
   slides or from memory. Section 7 of that file lists old numbers that are now wrong.
2. **Say what the tool does honestly:** same profit, much less water. Do not write "maximises profit",
   "beats the current mix on profit", or "predicts yields accurately".
3. **Say what the backtest is:** four years (2016-2019), a 10 ha model farm, using only information that was
   available before each year. It is evidence, not proof.
4. **Do not invent anything.** Missing items are marked `[TEAM NAMES]`, `[GUIDE NAME]`, `[COLLEGE FORMAT]` -
   fill them in yourselves.
5. **Explain every technical term on first use** (the glossary has plain-English versions).

## Map of the repository

| Folder / file | What is inside | Who needs it |
|---|---|---|
| `README.md` | Overview, the key-results table, how to reproduce everything | everyone (read the top) |
| `docs/handoff/` | This pack: numbers, guides, glossary, figures, references | everyone |
| `docs/handoff/figures/` | Ready-to-use PNG figures with captions (`FIGURES.md`) | report, paper, PPT |
| `docs/formulation.md` | The optimisation problem written out (objectives, constraints, baselines) | report/paper: Methodology |
| `docs/reference_data.md` | Where cost, MSP, fertilizer and water-need numbers come from, with their limits | report: Data, Limitations |
| `docs/units.md` | How yields are converted to quintals of marketed product (rice, cotton assumptions) | report: Methodology |
| `docs/water.md` | The water model: effective rain, net irrigation, regions (long) | report/paper: Methodology (water) |
| `docs/backtest.md` | How the backtest avoids "looking into the future" | report/paper: Methodology (backtest) |
| `docs/img/` | Screenshots of three app tabs | PPT demo slides |
| `reports/results/` | **All result files** (tables as markdown and CSV files, charts as PNG images). Start with `RESULTS_INDEX.md` | report/paper: Results |
| `reports/results/CHANGELOG_fixes.md` | History of the corrections made after a review, with before/after numbers | anyone asking "why did this number change?" |
| `reports/eda/` | Data audit: dataset sizes, coverage, outliers, plots | report: Data |
| `app/` | The Streamlit web app (one file per tab in `app/components/`) | report: Implementation |
| `src/agriopt/` | The real code: `src/agriopt/models/` (yield, price), `src/agriopt/optim/` (economics, optimizer, risk), `src/agriopt/data/` (loaders, rainfall), `src/agriopt/backtest/`, `src/agriopt/stats/` | report: Implementation (skim names only) |
| `scripts/` | Numbered scripts that produce the results (10 train yield, 20 train price, 30 optimizer, 31 risk, 50 ablation, 60-62 backtest, 70-71 water, 90-95 statistics, 40 builds the app's data file) | report: Reproducibility |
| `data/reference/` | Hand-collected tables: `crop_reference.csv` (cost, water, fertilizer), `msp_history.csv` (MSP by year with sources) | report: Data |
| `data/processed/crop_params_cache.json` | The single data file the app reads | report: Architecture |
| `tests/` | Automated checks (the project's quality control) | report: Testing |
| `requirements*.txt`, `pyproject.toml` | Software lists (not needed for writing) | nobody |

Not in the repository (large, downloaded separately): the raw datasets and the trained models. You never
need them to write the documents.

## If you get stuck

- "Where does this number come from?" -> `KEY_NUMBERS.md`, the "Source" column.
- "Why did the number change?" -> `reports/results/CHANGELOG_fixes.md`.
- "What does this word mean?" -> `GLOSSARY.md`.
- "A teacher asks something hard." -> `VIVA_QA.md`.

Placeholders you must fill in yourselves: `[TEAM NAMES]`, `[GUIDE NAME]`, `[COLLEGE FORMAT]`,
`[INSTITUTION NAME]`, `[DATE]`.
