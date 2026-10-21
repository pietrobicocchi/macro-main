# PROJECT.md

The living scientific state of this project: what we are investigating, and what
we currently know. **Update this file in place; never append to it as a log.**
Git remembers what happened.

## Question

Starting from this code (the paper's original code is not available), can we build a
macro ABM whose dynamics are economically credible and whose forecasts of real GDP,
inflation, household consumption, government consumption and investment are
comparable to, or better than, the paper's (Table `table:forecasting_gdp`)? Then:
which of its ingredients deliver that skill (the reviewers' attribution and ablation
questions)?

Modelling choices follow economic reasoning, guided by the paper and the referee
reports. Where the paper is too simple or wrong, we change the model and the paper
says so. Every choice is recorded in "Modelling decisions".

## Hypothesis

Credible dynamics need three things the current build lacks: (a) balanced accounts,
(b) a growth engine (firms with spare capacity that invest gradually towards
expected demand, plus a source of productivity growth), and (c) prices driven by
costs and demand rather than copied from a forecast. With these in place and the
paper's parameters calibrated on 2010–2013 data only, the model forecasts France
2013–2016 better than AR(1). Falsified if, with (a)–(c) in place, every calibration
leaves `sim / AR(1)` above 1 for GDP and inflation.

## Success metric

`make baseline` scorecard: `sim / AR(1)` RMSE ratio (median seed, 12 quarters,
France) for the five aggregates. Gates, in order:

1. **Accounts gate:** the accounting checks (S1) pass every quarter.
2. **Sanity gate:** no systematic drift. Mean simulated growth is within 0.5 pp/quarter
   of the data, unemployment stays within 2 pp of the data after 12 quarters, and
   20-quarter runs neither explode nor collapse.
3. **Target:** after calibration on pre-forecast data only, ratio ≤ 1 for every
   aggregate. For reference, the paper reports roughly 40–75% of the AR(1) RMSE.

## Data

| Dataset | Role | Location | Notes |
| --- | --- | --- | --- |
| Sample raw data | canonical (for now) | `tests/test_macro_data/unit/sample_raw_data` | Real OECD/Eurostat/ICIO/IMF; **spoofed** HFCS and Compustat |
| Real HFCS / Compustat | needed for paper claims | not on this machine | confidential |
| Full raw data, 2010–2017, 38 countries | needed from roadmap phase 5 | not on this machine (D1) | `~/Documents/dev/phd/datasets` is empty |

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

## Modelling decisions

Each departure from today's code or from the paper, with the reason recorded *before*
looking at the result. This is the raw material for the rewritten model section.

| # | Decision | Economic reason | Alternative considered | Evidence | Paper impact |
| --- | --- | --- | --- | --- | --- |
| MD1 | Price noise 0.0005 per quarter (was 0.05) | A 5% random price shock per firm per quarter is far larger than observed price changes; the paper's price equation has none | 0 (exactly the paper) | exp002, `60948b7` | none (matches paper) |
| MD2 | Loan write-offs are losses of the lending bank, charged against profit before tax | Standard bank accounting; without it a default turns the borrower's debt into free money | charge equity directly, after tax | Phase 1 accounting | rewritten paper: describe bank losses |
| MD3 | A failing bank is recapitalised by the government (the injection is government spending); its loans and deposits stay | Borrowers still owe what they borrowed and depositors keep their money; deleting them created money | bail-in of depositors | Phase 1 accounting | describe bank resolution |
| MD4 | The credit market holds all household mortgages, on the main residence and on other properties | They are real debts, already recorded by banks and households | — | Phase 1 accounting | none |
| MD5 | A failing bank is recapitalised by the government to exactly the minimum capital ratio (`MinimumCapitalBankDemography`, default) | Regulators restore minimum capital; it also works with one bank, unlike topping up to the healthy banks' average | top up to the average of healthy banks (still selectable) | Phase 1 | describe bank resolution |
| MD6 | Households' other financial assets are shares in domestic firms: purchases fund firms, firms pay dividends (Eurostat payout ratio) out of after-tax profits (`FirmSharesFinancialAssets`) | Income must have a payer and savings a receiver; shares in firms are the main household financial asset with a domestic counterpart | claims on the rest of the world; government bonds | Phase 1: money conserved; but dividends are ~2 bn/q against 107 bn/q of the old income, so consumption drops ~19% | built, off by default until firm profits are realistic (S2) |
| MD7 | Initial mortgages are capped at the value of the property they finance (`cap_mortgages_at_property_value`, data config, default on) | A mortgage is secured on a property; the spoofed survey breaks that link | wait for real data; cap at a loan-to-value above 1 | Phase 1: underwater households 77 → 24 | none; switch off with real HFCS |
| MD8 | Households default when they cannot pay: underwater and an overdraft above one quarter of income (`UnableToPayHouseholdInsolvencyHandler`, default) | Underwater households that keep paying do not default; the old rule defaulted at the first overdraft | old rule (still selectable); recovery of the house by the bank (not yet) | Phase 1: quarter-1 write-offs 400 → 110 bn, no bank bail-out needed | describe household default |
| MD9 | Initial wages keep each industry's SEA labour share of value added; capital compensation stays equal to investment (steady capital stock), and the rest is profit (`labour_share_from_sea`) | Value added = wages + depreciation + profits + taxes; the old rule gave profits to workers | keep the old rule (current default) | exp005: profits 3.9% → 24.5% of GDP, wages match France, GDP and CPI scores hold or improve | default since 2026-10-21; describe the initial income split |
| MD10 | Investment as a flexible accelerator: replacement plus a fraction λ of the gap to desired capital (initial capital/output ratio at planned output), planned on expected demand (`PartialAdjustmentTargetCapitalInputsSetter`) | Standard investment theory; closing only part of the gap avoids the paper's runaway top-up | paper's full top-up (G2) | exp006–exp008: cycles without brakes; with desired capital on smoothed demand (`demand_smoothing` 0.10) growth is steady at 0.7%/q | candidate, option until unemployment stays plausible (G12) |
| MD11 | Search frictions in the labour market: employees separate at s = 3% per quarter, firms post vacancies for the gap to desired labour (replacements included), and hires are capped by a Cobb-Douglas matching function M = μU^0.5 V^0.5, with μ set so the initial unemployment rate (10.3%) is a steady state (`SearchFrictionsLabourMarketClearer`, `settings.search_frictions`) | Real labour markets have job-to-unemployment flows and take time to fill vacancies; without them a boom hires the whole unemployed pool within a quarter (G13). Flows are calibrated to a steady state at the initial unemployment rate, as initial stocks are | quits by wage/wealth (`individuals_quitting`); a hiring-speed cap (`hiring_speed` < 1) | exp010: unemployment holds at 10.3% under today's defaults; under the growth engine it falls to 2% (no frictions: 0%) | option; describe the labour market |
| MD12 | Labour-augmenting technical progress: output per worker grows at an exogenous g per quarter in every industry (0.25%, about 1% a year), and real wages per worker grow with it (`LabourAugmentingGrowth`, `settings.labour_productivity_growth`) | On a balanced growth path output per worker rises and the labour share and capital-output ratio stay constant (Harrod-neutral progress); without it, output growth needs a proportional rise in employment from a fixed labour force (G14) | the TFP module (`SimpleTFPGrowth`, G15); g endogenous to investment | exp011: unemployment rises 10.3% → 14.4% on today's capacity-capped defaults; under the growth engine it stays near 2–4% because GDP growth rises instead (G16) | option; describe productivity growth |
| MD13 | Firms' expected growth falls when unemployment is below its initial level: AR(1) forecast − 0.2 × (initial − current unemployment rate) (`SlackAwareGrowthForecastingAutoReg`, `settings.growth_forecast_slack_aware`) | Firms extrapolating recent growth alone expect a boom to go on whatever the labour market; by Okun's law output is about twice as far above potential as unemployment is below normal, and firms expecting a tenth of that gap to close each quarter expect 0.2 × the unemployment gap less growth | forecast from pre-2014 data only (`DataOnlyGrowthForecastingAutoReg`, no lookahead) | exp014: unemployment 6.4% after five years (engine alone 2.4%); with cost pass-through and yearly wage catch-up 7.7% at q12 and 6.9% at q20, growth 0.4%/q | option; describe expectations |

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
| exp005 | Do realistic initial wages give firms realistic profits, and can profits pay households? | done | Yes (B); paying them as dividends (C) needs firms to invest retained profits first. `outputs/exp005_firm_profits/` |
| exp006 | Does a flexible-accelerator investment rule give a stable growth engine? | done | Growth, but boom–bust: needs wage, financing and expectation brakes (G8–G10). `outputs/exp006_investment_engine/` |
| exp007 | Do wages that follow prices and labour-market tightness stabilise the engine? | done | Indexation (S27) halves the bust; tightness adds demand without cost pass-through. `outputs/exp007_wage_brake/` |
| exp008 | Which brakes turn the boom–bust into steady growth? | done | Smoothed desired capital (G10): steady 0.7%/q growth; financing (G9) needs realistic bank limits. `outputs/exp008_investment_brakes/` |
| exp009 | Does a realistic work-effort cap keep unemployment plausible? | done | No: the labour market has no frictions (G13). `outputs/exp009_work_effort/` |
| exp010 | Do search frictions keep unemployment plausible while the economy grows? | done | No: 10.3% → 2% instead of 0%. Labour demand outgrows the labour force because labour productivity does not grow (G14). `outputs/exp010_search_frictions/` |
| exp011 | Does labour-augmenting productivity growth keep unemployment plausible while the economy grows? | done | No: unemployment 2.2–4.0% after five years at g = 0.15–0.5%/q; the engine grows faster instead, because growth expectations feed on the model's own growth (G16). `outputs/exp011_labour_productivity/` |
| exp012 | Do wages and prices that respond to tightness brake the growth engine? | done | No: unemployment 2.3–3.5% after five years with any brake; the model has no channel through which higher prices or interest rates cut spending (G17). Cost pass-through improves the inflation fit (CPI ratio 1.93 → 1.38). `outputs/exp012_price_wage_brakes/` |
| exp013 | Do wages that catch up with prices gradually let price rises brake the engine? | done | No: unemployment 3.0–3.5% after five years; the boom raises inflation only to 0.3–0.4%/q, so there is little to brake. On today's defaults, cost pass-through with yearly wage catch-up improves or matches every ratio (CPI 0.98). `outputs/exp013_wage_indexation/` |
| exp014 | Does anchoring firms' growth expectations stop the engine running unemployment down? | done | Partly: a slack-aware forecast keeps unemployment at 5.5–6.9% after five years (engine alone 2.4%); with cost pass-through and yearly wage catch-up the engine is within the sanity gate's tolerances at 12 quarters (unemployment 7.7% vs 9.4%, growth 0.4% vs 0.64%/q). The data-only forecast barely helps (3.6%). `outputs/exp014_growth_expectations/` |

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
| + price noise 0.05 → 0.0005 (default) | 1.14 | 2.47 | 1.99 | 1.14 | 1.72 | −0.04% | 10.5% |
| + Phase 1 accounting fixes (S15–S20) | **1.13** | **2.45** | 2.11 | **1.09** | 1.82 | −0.01% | 10.4% |
| + Phase 1 round 2 (S11, S12, S14, S22) | 1.16 | 2.56 | 1.94 | 1.13 | 1.92 | −0.05% | 10.4% |
| + upstream #83, #85 (quarterly rates), MD5 | 1.14 | 2.57 | 1.92 | 1.12 | 1.89 | −0.04% | 10.4% |
| + MD7 mortgage cap, MD8 default rule | 1.17 | 2.59 | 2.06 | 1.17 | 1.76 | −0.05% | 10.4% |
| + MD9 realistic initial wages (default) | 1.15 | 2.96 | 1.98 | 1.11 | 1.65 | −0.05% | 10.4% |
| + S27 wages indexed to CPI again | 1.14 | 2.85 | 2.05 | 1.20 | 1.84 | −0.04% | 10.3% |

## What we have learned

### Why we build from this code, not the paper's

The code that produced the submitted paper's results is not in this repository and is
not obtainable (R1). This matters for the rewritten paper: the model it describes will
differ from the submitted one.
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
- The paper's pipeline calibrates on 3 years (e.g. 2010-Q1–2013-Q1) per country with
  NPE and NRE on moments of real GDP, nominal GDP, the GDP deflator, real household
  consumption, real government consumption and real GFCF, then forecasts 3 years
  ahead. The paper-figure notebook path suggests a fourth repo, `inet-macro-dev`.

### Where the defaults differed from the paper (exp002, before MD1; 5 seeds, 12 quarters)

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
- **Growth is blocked at capital capacity.** With the current defaults all 18 firms produce
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

### Firm profits and household income (exp005, 5 seeds, 20 quarters)

- **S2's cause:** the data pipeline set initial wages to value added minus investment, so
  firms had no operating profit by construction. Keeping SEA labour shares (MD9) gives
  profits of about 24% of GDP and wages of about 46% (France ≈ 52%), with the scorecard
  unchanged or better (GDP 1.15, CPI 1.51).
- **Dividends need investment:** with firms paying 46% of profits as dividends (MD6),
  households' financial income becomes realistic (6.5% of GDP, paid by firms), but firms
  hold the retained 54% as deposits and spend nothing, so demand falls and unemployment
  reaches 19% after five years. Retained profits must finance investment: this is the
  growth engine (G1–G3).

### Investment engine (exp006, 5 seeds, 20 quarters)

- Spare capacity plus growth expectations gives growth (+0.4%/q over three years; data
  +0.6%) but unemployment falls from 10% to 4% (G11).
- A flexible-accelerator investment rule (MD10) adds a multiplier–accelerator cycle:
  λ = 0.10 grows then contracts (−0.9%/q in the last two years); λ = 0.25 booms (+2.1%/q)
  and busts (−5.6%/q, unemployment 34%); λ = 0.50 explodes (investment +7.6%/q).
- The missing brakes are standard: wages and prices that respond to labour-market
  tightness (G8), investment limited by financing (G9), and desired capital based on a
  steadier view of demand (G10).

### Brakes on the investment engine (exp007, exp008, 5 seeds, 20 quarters)

- **Wages were frozen in nominal terms (S27)**, a regression from the S12 fix. With wages
  paid at the current CPI again, the engine's bust halves (−1.4%/q instead of −5.6%).
- **A wage tightness markup (G8) does not brake** while firms do not pass costs into
  prices (P5): higher wages raise household spending.
- **Smoothed desired capital (G10) does:** with `demand_smoothing` 0.10, growth is a
  steady 0.7%/q (data 0.6%), with no bust. Unemployment then runs down to 0% because
  work effort lets output grow without workers (G12), and investment grows 2%/q (data 0.8%).
- **Financing limits (G9)** cause a recession with today's bank lending limits (firm
  debt/equity 0.03; paper 1.0).

