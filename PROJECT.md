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

## Issue register

One register for everything known to be wrong, missing or uncertain, merging our
findings with the CB7 team's list (UK fork). Update rows in place; reference IDs in
commit messages (e.g. `G1:`).

- **Kind:** **Bug**: code does not do what it intends. **Spec**: works as written but
  differs from the paper or behaves implausibly. **Gap**: missing feature.
  **Infra**: engineering or workflow. **Data**: inputs. **Question**: not yet
  established as a problem; verify first.
- **Priority:** **P1** blocks credible dynamics or reproducing the paper. **P2** needed
  for the paper revision or for trustworthy experiments. **P3** later. **—** out of
  scope for us.
- **Source:** ours (with experiment), CB7, upstream, or both.

### R. Reproducing the paper and calibration

| ID | Problem | Kind | Source | Evidence | Status | Pri |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | The code, configs and posterior samples behind the paper's results are not in this repo | Data | both | Sam's scripts use separate `inet-macro-*` repos and parameters that never existed here | open: ask Sam / José | P1 |
| R2 | No calibration in use; every behavioural parameter is a hand-set default | Gap | both | "Parameters in use" | open; after G1–G3 | P1 |
| R3 | Calibration and specification problems are hard to tell apart | Question | CB7 | Approach: ablations against a fixed scorecard (exp002–004) | partial | P2 |
| R4 | Scoring differs from the paper: GDP deflated by PPI (macro_data's "Real GDP" too, +2.6%/yr vs ~1% official), one country, one start date | Spec | ours | exp001 | open | P2 |
| R5 | `macrocalib` is untested and excluded from the test suite | Infra | ours | pytest `addopts` | open | P3 |
| R6 | Differentiable version of the model | Gap | CB7 | Matias investigating | not ours now | P3 |

### G. Growth and firm behaviour

| ID | Problem | Kind | Source | Evidence | Status | Pri |
| --- | --- | --- | --- | --- | --- | --- |
| G1 | No growth: firms start at full capacity (ω = 1; paper 0.85) and capital purchases only replace depreciation (φ^K = 0; paper 1) | Spec | ours | exp003, exp004: every firm at capital capacity; ω = 0.85 gives +0.3%/q | open | P1 |
| G2 | The paper's stock top-up (φ^K = φ^M = 1) explodes like an accelerator | Spec | ours | exp004 step 3: investment +15%/q | open | P1 |
| G3 | Growth expectations off by default (`sectoral_growth_adjustment_speed = 0`; paper weight 1) | Spec | ours | exp002, exp003 | open; with G1 | P1 |
| G4 | χ caps input purchases and hiring, not target production as in the paper | Spec | ours | exp002; Sam's `target_production_considers_*` | open | P2 |
| G5 | One firm per industry by default, and `default_data_configuration` ignores its `single_firm_per_industry` argument | Bug | ours | `configuration_utils.py:74` | workaround in `scoring.load_data` | P2 |
| G6 | Spare capacity overshoots: unemployment falls to 5.8% (data 9.4%) | Question | ours | exp004 step 2 | open | P2 |
| G7 | Many-firm runs crashed (per-firm prices used as per-industry) | Bug | ours | — | done `31f797a` | — |

### P. Prices, expectations and monetary policy

| ID | Problem | Kind | Source | Evidence | Status | Pri |
| --- | --- | --- | --- | --- | --- | --- |
| P1 | 5% per-firm price noise dominated the dynamics | Spec | ours | exp002 | done `60948b7` (0.0005) | — |
| P2 | Realised inflation equals the AR(1) forecast (self-fulfilling; referee R2.4) | Question | ours | exp003 | open | P2 |
| P3 | Forecast noise draw roughly doubles the inflation error: keep (paper) or drop? | Question | ours | exp003: CPI ratio 1.8 → 0.95 without it | decision pending | P2 |
| P4 | Taylor rule inert (zero by quarter 3), constant rate by default, and a TODO says `xi_pi` is estimated wrongly | Bug | ours | exp001; `default_synthetic_central_bank.py:168` | open; see upstream #83 | P2 |

### S. Initial state and stock-flow consistency

| ID | Problem | Kind | Source | Evidence | Status | Pri |
| --- | --- | --- | --- | --- | --- | --- |
| S1 | Stock-flow consistency is not verified; no accounting test, no balance-sheet or transaction-flow matrix in the code | Gap | both | CB7: Tom's review; only GDP's three approaches are computed, and forced to agree (S6) | open | P1 |
| S2 | Aggregate firm profits are negative at t=0 and stay negative | Question | ours | probes; also with 408 firms | open | P1 |
| S3 | The re-initialisation path double-counts bank deposits (liabilities 1.65e16) | Bug | ours | exp004 | workaround: build data with matching settings | P2 |
| S4 | Bank deposits are negative on the normal path (−1.17e12) | Question | ours | probe | open | P2 |
| S5 | Initial Demand = Production + Inventory | Question | ours | `firm_tools.py:487` | open | P3 |
| S6 | GDP is forced to balance by adjusting imports/exports, which can hide inconsistencies | Spec | ours | `economy.compute_gdp(always_adjust=True)` | open | P2 |
| S7 | Simulations modified their input data | Bug | ours | — | done `62d29d3` | — |
| S8 | Initial inventory read from the wrong parameter | Bug | ours | — | done `62d29d3` | — |

### M. Markets and trade

| ID | Problem | Kind | Source | Evidence | Status | Pri |
| --- | --- | --- | --- | --- | --- | --- |
| M1 | Housing market initialises and executes poorly (tenure mix, stock quality) | Spec | both | CB7; upstream #93 | partial: #93 merged | P2 |
| M2 | Rental market nearly dead (0–1 rentals/q vs 400–500 sales); some rent/value above 1 | Question | ours | rent probe; possibly spoofed data | open | P2 |
| M3 | Consumer credit decays towards 0 even after #104 | Question | ours | probes | open | P2 |
| M4 | Government consumption still about 2× the AR(1) error | Question | ours | baseline | partial: price noise fixed most | P2 |
| M5 | Imports, exports and exchange rates need review | Spec | CB7 | see S6 | open | P3 |
| M6 | Housing IDs set to −1 at initialisation | Bug | upstream | — | done: #93 merged `80d8b3d` | — |
| M7 | Credit-supply units bug | Bug | upstream | — | done: #104 merged `a6dca3c` | — |
| M8 | Rent-value regression swapped and fitted through one point | Bug | ours | — | done `21f1f2b`; report upstream (E9) | — |

### F. Government and finance

| ID | Problem | Kind | Source | Evidence | Status | Pri |
| --- | --- | --- | --- | --- | --- | --- |
| F1 | Taxes and benefits need review | Spec | both | upstream `bug/government-expenditure` (benefits, deficit fixes; no PR) | open | P2 |
| F2 | Corporate equity not wired between firms and households (profits not redistributed) | Gap | CB7 | Andrea's module; relates to S2 | open | P2 |
| F3 | Government debt, bond issuance, QE | Gap | CB7 | Tom's UK prototype | open | P3 |
| F4 | Fiscal rules | Gap | CB7 | — | open | P3 |

### E. Engineering and workflow

| ID | Problem | Kind | Source | Evidence | Status | Pri |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | Tests pass while dynamics are broken; no behavioural check runs automatically | Infra | ours | housing IDs, rent bug | partial: `make baseline` | P1 |
| E2 | Weak modularity: hard to run experiments on parts of the model | Infra | both | e.g. a firm-stock reset re-runs the whole financial initialisation | open | P2 |
| E3 | No standard Monte Carlo / experiment procedure | Infra | both | CB7: Emma's code, SLURM arrays | partial: `scoring.py` + `provenance.py` | P2 |
| E4 | No systematic sensitivity analysis of dynamics | Gap | both | CB7: Andrea and Marcela; ablations exp002–004 | partial | P2 |
| E5 | Upstream fixes not yet merged: #83, #85, #56/#64/#67, `bug/government-expenditure` | Infra | ours | `make upstream` | open | P2 |
| E6 | Scaling effects (1:100 vs 1:100,000) | Question | both | exp001: 10× agents changes nothing, but firms stay at 1 per industry (G5) | partial | P3 |
| E7 | Standardised outputs, dashboards, reporting to non-coders | Infra | CB7 | scorecard CSV/PNG per experiment | partial | P3 |
| E8 | Agent-level reporting; visualising the synthetic population | Gap | CB7 | — | open | P3 |
| E9 | Report our fixes upstream: rent regression, many-firm crash, data mutation, inventory mapping | Infra | ours | — | open | P3 |
| E10 | New-user induction; AI workflows not standardised | Infra | CB7 | partial: AGENTS.md, PROJECT.md | partial | P3 |
| E11 | `make lint` fails on the file merged from #104 | Infra | ours | `credit_market/func/clearing.py` | wait for upstream | P3 |
| E12 | Housing market takes 92% of run time (row-wise pandas loops); blocks finer scales | Infra | ours | profile, 408 firms, 8 quarters: 8.2 of 8.9 s | open | P2 |
| E13 | Plugging in behaviour means editing closed `Literal` lists and hard-wired argument passing in `country.py`; god objects (`firms.py` 2,256 lines, 196 time series) | Infra | ours | 54 behaviour slots, 27 with alternatives; 3 files use hooks | open | P3 |
| E14 | Data and simulation configs duplicate firm settings, reconciled by a compatibility check and a re-initialisation path | Infra | ours | G5, S3, S8 all came from this | open | P2 |

### D. Data

| ID | Problem | Kind | Source | Evidence | Status | Pri |
| --- | --- | --- | --- | --- | --- | --- |
| D1 | Only spoofed HFCS and Compustat on this machine | Data | ours | — | open: request access | P2 |
| D2 | OECD ICIO 2022 update; ICIO tables are nominal (referee R1.5) | Data | both | — | open | P3 |
| D3 | Wage distributions | Data | CB7 | Nuffield bid | open | P3 |
| D4 | Household composition and demography (death, marriage, inheritance) | Gap | CB7 | — | open | P3 |

### UK. CB7 net-zero and UK policy (out of scope for us)

CB subsidies all-or-nothing; random retrofitting order; all household changes at once;
no EV investment; net-zero uptake decisions; alignment with DESNZ / UK TIMES;
alternative investment; consumer energy prices; granular policy shocks and scenarios.
Kept here so that their fixes are recognisable if they land upstream.

### Next up

1. **G1–G3 (growth loop):** a stable stock top-up, then 20+ quarter runs to see
   whether growth persists.
2. **S1, S2:** a t=0 accounting test; find why firm profits are negative.
3. **R1:** message Sam / José for the paper's code and artefacts.
4. **P3:** decide on forecast noise.
5. **E5:** merge the next upstream fixes (#83, #85), scoring each.

## Claims → evidence

| Claim in the paper | Figure / table | Experiment |
| --- | --- | --- |
| Beats AR(1) and IIASA on forecasting RMSE | `table:forecasting_gdp` | not yet reproduced |
