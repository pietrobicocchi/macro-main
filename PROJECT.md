# PROJECT.md

The living scientific state of this project: what we are investigating, and what
we currently know. **Update this file in place; never append to it as a log.**
Git remembers what happened.

## Question

Can this model produce credible macro dynamics, and forecast real GDP, inflation,
household consumption, government consumption and investment better than an
AR(1) benchmark and the IIASA/Poledna model, as the paper claims (Table
`table:forecasting_gdp`, `paper-macro-model/main.tex`)?

## Hypothesis

The default build's dynamics are wrong mainly because of mechanism bugs (several
already fixed in unmerged upstream PRs), not missing calibration. Falsified if,
after the known fixes, the drift in exp001 persists and a parameter sweep over
the calibrated parameters removes it.

## Success metric

`make baseline` scorecard: `sim / AR(1)` RMSE ratio (median seed, 12 quarters,
France 2014-Q1) for the five aggregates.

- **Sanity gate:** no systematic drift. Mean simulated growth is within 0.5 pp/quarter
  of the data, and unemployment stays within 2 pp of the data after 12 quarters.
- **Target:** ratio ≤ 1 for every aggregate. The paper reports roughly 40–75% of
  the AR(1) RMSE.

## Data

| Dataset | Role | Location | Notes |
| --- | --- | --- | --- |
| Sample raw data | canonical (for now) | `tests/test_macro_data/unit/sample_raw_data` | Real OECD/Eurostat/ICIO/IMF; **spoofed** HFCS and Compustat |
| Real HFCS / Compustat | needed for paper claims | not on this machine | confidential |

## Parameters in use

No calibrated values are loaded anywhere: `macrocalib` has not been run, and the paper's
posterior (Table `table:prior`) is not used.
- **Estimated from data at initialisation:** input–output coefficients, initial stocks
  and balance sheets, tax rates, the Taylor-rule coefficients (ARDL on the policy-rate
  history; a TODO says `xi_pi` is wrong), and each quarter the AR(1) growth and inflation
  forecasts.
- **Hand-set defaults** in `macromodel/configurations/*.py`: every behavioural parameter
  (price setting, target production, input constraints, utilisation rates, bank limits,
  credit and housing markets). The only one changed so far is `price_setting_noise_std`
  0.05 → 0.0005.

## Baselines

| Baseline | Why it is the right comparison | Status |
| --- | --- | --- |
| AR(1) on q/q growth, fit 2000-Q3–2014-Q1 | the paper's benchmark | in exp001 |
| Observed French series | ground truth | in exp001 |
| IIASA/Poledna model | the competitor | not set up |

## Experiments

| ID | Question | Status | Result |
| --- | --- | --- | --- |
| exp001 | Does the default model produce plausible dynamics? | done, re-run after each fix | Fails the sanity gate; see the scorecard history. `outputs/exp001_baseline/` |
| exp002 | How much of the gap to the paper is configuration rather than code? | done | Most of the damage is the 5% price noise; see below. `outputs/exp002_paper_ablation/` |
| exp003 | Can the model grow, and where does its inflation come from? | done | Inflation = the noisy AR(1) forecast; no growth in any cell. `outputs/exp003_growth_inflation/` |
| exp004 | Does the paper's capacity setup let the growth loop run? | done | Spare capacity gives growth; the stock top-up explodes. `outputs/exp004_growth_loop/` |

### Baseline scorecard history

`make baseline` run after each change on `main`: `sim / AR(1)` RMSE ratio, plus the
mean quarterly real GDP growth (data: +0.64%) and the median unemployment rate after
12 quarters (data: ~10%).