### Current state of `main` (commit 7a8ac4d)

Default settings (price noise 0.0005), 10 seeds, 12 quarters, France 2014:
- **Unemployment passes the sanity gate**: 10.3–10.5% after 12 quarters vs ~9.4–10%.
- **Growth fails**: real GDP about −0.04%/quarter vs +0.64% in the data, investment
  about 0% vs +0.8%. There is no growth engine (G1–G3).
- **Inflation is too high**: about 0.5%/quarter vs about 0.1% (P2, P3).
- Every `sim / AR(1)` ratio is still above 1 (best: GDP and investment, both 1.17).
- **Accounts (Phase 1)**: every loan and deposit ledger agrees exactly; the money residual
  (up to 10% of GDP) is the by-design unbacked flows (S9, S10, S13); unexplained money is at
  most 1.2% of GDP (S23). Household defaults cost the bank 2–110 bn/q (S25), absorbed
  without government recapitalisation after MD7–MD8.
- Too few agents is not the cause of noise or drift (scale 10,000 vs 1,000; E6).
- Runs are deterministic per seed: about 1 s per 12 quarters with 18 firms, about 10 s
  with 408, mostly in the housing market (E12).

### Search frictions (exp010, 5 seeds, 20 quarters)

`SearchFrictionsLabourMarketClearer` (MD11): 3% of employees separate each quarter and a matching function
caps hires; μ makes the initial 10.3% unemployment a steady state (job-finding rate 0.21 per quarter).
- **On today's defaults the frictions are neutral:** unemployment stays at 10.3%, with about 3% of
  employment hired and separated each quarter.