| State of `main` | GDP | HH cons. | Gov. cons. | Invest. | CPI | GDP growth | Unemp. q12 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| upstream `76ac000` | 1.63 | 3.92 | 8.10 | 1.81 | 3.65 | −0.53% | 16.0% |
| + PR #93 housing IDs | 1.68 | 4.03 | 8.83 | 1.99 | 3.67 | −0.62% | — |
| + PR #104 credit units | 7.00 | 3.37 | 8.32 | 2.06 | 3.78 | explodes | 15.8% |
| + rent-regression fixes (ours) | 1.46 | 3.54 | 8.40 | 1.88 | 3.73 | −0.34% | 15.0% |
| + price noise 0.05 → 0.0005 (default) | **1.14** | **2.47** | **1.99** | **1.14** | **1.72** | −0.04% | 10.5% |

## What we have learned

### Is today's code the paper's model?

**No.** The code that produced the paper's results is not in this repository.
- Sam's calibration scripts (`extra/sam_calibration/`, local only and gitignored; dated
  Apr–Sep 2024, so later than any model code in this history) ran on a server
  against three separate repositories: `/data1/sam/inet-macro-model`,
  `/data1/sam/inet-macro-data` and `/data1/sam/inet-macro-calibration`. They used
  APIs (`inet_macromodel.Runner`, `inet_data.Creator`, YAML configs `inet_<ISO>.yaml`)
  that no longer exist here.
- His paper prior (`get_paper_prior`) calibrates `target_production_considers_capital_inputs`
  and `target_production_considers_labour_inputs`, i.e. χ applied to target production
  as in the paper. These parameters never existed in this repository's history
  (`git log -S` is empty).
- Here, Wiese's own commits end in Oct 2023 (`9939831`). That snapshot has neither the
  paper's χ nor its price rule (it uses `CANVASPriceSetter`). Today's code descends
  from it through about 1,450 later commits.
- Missing artefacts needed to reproduce the paper exactly: `configs/inet.yaml`, the
  per-run `baseline_config.yaml` / `prior.yaml` / `samples.txt` (posterior samples),
  and the processed data directory.
- The paper's pipeline calibrates on 3 years (e.g. 2010-Q1–2013-Q1) per country with
  NPE and NRE on moments of real GDP, nominal GDP, the GDP deflator, real household
  consumption, real government consumption and real GFCF, then forecasts 3 years
  ahead. The paper-figure notebook path suggests a fourth repo, `inet-macro-dev`.

### Where today's defaults differ from the paper (exp002, 5 seeds, 12 quarters)

Paper settings added cumulatively to the defaults as they were with 5% price noise
(`sim / AR(1)` RMSE ratios):

| Step | GDP | HH cons. | Gov. cons. | Invest. | CPI | GDP growth | Unemp. q12 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| defaults with old 5% price noise | 1.32 | 3.52 | 8.40 | 2.06 | 2.59 | −0.4% | 14.8% |
| + growth expectations (sectoral speed 1) | 1.57 | 3.92 | 7.24 | 1.66 | 2.86 | −0.6% | 16.6% |
| + input constraints χ (mapped) | 1.64 | 3.74 | 8.07 | 2.20 | 3.21 | −0.6% | 16.6% |
| **+ no price noise** | **1.19** | **2.75** | **1.97** | **1.13** | **1.83** | 0.0% | **10.1%** |
| + paper bank limits | 1.20 | 2.46 | 1.80 | 1.23 | 1.99 | −0.1% | 10.9% |
| + Taylor rule | 1.24 | 2.33 | 2.14 | 1.23 | 2.14 | 0.0% | 10.8% |
| + many firms (408) | 1.21 | 2.77 | 1.97 | 1.37 | 1.76 | −0.1% | 10.4% |
| + inventory target (φ^StY 0.10, −S) | diverges | | | | | | |
| data | | | | | | +0.6% | 9.4% |

- **Price noise was the main pathology.** Firms multiplied their price by a random
  shock with 5% standard deviation every quarter; the shocks compound as a random walk
  and, with one firm per industry, move whole sectors. The paper's price equation has
  none, and Sam's prior defaults it to 0. **The default is now 0.0005 (0.05%).**