- **Under the growth engine they slow the fall in unemployment but do not stop it:** 10.3% → 2.0% after
  five years (no frictions: 0%), and 1.3–1.9% for s = 0.02–0.04. A matching elasticity of 0.7 keeps 4.7%.
  GDP grows 0.6–0.7%/q as before, but more slowly in the last two years (0.2–0.4%/q vs 0.5%) because
  firms cannot fill all vacancies.
- **Why:** labour productivity is constant, so the engine's output growth needs proportionally more
  workers (about 0.5% more each quarter), and the labour force is fixed. Frictions only delay hiring.
  Unfilled vacancies stay open and pile up, and more vacancies raise the number of matches (a Beveridge
  curve), so unemployment keeps falling. Holding it near 9% while GDP grows 0.6%/q needs output per
  worker to grow (G14) or labour demand to respond to tightness through wages and prices (G8, P5).

### Productivity growth (exp011, 5 seeds, 20 quarters)

`LabourAugmentingGrowth` (MD12): output per worker grows at g per quarter, real wages with it.
- **On today's defaults it cuts labour demand as intended:** output is capped by capital, so with
  g = 0.25%/q unemployment rises from 10.3% to 14.4% in five years.
- **Under the growth engine (with frictions) it barely moves unemployment:** 2.0% without it; 2.2%, 2.4%
  and 4.0% at g = 0.15%, 0.25% and 0.5%. GDP growth rises instead: in the last two years 0.5–0.6%/q,
  against 0.2%/q without it, when unfilled vacancies held output back.
- **Why:** the engine's demand growth is not anchored. Firms scale demand by the forecast growth rate,
  an AR(1) over the data's history *and the model's own realised growth* (`Economy.set_estimates`), so
  any extra supply raises realised growth, then expected growth, then demand (G16). The data history is
  itself the PPI-deflated gross-output growth, faster than French real growth (R4).
- The first wiring grew productivity after the quarter's labour inputs were measured, so the next
  labour market compared last quarter's inputs with this quarter's productivity, and firms over-hired by
  exactly g. Productivity now grows between clearing and the measurement of labour inputs.

### Price and wage brakes (exp012, 5 seeds, 20 quarters)

On exp011's engine (frictions, productivity +0.25%/q), the brakes that are off by default were switched on:
wages that rise with hiring shortfalls (G8, scale 0.5), prices that pass on half of unit-cost growth in
place of half of expected inflation (P5), demand-pull pricing (0.25) and the Taylor rule.
- **Cost-push pricing was broken (P6):** it compared unit costs with the sector's price level, not cost
  growth. Unit costs are on average 0.895 of the price, so switching it on cut prices about 10% a
  quarter until margins vanished (probably Sam's "prices cause shit to break"). Fixed: it now passes on
  unit-cost growth, as its docstring says.
- **No brake moves unemployment:** 2.3–3.5% after five years with any combination, against 2.4% without.
  GDP grows 0.7%/q in every case; the Taylor rule raises the policy rate to 1.7% with no effect.
- **Why: nothing in the model transmits the brakes to spending (G17).** Wages are paid as real wage
  times the *current* CPI, so a price rise is handed back to workers within the quarter and real incomes
  never fall. Households spend a fixed share of nominal income, whatever the interest rate or prices.
  Investment follows the capital gap and ignores interest rates and financing (G9 off). And expected
  growth still feeds on realised growth (G16).
- **Cost pass-through improves the fit anyway:** CPI `sim / AR(1)` 1.93 → 1.38 on the engine. All brakes
  on today's defaults: GDP 1.14, HH cons. 2.78, gov. cons. 2.54, invest. 1.14, CPI 1.21 (baseline: 1.14,
  2.85, 2.05, 1.20, 1.84), unemployment unchanged at 10.3%.
- With the Taylor rule, unexplained money reaches 15.6% of GDP (S29).

### Gradual wage indexation (exp013, 5 seeds, 20 quarters)