- **Growth expectations are off by default** (`sectoral_growth_adjustment_speed = 0`)
  although in the paper firms always scale demand by predicted sectoral growth.
  Switching them on does not help with today's other defaults.
- **The χ structure differs:** the paper caps target production; the code caps labour
  demand and intermediate/capital purchases separately, all fully by capital by default.
- **One firm per industry by default** (18 firms for France). `default_data_configuration`
  ignores its `single_firm_per_industry` argument (`create_country_configurations`
  hard-codes the per-country flag), and many-firm mode crashed in
  `compute_productivity_investment` (per-firm prices used as per-industry). Both are
  worked around or fixed; many firms do not change the scorecard much.
- **The inventory step diverged because of two bugs, not the paper's rule** (both
  fixed after exp002, so its inventory row is stale): `FirmsConfiguration.reset_params`
  passed `existing_inventory_fraction` (how much inventory target production subtracts)
  as the *initial* inventory, so −S gave every firm a full quarter of output in stock;
  and the resulting data reset ran the broken re-initialisation path (below).
- Even at its best, the model has 0% GDP growth vs +0.6% in the data, and every
  ratio is still above 1: no growth engine, and no calibration yet.

### Growth and inflation (exp003, exp004)

- **Inflation is the forecast.** Firms set price = previous price × (1 + forecast PPI
  inflation), so realised PPI inflation equals `estimated_ppi_inflation` almost exactly.
  The forecast is an AR(1) on the previous 60 quarters (2000–2013, about 0.4%/quarter)
  plus a random draw each quarter (`assume_zero_noise=False`, as in Sam's runs). It
  cannot see the 2014–16 disinflation. Without the draw, CPI `sim / AR(1)` drops from
  about 1.8 to **0.95** and government consumption from 2.0 to about 1.35 (exp003).
  This is the "embedded AR(1)" concern of referee R2.4.
- **Growth is blocked at capital capacity.** With today's defaults all 18 firms produce
  exactly at capital capacity every quarter, headcount does not move and
  unemployment stays at 10.29%. Two reasons:
  - Initial stocks are sized for full utilisation (ω = 1.0; the paper uses 0.85).
  - Capital purchases target only depreciation, d·Ŷ (φ^K = 0; the paper uses 1), so
    the stock never grows.

  Turning on growth expectations alone changes nothing (exp003, all 8 cells ≈ 0% growth).
- **Spare capacity unlocks growth** (exp004 step 2: growth expectations + ω = 0.85):
  real GDP +0.3%/quarter (data +0.64%), investment +0.4%, GDP `sim / AR(1)` **1.09**
  (the best yet). Unemployment overshoots to 5.8% (data 9.4%), so part of this is a
  one-off catch-up into the spare capacity rather than steady growth.
- **The stock top-up explodes** (exp004 step 3, φ^K = φ^M = 1, the paper's values):
  investment +15%/quarter and GDP `sim / AR(1)` 12. It acts as an accelerator: closing
  the whole gap between stock and K(0)·Y/Y(0) each quarter raises demand for capital
  goods, hence output, hence the target stock. Later exp004 steps inherit the explosion
  and say nothing about χ, inventory or many firms.

### Bugs and model state on `main`

- **Current state (default price noise 0.0005, 10 seeds, 12 quarters):** unemployment
  passes the sanity gate (10.5% after 12 quarters vs ~9.4–10%). Growth still fails:
  - Real GDP about −0.04%/quarter vs +0.64% in the data, and investment about 0% vs
    +0.8%. There is no growth engine.
  - CPI inflation about 0.5%/quarter (≈2%/yr) vs about 0.1% in the data.
  - Every `sim / AR(1)` ratio is still above 1 (best: GDP and investment, both 1.14).
- **Simulations modified their input data:** when the simulation's firm settings
  differed from the data config, `Simulation.from_datawrapper` reset the caller's
  datawrapper in place, so later runs inherited it. Fixed (it now deep-copies).
- **The re-initialisation path is broken (open):** that reset re-runs the whole financial
  initialisation (`reset_firm_function_dependent` → `set_wealth_and_credit`) on data that
  is already initialised. Bank deposits go from −1.17e12 to +1.18e14 and bank
  liabilities to 1.65e16 (4,000× the normal path), and the run diverges.
  Experiments avoid it by building the data with matching settings
  (`scoring.load_data(utilisation_rate=..., inventory_fraction=...)`). Even the normal
  path's negative bank deposits look wrong.
- **Initial demand includes inventory:** `firm_tools.py:487` sets Demand = Production +
  Inventory (comment: "I am not sure about this"), so any inventory target starts firms
  expecting more demand than they sell. Left as is; changes initialisation.
- **Rent-regression bugs (ours, not fixed upstream):**
  `HousingMarket.compute_observed_fraction_rent_value` fitted value on rent (arguments
  swapped) and fitted a line through a single rental. After #104 vacated houses were
  listed at 35–72% of their value per quarter and output GDP doubled. Fixed with tests.
- **The rental market is nearly dead:** 0–1 rentals per quarter vs 400–500 sales.
  Some initial houses have quarterly rent above their value (rent/value up to 2.8).
- **Too few agents is not the cause** of noise or drift (scale 10,000 vs 1,000).
- **Taylor rule:** the rate hits zero by quarter 3. The default is `ConstantPolicyRate`.
- **Initial state is not a steady state:** aggregate firm profits are negative at t=0
  (also with many firms), and consumer credit decays towards 0 even after #104.
- **The data target may be wrong:** macro_data's "Real GDP" is GDP deflated by PPI
  (+2.6%/yr for France 2014–16; official ~1%/yr). The paper used a GDP deflator.
- Runs are deterministic per seed. A 12-quarter France run takes about 1 s with 18
  firms and about 10 s with 408.

## Open threads

1. **Get the paper's code and artefacts.** Ask Sam Wiese (and José Moran) for
   `inet-macro-model`, `inet-macro-data`, `inet-macro-calibration` and `inet-macro-dev`
   at the paper's commits, plus `configs/inet*.yaml`, `prior.yaml`, `samples.txt` and
   the processed data. With these, reproducing the paper is a re-run, not a port.
2. **The growth loop.** Spare capacity (ω = 0.85) plus growth expectations gives growth.
   Next: make the stock top-up stable (close a fraction of the gap per quarter, or use
   target rather than realised output), then test χ-on-target-production as a new
   `TargetProduction` class and the inventory target. Check whether growth persists or is
   a one-off catch-up (run 20+ quarters).
3. **Forecast noise:** decide whether expectations carry the AR(1) noise draw (paper and
   Sam: yes; without it CPI beats AR(1)). It is a modelling choice, not a bug.
4. **Fix the re-initialisation path** (double-counted bank deposits), or remove it in
   favour of building data with matching settings.
5. **Calibration:** none is in use (see Parameters). Calibrate the paper's seven
   parameters once the growth loop is stable.
6. **Scoring like the paper:** GDP deflator instead of PPI, calibration window
   2010–2013, forecast from 2013-Q1, and more countries once data allows.
7. **Merge the remaining upstream fixes**, scoring each: #83 Taylor rule, #85 frequency
   conversion, #56/#64/#67 productivity/investment/substitution, `bug/government-expenditure`.
8. **Report upstream:** the rent-regression fix, the many-firm crash, the data mutation
   and the inventory mapping.
9. **Initial-state consistency:** negative firm profits at t=0; a t=0 accounting test.
10. **Real micro-data:** HFCS and Compustat access.

## Claims → evidence

| Claim in the paper | Figure / table | Experiment |
| --- | --- | --- |
| Beats AR(1) and IIASA on forecasting RMSE | `table:forecasting_gdp` | not yet reproduced |