Nominal wages now close a fraction of the gap to the CPI each quarter (`cpi_indexation_speed`; 1 is today's
rule, wages at last quarter's CPI; `settings.lagged_wage_indexation`).
- **It does not brake the engine:** unemployment 3.0–3.5% after five years at speeds 1, 0.5 and 0.25,
  with or without wage tightness. The boom raises inflation only to 0.3–0.4%/q (data 0.2%): unit costs
  barely rise while productivity grows and firms have capacity, so prices do not surge and real wages do
  not fall. The brakes in exp012–exp013 act on inflation, and the boom is not inflationary.
- **On today's defaults it improves the forecasts:** with cost pass-through 0.5 and indexation 0.25,
  GDP 1.14, HH cons. 2.69, gov. cons. 1.96, invest. 1.17, CPI **0.98** (baseline 1.14, 2.85, 2.05, 1.20,
  1.84; 5 seeds, 20 quarters scored on the first 12). Unemployment unchanged at 10.3%. The first ratio
  below 1 for any aggregate.

### Growth expectations (exp014, 5 seeds, 20 quarters)

On exp011's engine (frictions, productivity +0.25%/q), with two forecasts of growth for firms:
- **From the pre-2014 data only** (h quarters ahead; no lookahead): unemployment 3.6% after five years
  (2.4% with today's forecast). The engine's own accelerator keeps demand growing even when firms
  expect only the historical rate, about 0.5%/q.
- **Lowered when unemployment is below its initial level** (MD13, sensitivity 0.1 / 0.2 chosen from
  Okun's law): unemployment 5.5% / 6.4% after five years, growth 0.5% / 0.4%/q. The labour market now
  feeds back on demand.
- **With cost pass-through 0.5 and yearly wage catch-up as well:** unemployment 7.7% at q12 and 6.9% at
  q20 (data 9.4%, 8.4%), growth 0.4%/q (data 0.64%/q, itself overstated by R4), CPI ratio 1.28, GDP 1.16.
  Within the sanity gate's tolerances at 12 quarters, though unemployment is still falling slowly and
  investment grows 1.0%/q (data 0.8%). The first configuration with growth and plausible unemployment.

### Next step

1. **A candidate model:** defaults + MD10–MD13 + cost pass-through + yearly wage catch-up. Score it with
   10 seeds and 12/20 quarters against the baseline, check the accounts, and decide which parts become
   defaults (needs approval).
2. **R4:** deflate output and expectations properly; the growth target may be half what the scorecard says.
3. **G9** with realistic bank limits; investment that responds to the real interest rate (G17).
4. **S28, S29**, and MD6 (dividends) before anything is published.

Every known problem, fixed or open, is in the Issue register below.

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
| R1 | The code, configs and posterior samples behind the paper's results are not in this repo | Data | both | Sam's scripts use separate `inet-macro-*` repos and parameters that never existed here | closed: not obtainable; everything is built from this code | — |
| R2 | No calibration in use; every behavioural parameter is a hand-set default | Gap | both | "Parameters in use" | open; after G1–G3 | P1 |
| R3 | Calibration and specification problems are hard to tell apart | Question | CB7 | Approach: ablations against a fixed scorecard (exp002–004) | partial | P2 |
| R4 | Scoring differs from the paper: GDP deflated by PPI (macro_data's "Real GDP" too, +2.6%/yr vs ~1% official), one country, one start date | Spec | ours | exp001 | open | P2 |
| R5 | `macrocalib` is untested and excluded from the test suite | Infra | ours | pytest `addopts` | open | P3 |
| R6 | Differentiable version of the model | Gap | CB7 | Matias investigating | not ours now | P3 |

### G. Growth and firm behaviour

| ID | Problem | Kind | Source | Evidence | Status | Pri |
| --- | --- | --- | --- | --- | --- | --- |
| G1 | No growth: firms start at full capacity and capital purchases only replace depreciation, capped at current capacity | Spec | ours | exp003, exp004, exp006 | partial: investment engine built (`PartialAdjustmentTargetCapitalInputsSetter`, MD10 candidate, option); unstable without G7–G9 | P1 |
| G2 | The paper's stock top-up (φ^K = φ^M = 1) explodes like an accelerator | Spec | ours | exp004 | superseded by the partial-adjustment rule (G1), which still cycles without stabilisers | — |
| G3 | Growth expectations off by default | Spec | ours | exp002, exp003, exp006 | open: part of the engine; no effect on its own | P1 |
| G4 | χ caps input purchases and hiring, not target production as in the paper | Spec | ours | exp002; Sam's `target_production_considers_*` | open | P2 |
| G5 | One firm per industry by default, and `default_data_configuration` ignores its `single_firm_per_industry` argument | Bug | ours | `configuration_utils.py:74` | workaround in `scoring.load_data` | P2 |
| G6 | Spare capacity overshoots: unemployment falls to 5.8% (data 9.4%) | Question | ours | exp004 step 2 | open | P2 |
| G7 | Many-firm runs crashed (per-firm prices used as per-industry) | Bug | ours | — | done `31f797a` | — |
| G8 | Wages did not respond to labour-market tightness (existing employees' markup scale 0) | Spec | ours | exp007: a tightness markup raises wages, but with prices not passing costs through it adds demand instead of braking | partial: needs cost pass-through in prices (P5) | P1 |
| G9 | Capital purchases are not limited by financing (`credit_gap_fraction = 0`) | Spec | ours | exp008: switching it on with today's bank lending limits (firm debt/equity 0.03; paper 1.0) starves investment and causes a recession | open: needs realistic bank limits first | P1 |
| G10 | Desired capital followed current planned output, booms included: multiplier–accelerator cycles | Spec | ours | exp008: sizing desired capital on smoothed planned output (`demand_smoothing` 0.10) gives steady growth of 0.7%/q (data 0.6%) with no bust | fix built (option) | — |
| G11 | Spare capacity alone sends unemployment from 10% to 4% within five years | Question | ours | exp006 step 2 (see G6) | open: check labour demand vs planned output | P2 |
| G12 | Work effort can raise output per worker by up to 50% (`max_increase_in_work_effort = 1.5`) | Spec | ours | exp009: not why unemployment hits 0% (caps of 1.05–1.2 change little within 5 years); effort rises 7% once all workers are hired | open: set a realistic cap (~1.1) with G13 | P2 |
| G13 | The labour market has no frictions: firms fill every vacancy within the quarter (`hiring_speed = 1`), nobody separates (`random_firing_probability = 0`), no quits; so a boom hires the whole unemployed pool and unemployment goes to 0% | Spec | ours | exp009: employment +11.5% in two years, unemployment 10.3% → 0% | partial: `SearchFrictionsLabourMarketClearer` (MD11, option); exp010: unemployment 10.3% → 2% under the engine, because of G14 | P1 |
| G14 | Labour productivity does not grow (`NoOpTFPGrowth`), so every percent of output growth needs a percent more workers from a fixed labour force | Spec | ours | exp010; exp011: labour-augmenting progress cuts labour demand on capacity-capped defaults (unemployment 10.3% → 14.4% at 0.25%/q), but under the engine output grows faster instead (G16) | partial: `LabourAugmentingGrowth` (MD12, option) | P1 |
| G15 | The TFP module (`SimpleTFPGrowth`) counts all net capital investment as productivity investment, so with the investment engine TFP grows about 3%/q (multiplier 1.88 after 20 quarters at a 0.25%/q base); TFP also scales intermediate and capital capacity, not labour demand | Spec | ours | G14 probes | open: not used | P2 |
| G16 | Demand growth is not anchored: firms scale demand by forecast growth, an AR(1) over the data history and the model's own realised growth, so extra supply (spare capacity, productivity) becomes faster growth | Spec | ours | exp011; exp014: a slack-aware forecast (MD13) holds unemployment at 5.5–6.9% after five years (2.4% without); a data-only forecast 3.6% | partial: `SlackAwareGrowthForecastingAutoReg` (MD13, option) | P1 |
| G17 | Nothing transmits higher prices or interest rates to spending: wages are paid at the current CPI (real wages fixed), households spend a fixed share of nominal income, investment ignores interest rates and financing | Spec | ours | exp012: brakes leave unemployment at 2–3.5%; exp013: gradual wage indexation (`cpi_indexation_speed`) works but the boom is not inflationary (0.3–0.4%/q), so there is little to transmit | partial: wage channel built (option); consumption and investment channels open | P1 |

### P. Prices, expectations and monetary policy

| ID | Problem | Kind | Source | Evidence | Status | Pri |
| --- | --- | --- | --- | --- | --- | --- |
| P1 | 5% per-firm price noise dominated the dynamics | Spec | ours | exp002 | done `60948b7` (0.0005) | — |
| P2 | Realised inflation equals the AR(1) forecast (self-fulfilling; referee R2.4) | Question | ours | exp003 | open | P2 |
| P3 | Forecast noise draw roughly doubles the inflation error: keep (paper) or drop? | Question | ours | exp003: CPI ratio 1.8 → 0.95 without it | decision pending | P2 |
| P4 | Taylor rule inert (zero by quarter 3), constant rate by default, and a TODO says `xi_pi` is estimated wrongly | Bug | ours | exp001; `default_synthetic_central_bank.py:168` | open; see upstream #83 | P2 |
| P5 | Firms do not pass cost increases into prices (cost-push weight 0), so higher wages raise demand rather than prices | Spec | ours | exp007; exp012: with the fixed cost-push term (P6), half pass-through improves CPI `sim / AR(1)` 1.93 → 1.38 on the engine, 1.84 → 1.21 on defaults (with all brakes) | partial: `settings.price_brakes`; candidate default | P1 |
| P6 | Cost-push inflation compared unit costs with the sector's price level, so it pulled prices down to costs (−10%/q) instead of passing on cost changes | Bug | ours | unit cost / price 0.895 at t=1; Sam's prior notes "prices cause shit to break" | done: uses unit-cost growth, with test | — |

### S. Initial state and stock-flow consistency

| ID | Problem | Kind | Source | Evidence | Status | Pri |
| --- | --- | --- | --- | --- | --- | --- |
| S1 | Stock-flow consistency: `macromodel/accounting.py` checks every quarter that the loan and deposit ledgers agree, bank equity and government debt move only by their flows, and money changes only by the deficit plus net exports; it separates the by-design unbacked flows from leaks | Gap | both | exp001 `accounts.csv`: all ledgers exact; money residual ≈ unbacked flows (up to 11% of GDP); unexplained ≤ 4% of GDP, early quarters only (S23) | partial: done once S9, S10, S13, S23 are closed | P1 |
| S2 | Firms made about zero profit: initial wages were value added minus investment (labour share 85%; SEA and France ≈ 59%) | Bug | ours | exp005 | done: `labour_share_from_sea` is the default (MD9); firm profits ≈ 24% of GDP | — |
| S3 | The re-initialisation path double-counts bank deposits (liabilities 1.65e16) | Bug | ours | exp004 | workaround: build data with matching settings | P2 |
| S4 | Bank deposits are negative on the normal path (−1.17e12) | Question | ours | probe | open | P2 |
| S5 | Initial Demand = Production + Inventory | Question | ours | `firm_tools.py:487` | open | P3 |
| S6 | GDP is forced to balance by adjusting imports/exports, which can hide inconsistencies | Spec | ours | `gdp.trade_adjustment` check: the adjustment is 0 in single-country runs | not active for one country; check in multi-country runs | P3 |
| S7 | Simulations modified their input data | Bug | ours | — | done `62d29d3` | — |
| S8 | Initial inventory read from the wrong parameter | Bug | ours | — | done `62d29d3` | — |
| S9 | Households receive income on "other financial assets" (about 19% of quarterly GDP) that nobody pays | Spec | ours | `money.unbacked_flows` | partial: `FirmSharesFinancialAssets` makes them shares in firms paying dividends (MD6); off by default until firms are profitable (S2) | P1 |
| S10 | Saving into "other financial assets" (about 11% of GDP per quarter) pays no one | Spec | ours | `money.unbacked_flows` | partial: paid to firms in `FirmSharesFinancialAssets` mode (MD6) | P1 |
| S11 | VAT was booked as government revenue but never paid by households (about 27 bn/q created) | Bug | ours | — | done: households pay VAT on consumption | — |
| S12 | Wage taxes were levied on the net wage while firms paid the gross (about 37 bn/q destroyed), and the wage bill was multiplied by the CPI a second time (gap growing with prices) | Bug | ours | — | done: taxes on the gross wage; wage bill = gross-up of wages received | — |
| S13 | Interest on government debt is added to the deficit but paid to no one | Spec | ours | about 4 bn/q | open: needs a bondholder (F3) | P3 |
| S14 | Firms' cash was charged for inputs used, not inputs bought | Bug | ours | — | done: cash follows purchases; used costs stay in profits | — |
| S15 | House sales charged buyers but never credited sellers: about 1 trillion destroyed per quarter | Bug | ours | — | done (Phase 1 commit) | — |
| S16 | Dissaving wiped households' overdrafts (`min(deposits, ...)` on a negative balance): 450–800 bn/q created | Bug | ours | — | done (Phase 1 commit), with test | — |
| S17 | Written-off household and firm loans cost the banks nothing | Bug | ours | — | done: losses reduce bank profits before tax (MD2), with test | — |
| S18 | Credit market omitted mortgages on other properties (543 bn at t=0) that banks and households record | Bug | ours | — | done (MD4) | — |
| S19 | A failing bank's whole loan book was deleted and its reserves zeroed; the government's injection was not in the deficit | Bug | ours | — | done (MD3) | — |
| S20 | Households' debt records kept loans after they were written off | Bug | ours | — | done | — |
| S21 | With a single bank there are no healthy banks to average over, so a failing bank was never recapitalised | Spec | ours | — | done: `MinimumCapitalBankDemography` (default) tops equity up to the solvency ratio (MD5) | — |
| S22 | Unemployment benefits were counted in the deficit but paid to no one (about 9 bn/q destroyed) | Bug | ours | `distribute_unemployment_benefits_to_individuals` was never called | done: paid with household labour income | — |
| S23 | A transient unexplained money residual in the early quarters | Question | ours | `money.unexplained`: at most 1.1% of GDP after the upstream merges (was 4%) | open | P3 |
| S24 | At t=0, 2.7% of households were underwater and held 40% of household debt: mortgages with no matching property (spoofed HFCS) | Data | ours | — | done (MD7): mortgages capped at property value; now 0.8% underwater holding 14% of debt; mortgages 698 bn (was 1,315; France ~850 bn) | — |
| S25 | Household default rule wrote off a household's whole debt at its first overdraft when underwater | Spec | ours | — | partial (MD8): default only when unable to pay; still 10–18 defaults/quarter (~2%/yr, real <1%); no collateral recovered yet | P2 |
| S26 | Household consumption jumps about 4.6% in the first quarter, then settles | Question | ours | exp001 figure; household consumption ratio 2.96 under MD9 | open: initial consumption vs income | P2 |
| S27 | Regression from S12: firms' wage bill lost its CPI factor, so nominal wages were frozen and real wages fell with prices | Bug | ours | the wage setter pays real wages; the CPI factor belonged on the employees' side | done: employees receive real wage × CPI, firms pay the gross-up of that | — |
| S28 | The baseline's accounting report shows a firm-loan borrower ledger residual of 3.5% of GDP (seed 7, t = 8) and unexplained money of 1.4%, although "Current state" says every ledger agrees exactly and unexplained money is at most 1.2% | Question | ours | `make baseline` at `7a8ac4d` and after MD11 (identical) | open | P2 |
| S29 | With the Taylor rule (`PolednaPolicyRate`) on, unexplained money reaches 15.6% of GDP | Question | ours | exp012 step 5 | open | P2 |

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
| M9 | Houses change hands far too often: about 12% of the stock per quarter (real: about 1%), 800–1,400 bn of sales per quarter | Spec | ours | Phase 1 decomposition | open | P2 |
| M10 | Interest on existing loans was an annual rate charged every quarter (4×) | Bug | upstream | now: firm loans 1.0%/yr, consumer loans 4.8%/yr, mortgages 2.3%/yr | done: upstream #83 and #85 merged (`40c8a1e`, `f12f78b`) | — |
| M11 | Poledna layoffs reported the sum of every firm's excess employees, negative ones included, as the number fired (−hires under search frictions); only the reported flows (`num_individuals_newly_fired`, `job_reallocation_rate`) were wrong | Bug | ours | exp010 | done: counts the workers actually fired, with test | — |

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
| E5 | Upstream fixes not yet merged: #56/#64/#67, `bug/government-expenditure` (#83 and #85 merged) | Infra | ours | `make upstream` | open | P2 |
| E6 | Scaling effects (1:100 vs 1:100,000) | Question | both | exp001: 10× agents changes nothing, but firms stay at 1 per industry (G5) | partial | P3 |
| E7 | Standardised outputs, dashboards, reporting to non-coders | Infra | CB7 | scorecard CSV/PNG per experiment | partial | P3 |
| E8 | Agent-level reporting; visualising the synthetic population | Gap | CB7 | — | open | P3 |
| E9 | Report our fixes upstream: rent regression, many-firm crash, data mutation, inventory mapping | Infra | ours | — | open | P3 |
| E10 | New-user induction; AI workflows not standardised | Infra | CB7 | partial: AGENTS.md, PROJECT.md | partial | P3 |
| E11 | The file merged from #104 is not ruff-formatted | Infra | ours | `credit_market/func/clearing.py` | workaround: excluded from the format check in the Makefile until upstream merges #104 | P3 |
| E12 | Housing market takes 92% of run time (row-wise pandas loops); blocks finer scales | Infra | ours | profile, 408 firms, 8 quarters: 8.2 of 8.9 s | open | P2 |
| E13 | Plugging in behaviour means editing closed `Literal` lists and hard-wired argument passing in `country.py`; god objects (`firms.py` 2,256 lines, 196 time series) | Infra | ours | 54 behaviour slots, 27 with alternatives; 3 files use hooks | open | P3 |
| E14 | Data and simulation configs duplicate firm settings, reconciled by a compatibility check and a re-initialisation path | Infra | ours | G5, S3, S8 all came from this | open | P2 |

### D. Data

| ID | Problem | Kind | Source | Evidence | Status | Pri |
| --- | --- | --- | --- | --- | --- | --- |
| D1 | Only the test sample data is on this machine: one year (2014 input–output tables, one spoofed HFCS wave, spoofed Compustat). The paper needs 2010–2017 and 38 countries with real micro-data | Data | ours | `sample_raw_data/`; `~/Documents/dev/phd/datasets` is empty | open: get the full raw data (likely on the INET server Sam used) | P1 |
| D2 | OECD ICIO 2022 update; ICIO tables are nominal (referee R1.5) | Data | both | — | open | P3 |
| D3 | Wage distributions | Data | CB7 | Nuffield bid | open | P3 |
| D4 | Household composition and demography (death, marriage, inheritance) | Gap | CB7 | — | open | P3 |

### UK. CB7 net-zero and UK policy (out of scope for us)

CB subsidies all-or-nothing; random retrofitting order; all household changes at once;
no EV investment; net-zero uptake decisions; alignment with DESNZ / UK TIMES;
alternative investment; consumer energy prices; granular policy shocks and scenarios.
Kept here so that their fixes are recognisable if they land upstream.

### Roadmap

Rules: every mechanism change is a new behaviour class selectable in config (the old one
kept), so each rung of the reviewers' ablation ladder is a config switch; every change
gets a modelling-decision row, a before/after scorecard and a register update.

| Phase | Goal | Issues | Done when |
| --- | --- | --- | --- |
| 1 | **Balanced accounts**: an automatic accountant (balance-sheet and flow checks every quarter), then fix what it finds | S1–S6, F2 | checks pass at t=0 and every quarter; GDP no longer forced to balance |
| 2 | **A growth engine**: spare capacity, a gradual investment rule towards expected demand, growth expectations on, and a source of productivity growth | G1–G4, G6 | France grows at a plausible, steady rate over 20+ quarters with stable unemployment and no explosion |
| 3 | **Prices and money**: prices from costs and demand (not copied from the forecast); a working Taylor rule; decide forecast noise | P2–P4 | inflation emerges from the model and responds to slack; the policy rate reacts |
| 4 | **Markets and government**: housing (rental market, speed), consumer credit, taxes and benefits, trade | M1–M5, F1, E12, E5 | each market passes a plausibility check; remaining upstream fixes merged |
| 5 | **Calibration done properly**: choose parameters by sensitivity analysis, informed priors, fit on 2010–2013, score on held-out years | R2, R3, R4, E4 | sanity gate passed after calibration; target met for France, then several countries |
| 6 | **Reviewer experiments**: ablation ladder (Poledna-like → full), simple-expectations / interactions-off, VAR benchmark, unemployment and growth in the results table, uncertainty | see `revision_plan.md` "Post" entries | the numbers the paper's Post entries wait for |

In parallel: **D1** (full raw data for 2010–2017 and 38 countries), needed by phase 5.

## Claims → evidence

| Claim in the paper | Figure / table | Experiment |
| --- | --- | --- |
| Beats AR(1) and IIASA on forecasting RMSE | `table:forecasting_gdp` | not yet reproduced |
