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
France) for the five aggregates. The four real aggregates are scored against Eurostat chain-linked volumes
(since 2026-10-21, R4; before, nominal data deflated by PPI or CPI); inflation against the seasonally adjusted
household consumption deflator and unemployment against the quarterly series (since 2026-10-22, R7; before, the
unadjusted CPI and the annual rate). Gates, in order:

1. **Accounts gate:** the accounting checks (S1) pass every quarter.
2. **Sanity gate:** no systematic drift. Mean simulated growth is within 0.5 pp/quarter
   of the data, unemployment stays within 2 pp of the data after 12 quarters, and
   20-quarter runs neither explode nor collapse.
3. **Target:** after calibration on pre-forecast data only, ratio ≤ 1 for every
   aggregate. For reference, the paper reports roughly 40–75% of the AR(1) RMSE.

## Data

Everything about the raw data lives here and in D1.

**Interim (since 2026-10-22): public data in full, micro-data still spoofed.** We do not have the paper's data. The
public sources (OECD, Eurostat, IMF, World Bank, BIS) can be downloaded and are, in
`~/Documents/dev/phd/datasets/macro_raw_data`. The household survey (HFCS) and the firm and bank accounts
(Compustat) are licensed, and only spoofed copies exist here. This is temporary: no result on it is a paper claim.
When the licensed data arrives, rebuild the folder with it and rerun the experiments.

| Dataset | Status | Location | Notes |
| --- | --- | --- | --- |
| Test sample | default for experiments and tests | `tests/test_macro_data/unit/sample_raw_data` | real public data cut to France or 2014; **spoofed** HFCS (France, 2014) and Compustat |
| Full public data | built, opt-in: `MACRO_RAW_DATA=~/Documents/dev/phd/datasets/macro_raw_data` | `make data` (`experiments/public_data.py`); `SOURCES.json` in the folder says what each file is | OECD ICIO 2023 edition (small version, 76 countries + ROW) for 2011–2017; Eurostat quarterly GDP, volumes, deflators, unemployment and financial balance sheets for every country; OECD house prices for every country. The other files are the sample's, most already multi-country and multi-year. Raw downloads are kept in `datasets/downloads/` |
| ICIO 2010 | missing | | the 2006–2010 bundle is behind a browser check: download `2006-2010_SML.zip` from https://oe.cd/icio into `datasets/downloads/icio/`, then `make data` |
| HFCS microdata (ECB) | licensed, not here | | the reader wants one wave per start year (`hfcs/<year>/`); waves 1–3 are about 2010, 2014, 2017. ECB research access, by application (weeks) |
| Compustat Global and CRSP/Compustat bank quarterly (WRDS) | licensed, not here | | through the university's WRDS subscription, if it includes them |
| Eurostat `namq_10_gdp`, chain-linked volumes (`CLV10_MEUR`, SCA); deflators and `une_rt_q` (R7) | scoring targets | `eurostat/namq_10_gdp_clv.csv`, `namq_10_gdp_deflators.csv`, `une_rt_q.csv` (France in the sample, every country in the full data) | from the Eurostat API (URLs in `scoring.py`, `public_data.py`); not read by the data pipeline |

**What the full public data gives.** France 2014 builds and runs on it. The input–output tables are identical to
the sample's (the sample is a subset of the same OECD file). Eurostat has revised the balance sheets since the
sample was taken: firm debt +2.1%, firm deposits +5.6%, bank equity −11.4%. Baseline ratios (defaults of 2026-10-22): GDP 1.03 → 1.01,
investment 1.08 → 1.03, the others within 0.01. The defaults stay on the sample: switching changes the initial state.

**What it cannot do yet.** No other start year or country builds:
- HFCS: only the spoofed 2014 France wave exists.
- The spoofed Compustat works only for 2014 (2011 fails on a missing column).
- The WIOD socio-economic accounts (labour shares, S2) end in 2014, and there is no newer release. Start years after
  2014 need another source (Eurostat `nama_10_a64` or OECD STAN), which is a data-processing change.
- Not refreshed: OECD business demography (`SSIS_BSC_ISIC4`, 5 countries; only `many_firms` reads it) and
  `EGDNA_PUBLIC` (France; unused). The OECD bank files ending in 2009 come from discontinued datasets.

**Getting the licensed data**, quickest first:
1. Ask INET (Sam Wiese, or the data contact) for `/data1/sam/inet-macro-data`, the folder the paper ran on (R1).
   Also ask whether their HFCS and Compustat agreements cover Pietro.
2. Compustat through WRDS.
3. Apply to the ECB for HFCS access.

## Parameters in use

No calibrated values are loaded anywhere: `macrocalib` has not been run, and of the paper's
posterior (Table `table:prior`) only the χ caps are used.
- **Estimated from data at initialisation:** input–output coefficients, initial stocks
  and balance sheets, tax rates, the Taylor-rule coefficients (ARDL on the policy-rate
  history), and each quarter the AR(1) growth and inflation
  forecasts.
- **Hand-set defaults** in `macromodel/configurations/*.py`: every behavioural parameter
  (price setting, target production, input constraints, utilisation rates, bank limits,
  credit and housing markets). Changed so far: `price_setting_noise_std` 0.05 → 0.0005 (MD1);
  price setting, wage indexation and the consumption floor (MD14); the growth engine and forecasts
  without a random draw (MD15); the government's plan (MD16); the paper's Taylor rule (MD18); benefits from
  SOCX cash spending (MD17, data configuration); households' financial-asset return from national accounts (MD20,
  data configuration); the paper's housing rules (MD21) and firm-loan limits (MD22).
- **The paper's posterior** (`table:prior`, estimated on Austria): only the χ caps on target production
  (0.53, 0.03, 0.18; MD19).

**Against the paper's stated values** (`appendix_model_description.tex`, calibration paragraphs; audit 2026-10-22).
Equal: target inflation 0.02, ω^M = ω^K = 0.85, h^max = 1.5, φ^FM = φ^FK = 0, φ^GM = 2, φ^ROW = 1,
γ^F = γ^H = 1, h^U = h^E = 0, φ^WN = 0 (`firms.wage_setter`; the 0.5 in `firms.offered_wage_setter` is never read, E15),
ρ^CAR = 0.08; since MD21 p^OS = 79/80 and p^RS = 7/8; since MD22 ρ^DtE = 1.0, ρ^RoE = 0.15, with ρ^RoA = 0.05 (time
unit: M17). Different:

| Parameter | Paper | Code default | Where | Tested |
| --- | --- | --- | --- | --- |
| Psychological pressure of renting μ^PS | 0.4 | 0.1 | `households.property` | exp034 |
| Buy-or-rent sensitivity φ^B | 0.001 per euro | 1 per euro (temperature 1, `/ 10000`) | `households.property` | exp037; M2 |
| Rent indexation φ^PIR, lag | 1, 1 | 0 | `households.property` | exp034 |
| Asking price and rent of a new listing | (1 + predicted HPI / RPI inflation) × value / average rent | markups 0 (`price_initial_markup`, `rent_initial_markup`) | `households.property` | M18 |
| Price and rent cuts of unsold properties p^PM, p^RM | 0.1964, 0.2848 | 0 (off) | `households.property` | formula needs /100 (exp034) |
| Purchase price and rent rules (φ^HP, β^HP; φ^HR, β^HR) | 42.9 Y^0.789; 17.2 Y^0.346 (Y yearly, Carro et al.) | 20 Y (Y quarterly: 5 years of income); 0.25 Y (MD21; before, 5 Y and a constant 0.2) | `households.property` | exp037, exp040 |
| Bank solvency ratio ρ^SR | 0.1 | 0.05 | `banks.functions.demography` | exp035: dormant |
| Consumer loans ρ^LTI-C | 0.36 | 0.5 | `banks.parameters` | M3; exp040: gov. 1.79 → 2.34 |
| Mortgages LTV, LTI, DSTI | ESRB national measures | 0.8, 3, 0.3 | `banks.parameters` | — |
| Reservation-wage period T^RW | 8 quarters | 0 (off) | `individuals` | ladder rung P4: dormant |

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
| MD10 | Investment as a flexible accelerator: replacement plus a fraction λ of the gap to desired capital (initial capital/output ratio at planned output), planned on expected demand (`PartialAdjustmentTargetCapitalInputsSetter`) | Standard investment theory; closing only part of the gap avoids the paper's runaway top-up | paper's full top-up (G2) | exp006–exp008: cycles without brakes; with desired capital on smoothed demand (`demand_smoothing` 0.10) growth is steady at 0.7%/q | default since MD15 (λ 0.10); describe investment |
| MD11 | Search frictions in the labour market: employees separate at s = 3% per quarter, firms post vacancies for the gap to desired labour (replacements included), and hires are capped by a Cobb-Douglas matching function M = μU^0.5 V^0.5, with μ set so the initial unemployment rate (10.3%) is a steady state (`SearchFrictionsLabourMarketClearer`, `settings.search_frictions`) | Real labour markets have job-to-unemployment flows and take time to fill vacancies; without them a boom hires the whole unemployed pool within a quarter (G13). Flows are calibrated to a steady state at the initial unemployment rate, as initial stocks are | quits by wage/wealth (`individuals_quitting`); a hiring-speed cap (`hiring_speed` < 1) | exp010: unemployment holds at 10.3% under today's defaults; under the growth engine it falls to 2% (no frictions: 0%) | default since MD15; describe the labour market |
| MD12 | Labour-augmenting technical progress: output per worker grows at an exogenous g per quarter in every industry (0.25%, about 1% a year), and real wages per worker grow with it (`LabourAugmentingGrowth`, `settings.labour_productivity_growth`) | On a balanced growth path output per worker rises and the labour share and capital-output ratio stay constant (Harrod-neutral progress); without it, output growth needs a proportional rise in employment from a fixed labour force (G14) | the TFP module (`SimpleTFPGrowth`, G15); g endogenous to investment | exp011: unemployment rises 10.3% → 14.4% on today's capacity-capped defaults; under the growth engine it stays near 2–4% because GDP growth rises instead (G16) | default since MD15; describe productivity growth |
| MD13 | Firms' expected growth falls when unemployment is below its initial level: AR(1) forecast − 0.2 × (initial − current unemployment rate) (`SlackAwareGrowthForecastingAutoReg`, `settings.growth_forecast_slack_aware`) | Firms extrapolating recent growth alone expect a boom to go on whatever the labour market; by Okun's law output is about twice as far above potential as unemployment is below normal, and firms expecting a tenth of that gap to close each quarter expect 0.2 × the unemployment gap less growth | forecast from pre-2014 data only (`DataOnlyGrowthForecastingAutoReg`, no lookahead) | exp014: unemployment 6.4% after five years (engine alone 2.4%); with cost pass-through and yearly wage catch-up 7.7% at q12 and 6.9% at q20, growth 0.4%/q | default since MD15; describe expectations |
| MD14 | Prices pass on half of unit-cost growth in place of half of expected inflation (`price_setting_speed_gf` 0.5, `_cp` 0.5); nominal wages close a quarter of the gap to the CPI each quarter (`cpi_indexation_speed` 0.25); no consumption floor (`minimum_consumption_fraction` 0) | Firms set prices from costs as well as expectations (the paper's equation has a cost term); wages are renegotiated about once a year, not every quarter; the floor counted every adult as unemployed, exceeded the income of 40% of households and was not in the initial state (S26) | each part alone (exp013, exp016); old rules selectable (`settings.pre_md14_prices_wages_consumption`) | exp015, exp016 (10 seeds): HH cons. 2.85 → 1.52, invest. 1.20 → 1.13, CPI 1.84 → 1.20; GDP 1.14 → 1.26, gov. cons. 2.05 → 2.26; unemployment 10.3% → 10.9–11.2% | **default since 2026-10-21**; describe prices, wages, consumption |
| MD15 | The growth engine is the default: firms start with spare capacity (utilisation 0.85, data and simulation), expected demand grows with the growth forecast, investment closes λ = 0.10 of the gap to desired capital per quarter on smoothed demand (MD10), search frictions with μ calibrated at the first quarter so the initial unemployment rate is a steady state (MD11), labour productivity +0.25%/q (MD12), the slack-aware growth forecast (MD13); and forecasts carry no random draw (`assume_zero_noise=True`, P3) | Firms do not run at full capacity (French manufacturing utilisation was about 81% in 2014); a quarterly adjustment of 0.10 (about a third of the capital gap a year) is in the range of estimated adjustment speeds, where 0.25 (two thirds a year) is fast; expectations are forecasts, and survey expectations are much smoother than outcomes; government spending follows a budget, not a random path. Without the draw the accelerator no longer turns forecast noise into investment swings | keep the draw (the paper); λ 0.25; old defaults selectable (`settings.pre_md15_no_growth_engine`, with `load_data(utilisation_rate=1.0)`) | exp020, `make baseline` (10 seeds, against volumes): GDP 1.50 → **0.99**, HH cons. 2.32 → 1.08, gov. cons. 6.70 → 1.90, invest. 1.11 → 1.09, CPI 1.09 → **0.86**; growth −0.07 → +0.19%/q (data 0.28%); unemployment q12 10.7% → 10.0% (data 9.4%) | **default since 2026-10-21**; describe the growth engine and expectations |
| MD16 | The government plans real consumption from an AR(1) on the growth rates of its past spending deflated by the CPI (`AutoregressiveGrowthGovernmentConsumptionSetter`, `deflator="cpi"`), in place of an AR(1) on log levels deflated by the PPI | Budgets extend the recent growth of spending; an AR(1) on log levels mean-reverts, so planned growth fades to zero; the CPI is closer to the price of what governments buy than the PPI, which fell with oil in 2014–16 | follow the economy's growth forecast; levels deflated by CPI (1.67); growth rates deflated by PPI (1.63); old rule selectable (`settings.pre_md16_government_consumption`) | exp021; `make baseline` (10 seeds): gov. cons. 1.90 → 1.42, GDP 0.99 → **0.94**, HH cons. 1.08 → 1.04, invest. 1.09 → 1.13; growth 0.28%/q (data 0.28%); unemployment q12 9.4% (data 9.4%) | **default since 2026-10-22**; describe government spending |
| MD17 | Other social benefits are OECD SOCX public social spending in cash only (`cash_social_benefits`, data configuration), not total public social spending (F6) | In-kind benefits (health, care) are government consumption in the national accounts; counting them also as transfers to households counts them twice (benefits 31% of GDP against France's 19.8%, deficit 18% against 4.6%) | keep the total (the paper's source) | exp024: deficit 18.4% → 6.2% of GDP, household income 80% → 67.5% (France ≈ 67%); gov. cons. 1.53 → 1.30, HH cons. 0.95 → 1.03; unemployment closer to the data | **default since 2026-10-22**; the paper's data section must change its source |
| MD18 | The policy rate follows the paper's Taylor rule, estimated by OLS on pre-sample data (`PolednaPolicyRate`), not a constant | The paper's rule; a constant rate cannot respond to the economy. On France the estimated rule cuts the rate to zero within four quarters, as the ECB did in 2014 (0.25% → 0.05%) | constant rate (the forked default); `SmoothTaylorRule` (annual CPI and output gap) | exp025, exp027: gov. cons. 1.53 → 1.47, invest. 1.20 → 1.14, others unchanged | **default since 2026-10-22**; as in the paper |
| MD19 | Target production is capped as in the paper, at the paper's posterior: Ŷ ≤ Q + χ (limit − Q) for labour, intermediate and capital stocks, χ^H 0.53, χ^M 0.03, χ^K 0.18 (`PaperTargetProductionSetter`, G4); the code's caps on purchases stay | Makes the code match the paper's equation and posterior (E2); firms plan below demand when their inputs bind, as in the paper | no caps on target production (old default, `settings.pre_md19_target_production`); χ = 1 (IIASA-like: growth stops, unemployment 14%) | exp026; exp023 (rung 13, on MD17–MD18, R7 targets): GDP 0.96 → 1.03, HH 1.03 → 1.04, gov. cons. 1.38 → 1.69, invest. 1.11 → 1.08; unemployment 9.3% / 8.2% → 10.0% / 9.1% (data 9.7% / 8.8%). The one adopted decision that costs accuracy: kept for fidelity to the paper's equation and posterior | **default since 2026-10-22**; describe the rule as the paper does, plus the purchase caps |
| MD20 | Households' other financial assets earn the national accounts' return: the return is set so their income equals households' property income received other than interest (Eurostat `nasa_10_nf_tr` D4 − D41, S14: dividends, investment income of insurance and pensions, rents on land; deposits earn interest separately; France 2014: 82.6 bn a year, 0.39% a quarter), in place of the survey's ratio of financial income to financial assets (1.93% a quarter on the spoofed HFCS) (`financial_income_from_national_accounts`, data configuration) | The return on households' financial wealth is a macro quantity the national accounts measure; the survey ratio (7.7% a year) is three times France's and paid by no one (S9), so its excess was 17% of GDP of unbacked income compounding on unbacked savings (G18) | the survey ratio (old default; `settings.SURVEY_RETURN`); dividends from firms (MD6, exp039: not ready) | exp031, exp040 (on S32): HH 1.05 → 1.10, invest. 1.00, gov. 1.78; unbacked income 21% → 4% of GDP; the rest of the world's residual net lending −13% → −1% of GDP | **default since 2026-10-23**; the data section names the source |
| MD21 | The paper's housing rules: owners keep their home with probability 79/80 a quarter and renters with 7/8 (the paper's p^OS, p^RS); a renter can pay rent up to a quarter of its income, a buyer up to 5 years of its income (`households.property` parameters) | Owners stay about 20 years and renters 2 (the paper's values; 0.5 meant everyone reconsidered every other quarter, so 2.5% of the stock sold a quarter against France's ≈ 0.75%). A renter's budget was a constant 0.2 money units whatever its income (exponent 0), so no home was ever rented; 25% of income is the usual affordability benchmark. A buyer could pay 5 × *quarterly* income (≈ €47,000 against a median home of €161,000), a likely quarterly/yearly slip: 5 years is close to the paper's rule at the median (≈ €175,000). The two budget rules keep the code's form (coefficient × income^exponent), not the paper's concave one | each part alone (exp034, exp037; purchase affordability alone churns the market at the old moving probabilities: 11% sold a quarter); the paper's buy-or-rent sensitivity (M2, not adopted: the cost of buying is still incomplete); old values selectable (`settings.pre_md21_housing_rules`) | exp040: GDP 1.01 → 0.97, HH 1.10 → 1.00, invest. 1.00 → 1.05, gov. 1.79; growth 0.20% → 0.29%/q (data 0.28%), unemployment 9.6% / 8.5% (data 9.7% / 8.8%); house sales 1.7% → 0.27% and new rentals 0 → 1.0% of the stock a quarter | **default since 2026-10-23**; as in the paper for moving; describe the budget rules |
| MD22 | The paper's firm-loan limits: debt up to the capital stock's value (ρ^DtE = 1.0, was 0.03) and return on equity 0.15 (was 0.05); return on assets 0.05 as before (`banks.parameters`) | The paper's values; a bank lending at most 3% of a firm's collateral is not a credit market. Their time unit (quarterly or annual) is open (M17) | the paper's consumer-loan ratio 0.36 as well (not adopted until M3 settles the rule's base: it moves gov. cons. 1.79 → 2.34 through almost no credit); old values selectable (`settings.pre_md22_bank_limits`) | exp035, exp040: no change on the sample data (firms ask for no credit, F2, G9) | **default since 2026-10-23**; as in the paper |

## Model map: paper ↔ code

Every rule the default model uses, against the paper's appendix (`appendix_model_description.tex`, labels in
`code`). Status: **=** as in the paper; **≠ MD#** our decision; **≠ (ID)** an upstream default that departs
from the paper, open in the register; **+** not in the paper. Config slots are `CountryConfiguration` paths;
`make figures` draws this structure (I4). Revision-plan entries that wait on a row are in "Claims → evidence".

| Block | Paper | Default in code | Status |
| --- | --- | --- | --- |
| Growth expectations | AR(1) on log real gross output, deterministic (`sec:expectations`) | `economy.growth` `SlackAwareGrowthForecastingAutoReg`: AR(1) on real growth rates, minus 0.2 × the unemployment gap | ≠ MD13 |
| Inflation expectations | AR(1) on PPI / CPI / HPI / RPI, deterministic | `economy.inflation` `InflationManualForecastingAutoReg`; `assume_zero_noise=True` | = (MD15; ROW still draws noise: M15) |
| Firm demand | sectoral growth × idiosyncratic growth (φ^Q_F) × previous demand (`eq:firm_exp_demand`) | `firms.demand_estimator` sectoral speed 1, firm speed 0 | = (φ^Q_F = 0; MD15 turned growth on) |
| Target production | min of demand + inventory target, χ caps on labour, inputs, capital (`eq:firm_target_production`) | `firms.target_production` `PaperTargetProductionSetter`: no inventory target, χ caps on target production at the posterior (0.53, 0.03, 0.18); plus the code's caps on intermediate purchases (capital, weight 1) | = MD19 (+ purchase caps) |
| Work effort, labour demand | h_max caps overtime (`eq:we`); Ĥ = Ŷ | `firms.labour_productivity` `WorkEffortLabourProductivitySetter`, h_max 1.5 | = (G12) |
| Productivity | constant coefficients | `firms.productivity_growth` `LabourAugmentingGrowth` 0.25%/q | + MD12 |
| Production | Leontief in labour, intermediate and capital stocks (`eq:firm_production`) | `firms.production` `PureLeontief`; capacity = stock × productivity; initial stocks sized for utilisation 0.85 | = (ω = 0.85 as the paper's appendix; MD15) |
| Wages | (1 + E[π^PPI]) (1 + μ^WN) φ^WE w(t−1) (`eq:firm_wages`) | `firms.wage_setter`: index closes 25% of the gap to the realised CPI each quarter; tightness markup 0 | ≠ MD14 |
| Prices | (1 + E[π^PPI]) (1 + φ^DP π^DP) (1 + φ^CP π^CP) P(t−1), π^CP = U/P − 1 (`eq:firm_prices`) | `firms.prices`: weights 0.5 on expected inflation and 0.5 on unit-cost growth, no demand pull; noise 0.05% | ≠ MD1, MD14, P6 |
| Intermediate inputs | d · Ŷ minus φ^M × stock gap (`eq:firm_target_intermediate_inputs`) | `firms.target_intermediate_inputs`, φ^M = 0 | = |
| Investment | d · Ŷ minus φ^K × stock gap (`eq:firm_target_capital_inputs`) | `firms.target_capital_inputs` `PartialAdjustmentTargetCapitalInputsSetter`: replacement + 0.10 × gap to desired capital on smoothed demand | ≠ MD10, MD15 |
| Credit demand and frictions | financing gaps; purchases cut by φ^FM, φ^FK × unmet credit (`eq:ii_demand`, `eq:cap_demand`) | φ^FM = φ^FK = 0 | = (values; G9) |
| Firm accounts, bankruptcy | `eq:firm_profits` – `eq:firm_equity`; replaced with zero deposits and debt | `firms.demography` `DefaultFirmDemography` | = (S28, S30 fixed) |
| Government consumption | AR(1) on real consumption, at E[π^PPI] (`eq:gov_cons`) | `government_entities.consumption` `AutoregressiveGrowthGovernmentConsumptionSetter`: AR(1) on growth rates of CPI-deflated spending | ≠ MD16 |
| Social benefits | w^U and sb^O grow with predicted growth (`eq:gov_ub`, `eq:gov_ob`); initial from SOCX | `central_government.social_benefits` `GrowthSocialBenefitsSetter`; initial = SOCX public cash spending | = rule; source ≠ MD17 |
| Revenue, deficit, debt | fixed tax rates (`eq:gov_revenue` – `eq:gov_debt`) | as the paper; rates from OECD | = rule; levels ≠ (F7) |
| Household income, consumption | max(floor, (1 − SR) E[Y], smoothing) (`eq:hh_consumption_full`); SR per household from HFCS | `households.consumption` floor 0 (MD14), smoothing 0; `households.saving_rates` `AverageSavingRatesSetter`: one income-weighted rate for all | ≠ MD14, (M13) |
| Social transfers to households | by household type, income, wealth, debt | `households.social_transfers` `EqualSocialTransfersSetter`: equal per household | ≠ (M13) |
| Financial assets | income φ^FA W^OFA, φ^FA from HFCS | `households.financial_assets` `DefaultFinancialAssets`, φ^FA from national accounts property income (MD20); MD6 shares in firms: option | = rule; φ^FA ≠ MD20 (S9, S10 unbacked) |
| Housing demand and rents | moving probabilities p^OS, p^RS; budgets 42.9 Y^0.789 and 17.2 Y^0.346; buy-or-rent logit; rents indexed φ^PIR, cut while vacant (`eq:mpp` – `eq:rent_red`) | `households.property`: the paper's moving probabilities, budgets 5 years of income and 25% of income (MD21); logit sensitivity 1 per euro; rents never change (indexation 0; `households.rent` is never called) | = moving; budgets ≠ MD21; ≠ (M2, M14, M18) |
| Housing market | random sequential matching | `housing_market.clearing` `AutomaticHousingMarketClearer` (optimal assignment) | ≠ (E12, M9) |
| Individuals | labour quality drifts (h^U, h^E); reservation wage = max(benefit, past wages) (`eq:ind_reservation_wages`) | h^U = h^E = 0; `DefaultReservationWageSetter` | = |
| Rest of the world | exports, imports, prices indexed to modelled production and prices (φ^ROW = 1) | `row_configuration`: exports and imports from AR(1) forecasts with a random draw | ≠ (M15) |
| Goods market | random search and matching, priority by price (φ^GM = 2) and size (`eq:gm`) | `WaterBucketGoodsMarketClearer`, price temperature 2 | = |
| Labour market | fire to target, hire in random order, no separations (`eq:lm_firing`, `eq:lm_hiring`) | `labour_market.clearing` `SearchFrictionsLabourMarketClearer`: 3% separations, matching function | ≠ MD11 |
| Credit market | random order, n^LF / n^LH banks by rate | `WaterBucketCreditMarketClearer`, 5 banks | = |
| Bank rates and limits | ARDL error correction on the policy rate (`eq:bank_ir`); DtE, RoE, RoA, LTV, LTI, DSTI limits | `banks.interest_rates` `DefaultInterestRatesSetter`; limits from `banks.parameters`: firm limits as the paper (MD22), consumer loans 0.5 (paper 0.36) | = rule; = firm limits (MD22); consumer ≠ (M3) |
| Bank failure | bail-in by other banks | `banks.demography` `MinimumCapitalBankDemography`: government recapitalises to the minimum ratio | ≠ MD3, MD5 |
| Central bank | Taylor rule estimated by OLS (`eq:cb_policy_rate`) | `central_bank.policy_rate` `PolednaPolicyRate` (France: ρ 0.93, ξ_π 1.51, ξ_γ 4.05 on quarterly PPI inflation and gross-output growth) | = MD18 |
| Initial state | ICIO, SEA, HFCS, Compustat, OECD, World Bank | `macro_data`: wages from SEA labour shares (MD9), mortgages capped at property value (MD7), utilisation 0.85 (MD15), cash benefits (MD17), the financial-asset return from national accounts (MD20), investment split by capital compensation (S32 fix) | ≠ MD7, MD9, MD17, MD20 |

Lessons from exp002 (before MD1): the old 5% price noise per quarter was the main pathology; growth
expectations, χ caps, bank limits, a Taylor rule or many firms changed little on the defaults of the time.

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
| exp015 | How does the candidate model score against today's defaults, and what does each part contribute? | done | A (cost pass-through + yearly wage catch-up) improves HH cons., investment and CPI (1.84 → 1.06), worsens gov. cons.; B (A + engine) grows but stalls after three years and misses the unemployment gate by 0.6 pp. The slack-aware forecast is B's key part; the work-effort cap has no effect. `outputs/exp015_candidate_model/` |
| exp016 | Does removing the consumption floor (S26) fix the start-up jump? | done | Yes: HH cons. ratio 2.85 → 1.71 on defaults; candidate B's start-up shock goes, unemployment 10.7% at q12 and 8.1% at q20 (data 9.4%, 8.4%), growth 0.6%/q in the last two years; GDP ratio worsens (1.14 → 1.24). `outputs/exp016_consumption_floor/` |
| exp017 | Is the growth engine ready to be the default, on the new defaults? | done | It passes the sanity gate, the first configuration to do so: unemployment 9.9% at q12 and 8.5% at q20 (data 9.4%, 8.4%), growth 0.2–0.4%/q, GDP ratio 1.14 (defaults 1.18); but investment 2.50 (lumpy, seed-to-seed), HH cons., gov. cons. and CPI worse. Spare capacity is needed. `outputs/exp017_engine_on_new_defaults/` |
| exp018 | With many firms, is the growth engine's investment less lumpy? | done | Barely: investment ratio 2.50 → 2.39 with 408 firms, so the poor investment forecast is the engine's dynamics (early burst, 1.1%/q vs 0.8%), not lumpiness; unemployment 9.6% at q12 and 8.4% at q20 (data 9.4%, 8.4%). `outputs/exp018_engine_many_firms/` |
| exp019 | Do financing limits with realistic bank lending limits tame the engine's investment? | done | No: with the paper's bank limits alone the investment ratio is 2.34 (2.50 without); with capital purchases cut by unmet credit the economy goes into recession (unemployment 16–18%). Only 2 of 18 firms want long-term credit and both already owe more than their capital is worth (spoofed balance sheets, D1). `outputs/exp019_financing_limits/` |
| exp020 | Why is the growth engine's investment forecast poor? | done | The random draw in firms' growth forecast and in the government's spending path (P3): without it investment volatility falls from 2.5% to 0.7%/q within a run; with a slower gap adjustment (λ 0.10) too (candidate C), scored against volumes: GDP **0.98**, HH cons. 1.08, gov. cons. 1.89, invest. 1.08, CPI **0.86**, unemployment 10.0% / 9.4% at q12 / q20. `outputs/exp020_engine_investment/` |
| exp021 | Can the government's spending plan track 2014–16? | done | Yes, mostly: planning on an AR(1) of past growth rates of CPI-deflated spending (in place of log levels deflated by PPI, which mean-revert and fell with oil) takes gov. cons. 1.90 → 1.42, GDP 0.99 → 0.94; growth 0.3%/q, unemployment 9.4% / 8.1% at q12 / q20 (data 9.4%, 8.4%); investment 1.09 → 1.13. `outputs/exp021_government_consumption/` |
| exp022 | Are today's defaults a plateau or a knife edge? | done (rerun on MD17–MD19, R7 targets) | Plateau for GDP (0.99–1.03), HH cons. (1.03–1.09), CPI (0.73–0.76) and unemployment at q12 (9.5–10.6%; data 9.7%) across every one-at-a-time change. Gov. cons. and investment are sensitive to the investment rule: λ 0.05 gives 1.30 / 0.93, λ 0.20 2.53 / 1.21; demand smoothing likewise (in-sample: not a reason to retune). The rest of the world's forecast noise changes nothing (M15). Many firms: similar ratios (gov. cons. 1.45). With no source of growth the economy still grows about 0.2%/q and unemployment falls to 7.4% by q20 (G18; 5.8% before MD17–MD19). `outputs/exp022_robustness/` |
| exp023 | What does each decision contribute? The ablation ladder on France (R1.1, R2.1) | done (rerun 2026-10-23 on MD22, with the P8 and S32 fixes in every rung) | From an IIASA-like model through the paper's innovations (P0–P4) and the model as forked (0) to today's defaults (16). The two noise removals carry most of the gain in the ratios: price noise MD1 (GDP 2.86 → 1.46, gov. cons. 28.7 → 7.1, unemployment at q20 20.0% → 10.3%) and deterministic forecasts MD15 (GDP 2.44 → 1.00, HH 2.25 → 0.96, gov. 7.3 → 2.0, CPI 1.66 → 0.74); MD14 cuts the household error by almost two thirds (6.60 → 2.44); the growth-engine rungs (MD15 capacity, MD10–MD13) bring growth and unemployment towards the data at a cost in the noisy ratios. MD16 and MD17 bring gov. cons. 2.01 → 1.41; MD18 GDP 0.96 → 0.99, invest. 1.08 → 1.16; MD19 GDP 0.99 → 1.01, gov. cons. 1.47 → 1.87, unemployment 9.1% → 10.0% at q12 (data 9.7%); MD20 HH 1.05 → 1.10, invest. 1.03 → 1.00; MD21 GDP 1.01 → 0.97, HH 1.10 → 1.00, unemployment 9.6%; MD22 nothing (firms ask for no credit). Household credit (P3) and reservation wages (P4) change nothing on the sample data (dormant, E8). Single order only: leave-one-out in exp025 (not rerun on MD20–MD22). `outputs/exp023_ablation_ladder/` |
| exp024 | Do realistic government and household accounts change the dynamics (F6, S9, S31)? | done (after M16) | Cash benefits (SOCX cash, `cash_social_benefits`): deficit 18% → 6% of GDP, household income 80% → 67%; GDP 0.97 (same), HH cons. 0.95 → 1.03, gov. cons. 1.53 → 1.30, invest. 1.20 → 1.12, CPI 0.86; unemployment 9.3% / 8.3% at q12 / q20 (data 9.4%, 8.4%; defaults 9.0%, 7.6%). Adding firm shares (MD6) removes 19% of GDP of unpaid income at once and collapses demand (unemployment 21%). `outputs/exp024_government_accounts/` |
| exp025 | Which elements of today's defaults matter, independent of order? Leave-one-out (R1.1, R2.1) | done (rerun on MD17–MD19, R7 targets) | Load-bearing: the price-noise fix MD1 (without it GDP 2.93, gov. cons. 22.5, unemployment 16% at q20), deterministic forecasts MD15 (GDP 1.99, HH 2.15, gov. 3.75), MD14 (HH 6.76, unemployment 5.8% at q20), spare capacity (no growth, unemployment 14.1% at q20). Moderate: the government plan MD16 (gov. 1.99 without), cash benefits MD17 (gov. 2.11 without, HH 0.97), the paper's caps MD19 (without: GDP 0.96, gov. 1.38, unemployment 9.3% / 8.2% against data 9.7% / 8.8%; with: 10.0% / 9.1%), productivity growth MD12 (HH 1.17 without, unemployment 7.4% at q20). Small: the Taylor rule MD18 (HH 1.07, invest. 1.13 without), growth expectations, search frictions, slack-aware expectations (no longer needed to keep unemployment on track once the caps are on), SEA labour shares, Leontief production; without the housing market GDP and HH improve slightly but gov. cons. worsens (2.09). Without partial-adjustment investment gov. cons. and investment improve (1.02, 1.00; in-sample). Dormant: household credit, reservation wages. `outputs/exp025_leave_one_out/` |
| exp026 | Does the paper's target-production rule (χ caps on target production, G4) change today's model? | done | At the paper's posterior (χ^H 0.53, χ^M 0.03, χ^K 0.18): GDP 1.00, HH cons. 0.99, gov. cons. 1.93, invest. 1.07, CPI 0.86; unemployment 9.7% / 8.6% at q12 / q20 (data 9.4%, 8.4%; defaults 9.0%, 7.6%). With χ = 1 (IIASA-like) growth stops and unemployment reaches 14%. The paper's rule works with the growth engine: E2's text and the code can match. `outputs/exp026_paper_target_production/` |
| exp027 | The decision options together: cash benefits (F6), Taylor rule (P4), the paper's target-production caps (G4) | done; adopted as MD17–MD19 (2026-10-22) | Close to additive. Candidate E (all three): GDP 1.03, HH cons. 1.04, gov. cons. 1.69, invest. 1.08, CPI 0.86; unemployment 10.0% / 9.1% at q12 / q20 (data 9.4%, 8.4%); growth 0.2–0.3%/q. More faithful to the paper and to France's accounts at a cost of about 0.05 on the GDP and HH ratios (in-sample). `outputs/exp027_candidate_e/` |
| exp028 | With capital valued correctly (S30), do financing limits brake investment? (G9, repeats exp019) | done | No change from exp019: the paper's bank limits alone change nothing; with capital purchases cut by unmet credit, unemployment reaches 15% at q20. Healthy firms never ask for credit (they hoard deposits, F2); credit demand comes only from the two firms that start loss-making on the sample data (S32), which fail the return-on-assets test and get nothing, so the credit gap cuts their capital purchases by 18–27 bn a quarter. `outputs/exp028_financing_limits_after_s30/` |
| exp029 | Does inflation respond to slack once wages do? A wage Phillips curve (P2) | done | Weakly: with κ = 0.05–0.2 quarterly CPI inflation rises from 0.27% to 0.28–0.29% (data 0.18%), the ratios move by ±0.03 and unemployment does not change; the unemployment gap is small (about 1.3 points), so wage pressure is small. With the Taylor rule the policy rate falls to 0.23%/q. Built as an option (`unemployment_gap_sensitivity`, default 0); no default change proposed. `outputs/exp029_wage_phillips_curve/` |
| exp030 | Where does the inflation level come from? (P2, next step 3) | done | From the expectation term. Prices grow by 0.5 expected PPI inflation + 0.5 unit-cost growth, and import prices follow domestic prices (as in the paper), so the only nominal anchor is the AR(1) on 2000–2013 PPI (0.37–0.42%/q; the history is cut at 2014-Q1, no look-ahead). Realised CPI inflation climbs towards it (0.20% at q4, 0.33% at q20, mean 0.26%; data 0.16%) and the markup drifts up 11.6% → 12.1% while prices outpace costs. Prices from unit costs only: no anchor, inflation exactly 0, markup flat, CPI ratio 0.74 → 0.70, HH 1.04 → 1.00, gov. 1.69 → 1.81. Expectations only: 0.35%/q, CPI 0.99. Without productivity growth inflation is unchanged (wages grow with productivity); full wage indexation raises it to 0.29%. No default change: the level is the weight on expectations times the pre-2014 mean, and the 2014–16 fall (oil, euro-area lowflation) is information the model does not have; choosing the weight on the CPI ratio would be fitting it. `outputs/exp030_inflation_level/` |
| exp031 | Households' financial income at the national accounts' level (S9, S31, G18; next step 2) | done; adopted as MD20 (2026-10-23) | Option `financial_income_from_national_accounts` (data, off by default): the return on other financial assets pays households' property income net of interest (Eurostat D4 − D41, 82.6 bn a year for France 2014), 0.39%/q instead of the spoofed survey's 1.93%/q. Household income 74.6% → 57.8% of GDP; initial consumption unchanged (matched to the input–output tables). Ratios: GDP 1.03 → 1.02, HH 1.04 → 1.11, gov. 1.69 → 1.62, invest. 1.08 → 1.12, CPI 0.74 → 0.74; growth and unemployment unchanged. Fixed-point check (no productivity growth, zero growth forecast, government without trend): GDP growth −0.03%/q (was 0.2–0.3%/q with the government's trend, G18), and household consumption drifts 0.04%/q instead of 0.11%/q with the anchored return. Removes 17% of GDP of income nobody pays; worse household-consumption ratio in-sample. `outputs/exp031_financial_income/` |
| exp032 | The profit tax at the national accounts' effective rate (F7; next step 4) | done | Option `effective_profit_tax` (data, off by default): the rate that raises corporate income tax receipts (gov_10a_taxag D51B_C2, 55.3 bn in 2014) on the model's initial profits of firms and banks, 12.7% instead of the statutory 38%; initial corporate taxes 8.5% → 2.8% of quarterly GDP. As expected the money moves from the government to firms' deposits: firms' net lending +9.7% → +14.3% of GDP at t = 1, the government's −6.1% → −10.7%; growth, unemployment and inflation do not move; ratios GDP 1.03, HH 1.04, gov. 1.69 → 1.84, invest. 1.08 → 1.11. With the national-accounts return as well (S9): gov. 1.60, HH 1.11, invest. 1.14, the rest of the world's net lending −12% → −1% of GDP (the dashboard booked households' unpaid financial income to it). Not adopted alone: it widens the deficit, since income and production taxes raise too little; F7 needs every rate calibrated together. `outputs/exp032_effective_profit_tax/` |
| exp033 | Firms' investment split by capital compensation (S32) | done; adopted as the S32 fix (2026-10-23) | The default split divides SEA capital compensation by the investment in each industry's *product* (`_add_country_investment`), so accommodation (I), water and waste (E), mining (B) and energy (D) get capital costs of 93%, 91%, 93% and 62% of value added and start loss-making. Option `investment_shares_from_capital_compensation` (capital compensation over its total): 13–31% in those industries, 46% in real estate, no industry loss-making; totals unchanged. Firm I's default every 8 quarters and the bank-loss spikes (banks' net lending −9% and −10% of GDP at t = 9 and 18) disappear. Ratios: GDP 1.03 → 1.01, HH 1.05 → 1.05, gov. 1.66 → 1.87, invest. 1.11 → 1.03, CPI 0.74; growth and unemployment unchanged. `outputs/exp033_investment_shares/` |
| exp034 | The paper's housing parameters (M9, M14, M2) | done; moving probabilities adopted in MD21 (2026-10-23) | Owners and renters reconsider their home with probability 0.5 a quarter by default; the paper's 79/80 (owners) and 7/8 (renters) cut house sales from 2.5% to 0.14% of the stock a quarter (France: roughly 0.75%) and improve the ratios: GDP 1.03 → 0.98, HH 1.05 → 0.99, invest. 1.11 → 1.15, gov. 1.66 → 1.67; growth 0.21% → 0.26%/q (data 0.28%), unemployment 10.0% → 9.8% at q12 (data 9.7%). The paper's renting pressure 0.4 changes little (gov. 1.96). Rents indexed to the CPI (φ^PIR = 1): small (gov. 2.08, invest. 1.11). No house is newly rented in any step (M2). The paper's price and rent cuts for unsold properties are unusable as written (1 − exp ε with ε ~ N(1.45, 0.49): a missing /100) and stay off. `outputs/exp034_paper_housing/`; scoring now reports house sales and new rentals as shares of the stock |
| exp035 | The paper's stated values for wages and banks (parameter audit) | done; firm-loan limits adopted as MD22 (2026-10-23) | No offered-wage markup and the solvency ratio 0.1: identical runs. The first is not wired (`firms.offered_wage_setter` is never called; the markup in use is `wage_setter`'s, already 0 as in the paper); the second is dormant (the bank's equity stays above both thresholds). The paper's bank limits (firm debt-to-equity 1.0, return on equity 0.15, consumer loans 0.36): GDP 1.03 → 1.01, HH 1.05 → 1.06, gov. 1.66 → 1.81, invest. 1.11 → 1.00, CPI 0.75; growth and unemployment unchanged. `outputs/exp035_paper_parameters/` |
| exp036 | The candidate decisions together (candidate F: S32, S9, moving probabilities, bank limits) | done; superseded by exp040 | In order: S32 GDP 1.03 → 1.01, invest. 1.11 → 1.03, gov. 1.66 → 1.87; + S9 HH 1.05 → 1.10, invest. 1.00; + moving probabilities GDP 0.99, HH 1.02, invest. 1.05, growth 0.25%/q; + bank limits (F) GDP **0.98**, HH **1.00**, gov. 1.83, invest. 1.10, CPI 0.75, growth 0.25%/q (data 0.28%), unemployment 9.9% / 8.7% at q12 / q20 (data 9.7% / 8.8%), house sales 0.11% of the stock a quarter. Not additive for investment (the bank limits help alone, exp035, and hurt here); government consumption is the cost (rationing noise). `outputs/exp036_candidate_f/` |
| exp037 | Can households rent? Affordability in the housing market (M2) | done; rent and purchase affordability adopted in MD21 (2026-10-23) | A household deciding to rent can pay up to 0.2 money units whatever its income (coefficient 0.2, exponent 0), so none finds a home; a buyer can pay up to 5 times its *quarterly* income (about €47,000 against a median home of €161,000; the paper's rule gives about €175,000). Rent up to 25% of quarterly income (`rent_affordability`): new rentals 0% → 0.68% of the stock a quarter, GDP 1.01, HH 0.98, gov. 1.89, invest. 1.02, CPI 0.77 (hypothesis wrong: it was to change little). Adding purchases up to 5 years of income churns the market (11% sold and 11% rented a quarter; HH 1.44, gov. 2.90); the paper's sensitivity φ^B does not calm it, the paper's moving probabilities do (sales 0.38%, rentals 0.94%; GDP 0.98, HH 0.94, gov. 2.25). Rent affordability with the moving probabilities only: GDP 0.99, HH 0.99, gov. 2.05, invest. 1.02, CPI 0.73, unemployment 9.8% / 8.9% (data 9.7% / 8.8%), sales 0.15% and rentals 0.04% a quarter. Government consumption is again the cost. `outputs/exp037_housing_affordability/` |
| exp038 | Can households' financial assets pay dividends once their return is the national accounts'? (S9, MD6, F2) | done | After S9 (unpaid income 4% of GDP), firm shares paying dividends (MD6) no longer collapse demand (exp024: unemployment 21%), but the dividends (firms' net lending 9.6% → 4.0% of GDP) exceed the income they replace: growth 0.20% → 0.31%/q (data 0.28%), unemployment 9.0% / 7.7% at q12 / q20 (data 9.7% / 8.8%), HH 1.10 → 1.57, gov. 2.56, invest. 1.26. With the investment split by capital compensation as well (S32): HH 1.16, invest. 1.16, growth 0.27%/q, unemployment 9.4% / 8.1%. The payout (Eurostat ratio on after-tax profits) needs checking against households' dividend income before MD6 can be a default. `outputs/exp038_dividends_after_s9/` |
| exp039 | Dividends that pay exactly households' financial income (F2, MD6, S9) | done | The Eurostat payout ratio (0.46) counts households' own operating surplus and mixed income (212 of 334 bn in 2011) as distributed profits. Option `payout_from_national_accounts` (data): initial dividends equal households' D4 − D41, payout 0.37 with S32. On S9 and S32, firm shares at the matched payout keep growth (0.19%/q) and unemployment (10.2% / 9.1%) at the S9-and-S32 step and cut firms' net lending 10.3% → 5.9% of GDP (F2); gov. 1.78 → 1.71, invest. 1.00, GDP 1.01 → 1.03, but HH 1.10 → 1.30, mostly a one-off fall in household consumption at q2 (−0.64% against −0.09%) as dividends take over from the initial income, plus noisier income after (within-run std 0.31% against 0.18%): check the first dividend's timing. At the Eurostat payout: growth 0.27%, unemployment 9.4% / 8.1%, gov. 2.52. `outputs/exp039_dividends_matched/` |
| exp040 | The decisions adopted on 2026-10-23 together (candidate G: S32 fix, MD20, MD21, MD22) | done; adopted | From the defaults before 2026-10-23, in order: S32 GDP 1.03 → 1.01, invest. 1.11 → 1.03, gov. 1.66 → 1.87; + MD20 HH 1.05 → 1.10, invest. 1.00, gov. 1.78; + MD21 GDP **0.97**, HH **1.00**, invest. 1.05, gov. 1.79, CPI 0.75, growth 0.29%/q over 12 quarters (data 0.28%; was 0.21%), unemployment 9.6% / 8.5% at q12 / q20 (data 9.7% / 8.8%), house sales 0.27% and new rentals 1.0% of the stock a quarter (were 2.5% and 0); + MD22 identical (firms ask for no credit, F2). The paper's consumer-loan ratio (0.36, not adopted, M3) moves the ratios more than any decision here: gov. 1.79 → 2.34, HH 0.96, invest. 1.12, through consumer credit that is almost nothing (M3), so the government-consumption ratio is fragile to small changes in demand. The dashboard: no periodic firm default, the rest of the world's residual net lending −13% → −1% of GDP (it had absorbed the unpaid income), households net-borrow about 2.5% of GDP (France 2014: net lending ≈ +3%, S31). Hypothesis right on the ratios and gates; sales lower than expected (0.27%, France roughly 0.75%). `outputs/exp040_candidate_g/` |

### Baseline scorecard history

`make baseline` run after each change on `main`: `sim / AR(1)` RMSE ratio, plus the
mean quarterly real GDP growth (data: +0.28% in chain-linked volumes; +0.64% deflated by PPI, the target
before R4) and the median unemployment rate after 12 quarters (data: 9.4%). Rows above the R4 line are
scored against PPI- or CPI-deflated data.

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
| + MD14 cost pass-through, yearly wage catch-up, no consumption floor | 1.26 | **1.52** | 2.26 | **1.13** | 1.20 | −0.13% | 11.2% |
| + income-weighted average saving rate (S26) | **1.18** | **1.38** | 2.20 | 1.14 | **1.09** | −0.07% | 10.7% |
| R4: same model, scored against chain-linked volumes | 1.50 | 2.32 | 6.70 | 1.11 | 1.09 | −0.07% | 10.7% |
| + MD15 growth engine, forecasts without a random draw | **0.99** | **1.08** | **1.90** | **1.09** | **0.86** | +0.19% | 10.0% |
| + MD16 government spending planned on growth rates of CPI-deflated spending | **0.94** | **1.04** | **1.42** | 1.13 | 0.86 | +0.28% | 9.4% |
| + M16 housing matching respects willingness to pay (bug fix) | 0.97 | **0.95** | 1.53 | 1.20 | 0.86 | +0.31% | 9.0% |
| R7: same model, inflation and unemployment against seasonally adjusted quarterly data (q12: 9.7%) | 0.97 | 0.95 | 1.53 | 1.20 | **0.74** | +0.31% | 9.0% |
| + MD17 cash benefits, MD18 Taylor rule, MD19 the paper's target-production caps | 1.03 | 1.04 | 1.69 | **1.08** | **0.74** | +0.21% | 10.0% |
| + P8 house price forecasts no longer pinned at the 22%/q cap (bug fix) | 1.03 | 1.05 | **1.66** | 1.11 | 0.74 | +0.21% | 10.0% |
| + S32 investment split by capital compensation (bug fix) | 1.01 | 1.05 | 1.87 | **1.03** | 0.74 | +0.21% | 10.0% |
| + MD20 national-accounts return, MD21 paper's housing rules, MD22 paper's firm-loan limits | **0.97** | **1.00** | 1.79 | 1.05 | 0.75 | +0.29% | 9.6% |

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

### Current state of `main` (MD22, R7 targets)

Default settings, 10 seeds, 12 quarters, France 2014, real aggregates against chain-linked volumes, inflation and
unemployment against seasonally adjusted quarterly data:
- **Scorecard** (`sim / AR(1)`): GDP **0.97**, HH cons. **1.00**, gov. cons. 1.79, investment 1.05, CPI **0.75**
  (`sim / VAR`: 0.93, 0.99, 1.50, 1.04, 0.99). The paper reports 0.40–0.75. Nothing is calibrated yet, the firm and
  household data are spoofed (D1), and tax rates are statutory (F7).
- **Sanity gate passed**: growth +0.29%/q (data +0.28%); unemployment 9.6% after 12 quarters and 8.5% after 20
  (data 9.7%, 8.8%).
- **Inflation is three times the data**: 0.22%/q against 0.07%/q (adjusted deflator, 2014–16), so the VAR (the
  sample mean) scores as well as the model on CPI. The policy rate is at zero from quarter 4 (MD18), as the ECB's
  was, so monetary policy cannot respond.
- **Government consumption** (1.79) is the worst ratio: the plan is smooth, but realised spending is the
  plan at expected industry prices, scored as nominal over the CPI. Its error is quarter-to-quarter noise, not the
  deflator (at the government's own prices the RMSE is the same): the government gets 99.4–100% of its plan as goods
  are rationed, and small changes in other demand move the ratio by up to 0.5 (exp040).
- **Housing**: about 0.3% of homes sold and 1.0% newly rented a quarter (MD21); house prices never move (M18).
- **Accounts**: every loan and deposit ledger agrees exactly; unexplained money at most 0.3% of GDP; the
  by-design unbacked flows (S9, S10, S13) are at most 4.6% of GDP (16% before MD20). No industry starts
  loss-making and no firm defaults (S32 fixed).
- Runs are almost the same across seeds (the remaining randomness is price noise and labour-market flows):
  about 1 s per 12 quarters with 18 firms, about 10 s with 408, mostly in the housing market (E12).

### Audit of the default model (I1, 2026-10-22)

A walk through one quarter against the paper (model map above) and against France's 2014 national and government
accounts, at t = 1 (one seed; % of GDP; France: Eurostat `gov_10a_main`, `namq_10_gdp`):

| | Model | France 2014 | Register |
| --- | --- | --- | --- |
| Government revenue | 41.5 | 53.8 | F7 |
| Social benefits (cash) | 31.0 | 19.8 | F6 |
| Government consumption | 27.6 | 24.4 | F6 |
| Government deficit | 18.4 | 4.6 | F6, F7 |
| Household income (disposable) | 79.7 | ≈ 67 | S31 |
| Household consumption | 41.8 (46.5 incl. VAT) | ≈ 53 | S31 |
| Household saving rate | ≈ 40% of income | ≈ 15% | S31 |
| Capital stock / annual GDP | 2.2 | ≈ 2–3 (business capital) | — |
| Depreciation | 1.4% of capital a quarter | ≈ 1.5% | — |

- **Bugs:** the capital stock's value used the intermediate-input stock's function (S30, fixed): firm collateral
  was a ninth of its true value, so exp019's conclusion on financing limits is suspect.
- **Accounts that matter for dynamics:** benefits counted twice (F6; fixed by MD17: benefits 18.8%, deficit 6.2%,
  household income 67.5% of GDP),
  revenue rates far from effective rates (F7), unpaid financial income (S9), and so a household sector that saves
  40% of an inflated income (S31). Four industries start loss-making on the sample data and one firm defaults every
  8 quarters (S32).
- **Departures from the paper that are upstream defaults:** one saving rate and equal transfers for all households
  (M13), constant rents (M14), rest-of-the-world trade from noisy AR(1) forecasts (M15), a constant policy rate
  (P4; the paper's rule since MD18), optimal-assignment housing market (E12). The paper's expectations are deterministic: dropping the noise
  (MD15) follows the paper (P3).
- **Scoring data:** CPI is not seasonally adjusted and unemployment is annual (R7; adjusted quarterly targets since
  2026-10-22).

### How the default model came to be (exp003–exp021)

One paragraph per mechanism; each experiment's numbers are in the Experiments table and in
`outputs/expNNN_*/summary.csv`. Ratios before R4 were scored against PPI-deflated data.
- **Growth needs room and a reason (exp003–exp004; G1–G3).** At the old defaults every firm produced at
  capital capacity (ω = 1) and bought only depreciation, so the economy could not grow and growth
  expectations changed nothing. Spare capacity (ω = 0.85, the paper's value) unlocked growth; the paper's
  full stock top-up (φ^K = φ^M = 1) acted as an accelerator and exploded.
- **Profits and incomes (exp005; MD9, MD6).** Initial wages were value added minus investment, so firms had
  no profit; SEA labour shares give profits of about 24% and wages of about 46% of GDP. Paying dividends
  (MD6) makes financial income realistic but needs firms to invest retained profits (still an option).
- **Investment (exp006–exp008, exp018–exp020; MD10, G10).** A flexible accelerator closing λ of the gap to
  desired capital cycles or explodes for λ ≥ 0.25; desired capital sized on smoothed demand steadies it.
  Wages had been frozen in nominal terms (S27). With 408 firms the investment forecast barely changes, so
  its errors were not lumpiness: the random draw in firms' forecasts, amplified by the accelerator, swung
  quarter-1 investment from −14% to +15% across seeds (exp020). Deterministic forecasts and λ 0.10 fix it.
- **Labour market (exp009–exp011; MD11, MD12, G13, G14).** Without frictions a boom hires the whole
  unemployed pool; with separations and a matching function unemployment still fell to 2%, because output
  per worker did not grow. Labour-augmenting progress (1% a year) removes that, but the engine then grew
  faster instead, because expected growth fed on realised growth (G16).
- **Expectations (exp014, exp020; MD13, MD15, P3).** Lowering expected growth when unemployment is below its
  initial level (Okun's law) anchors the engine; a forecast from pre-2014 data alone does not. The paper's
  expectations are deterministic; dropping the forecast draw removes the main source of model noise.
- **Prices and wages (exp012–exp013; MD14, P6, G17).** Cost-push pricing compared unit costs with the price
  level and cut prices 10% a quarter (P6, now unit-cost growth). Tightness brakes do nothing: nothing
  transmits prices or interest rates to spending, and the boom is not inflationary. Cost pass-through with a
  yearly wage catch-up improves the CPI fit (1.84 → 0.98 on the defaults of the time).
- **Consumption floor (exp016; S26, MD14).** The floor counted every adult as receiving unemployment benefit
  and lifted consumption 7% in quarter 1; dropping it halves the household-consumption error.
- **Assembling the engine (exp015, exp017).** Spare capacity is necessary; the slack-aware forecast is the
  key part; the work-effort cap changes nothing. The engine first passed the sanity gate in exp017
  (unemployment 9.9% / 8.5% at q12 / q20, data 9.4% / 8.4%).
- **Scoring target (R4).** Nominal GDP over PPI grew 0.64%/q in 2014–16 against 0.28%/q in chain-linked
  volumes, with three times the quarterly noise and no correlation (0.05). Against volumes the AR(1)
  benchmark is harder, and the model's own noise dominated its errors until MD15.
- **Government plan (exp021; MD16, F5).** An AR(1) on log levels mean-reverts, so planned spending growth
  faded to 0.10%/q (data 0.34%); growth rates of CPI-deflated spending give 1.42 (offline 1.03; the rest is
  measurement: purchases at expected industry prices, scored over the CPI).

### Next step

The intermezzo (phase 2½) is done, and the decisions it raised are adopted (MD17–MD19, R7 targets), as are the
candidates of 2026-10-22 (S32 fix, MD20–MD22; exp040). Every MD15–MD22 value was chosen in-sample. In order:
1. **Data (D1), on the critical path**: the public data is in (interim, see Data); the licensed HFCS and Compustat
   are not (Pietro: ask INET for `inet-macro-data`, then WRDS and the ECB). Everything that becomes a paper claim
   waits on it: calibration on 2010–2013 (phase 5), held-out start dates, the 38-country ladder (E_ATTR), the
   recovery period (E24).
2. **Household side** (S9, S31, F2): the remaining 4% of GDP of unpaid financial income needs a payer (MD6 with the
   matched payout, exp039, once the first dividend's timing is fixed), and the income should be received net of
   tax, which needs the initial income and saving rate built net too. Households now net-borrow about 2.5% of GDP
   (France: lend ≈ 3%); recheck after these and F7.
3. **Effective tax rates** (F7, phase 4): revenue 41.5% of GDP against 53.8%. The profit tax is built as an
   option (exp032; alone it widens the deficit). Left: income tax, social contributions and production taxes,
   calibrated together, since they set the gross–net wage split in the initial state.
4. **Phase 4 markets**: the buy-or-rent comparison (M2: a user cost of owning), house prices that never move (M18),
   consumer credit (M3: the rule's base, then the paper's ρ = 0.36), firm credit (M17's time unit, F2, G9), E15
   (three configured functions are never called).
5. **Inflation level** (P2, phase 3): diagnosed (exp030). Realised inflation converges to the AR(1) expectation on
   pre-2014 PPI, the only nominal anchor. Nothing to add on France 2014 alone; recheck on other start dates (D1).
6. **Government consumption** is the worst ratio (1.79) and fragile: the government gets 99.4–100% of its plan as
   goods are rationed, and small changes in demand move the ratio by up to 0.5 (exp040). A rationing rule that
   serves the government's plan first, as budgets are, is a candidate decision.
7. **For the paper**: E1's text ("no exogenous TFP") is contradicted by MD12; the revision plan's χ^K ≈ 0.56
   against `table:prior`'s 0.18 (E2); the data section's sources change (MD17, MD20); the housing budgets differ
   from the paper's rules (MD21). Typos in the appendix (M2, exp034): the buy-or-rent probability falls when renting
   is dearer (sign); the mortgage annuity has exponent +m_l and adds the principal twice; the price and rent cuts
   1 − exp ε need ε in percent (/100); ρ^RoA and ρ^RoE have no time unit (M17).
8. **Upstream** (E9, ask Pietro first: public): P7, P8, S3, G5 and S32 are upstream bugs with tests here.

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
| R4 | Scoring differs from the paper: GDP deflated by PPI (macro_data's "Real GDP" too, +2.6%/yr vs ~1% official), one country, one start date | Spec | ours | exp001; `exogenous_data.py:375` divides nominal growth by PPI inflation | fixed for scoring: real aggregates scored against Eurostat chain-linked volumes (`scoring.observed`, `volumes=False` for the old target); firms' growth expectations still use the PPI-deflated history; one country, one start date remain | P3 |
| R5 | `macrocalib` is untested and excluded from the test suite | Infra | ours | pytest `addopts` | open | P3 |
| R6 | Differentiable version of the model | Gap | CB7 | Matias investigating | not ours now | P3 |
| R7 | Scoring targets: CPI is not seasonally adjusted (quarterly inflation swings −0.5% to +0.9%), and the unemployment series is annual (flat within each year) | Data | ours | I4 forecast fans | fixed: `scoring.observed(adjusted=True)`, the default since 2026-10-22, takes CPI inflation from the seasonally adjusted household consumption deflator (`namq_10_gdp` PD10_EUR SCA) and quarterly unemployment (`une_rt_q`, SA); `adjusted=False` keeps the old targets. Rescoring the M16 baseline: CPI data s.d. 0.47% → 0.22%/q, CPI ratio 0.86 → 0.74, unemployment at q12 9.4% → 9.7%; other ratios unchanged. Experiments before 2026-10-22 used the old targets | — |

### G. Growth and firm behaviour

| ID | Problem | Kind | Source | Evidence | Status | Pri |
| --- | --- | --- | --- | --- | --- | --- |
| G1 | No growth: firms start at full capacity and capital purchases only replace depreciation, capped at current capacity | Spec | ours | exp003, exp004, exp006 | fixed: spare capacity and the partial-adjustment investment rule are the default (MD15) | — |
| G2 | The paper's stock top-up (φ^K = φ^M = 1) explodes like an accelerator | Spec | ours | exp004 | superseded by the partial-adjustment rule (G1), which still cycles without stabilisers | — |
| G3 | Growth expectations off by default | Spec | ours | exp002, exp003, exp006 | fixed: on by default (MD15) | — |
| G4 | χ caps input purchases and hiring, not target production as in the paper | Spec | ours | exp002; Sam's `target_production_considers_*` | fixed: `PaperTargetProductionSetter` at the paper's posterior is the default (MD19, 2026-10-22); exp026: unemployment 9.7% / 8.6% (data 9.4% / 8.4%). The code's caps on purchases stay on top (E2) | — |
| G5 | One firm per industry by default, and `default_data_configuration` ignores its `single_firm_per_industry` argument | Bug | ours | `configuration_utils.py:74` | fixed: `default_data_configuration` applies it to each country (it went to `DataConfiguration`, which has no such field, and pydantic dropped it), with test | P2 |
| G6 | Spare capacity overshoots: unemployment falls to 5.8% (data 9.4%) | Question | ours | exp004 step 2; exp020: with the default engine (MD15) unemployment is 10.0% / 9.4% after 12 / 20 quarters (data 9.4%, 8.4%) | fixed by MD11–MD13, MD15 | — |
| G7 | Many-firm runs crashed (per-firm prices used as per-industry) | Bug | ours | — | done `31f797a` | — |
| G8 | Wages did not respond to labour-market tightness (existing employees' markup scale 0) | Spec | ours | exp007: a tightness markup raises wages, but with prices not passing costs through it adds demand instead of braking | partial: needs cost pass-through in prices (P5) | P1 |
| G9 | Capital purchases are not limited by financing (`credit_gap_fraction = 0`) | Spec | ours | exp008; exp019: even with the paper's bank limits, firms receive no long-term credit: only 2 of 18 firms want it, both with debt above the value of their capital (the bank rule is a loan-to-collateral limit) and one loss-making; cutting their investment by the unmet credit causes a recession | blocked on data: exp028 (after S30): healthy firms ask for no credit (F2) and only the sample data's loss-making firms (S32, now fixed) did, failing the return-on-assets test; see M17 on that test's units. The paper's firm-loan limits are the default since MD22 (no effect on the sample data) | P2 |
| G10 | Desired capital followed current planned output, booms included: multiplier–accelerator cycles | Spec | ours | exp008: sizing desired capital on smoothed planned output (`demand_smoothing` 0.10) gives steady growth of 0.7%/q (data 0.6%) with no bust | fix built (option) | — |
| G11 | Spare capacity alone sends unemployment from 10% to 4% within five years | Question | ours | exp006 step 2 (see G6) | fixed with G6 | — |
| G12 | Work effort can raise output per worker by up to 50% (`max_increase_in_work_effort = 1.5`) | Spec | ours | exp009; exp015: a cap of 1.1 changes nothing in the candidate model | low priority: effort is not what drives employment | P3 |
| G13 | The labour market has no frictions: firms fill every vacancy within the quarter (`hiring_speed = 1`), nobody separates (`random_firing_probability = 0`), no quits; so a boom hires the whole unemployed pool and unemployment goes to 0% | Spec | ours | exp009: employment +11.5% in two years, unemployment 10.3% → 0% | fixed: `SearchFrictionsLabourMarketClearer` is the default (MD15), μ calibrated to the initial unemployment rate | — |
| G14 | Labour productivity does not grow (`NoOpTFPGrowth`), so every percent of output growth needs a percent more workers from a fixed labour force | Spec | ours | exp010; exp011: labour-augmenting progress cuts labour demand on capacity-capped defaults (unemployment 10.3% → 14.4% at 0.25%/q), but under the engine output grows faster instead (G16) | fixed: `LabourAugmentingGrowth` is the default (MD15) | — |
| G15 | The TFP module (`SimpleTFPGrowth`) counts all net capital investment as productivity investment, so with the investment engine TFP grows about 3%/q (multiplier 1.88 after 20 quarters at a 0.25%/q base); TFP also scales intermediate and capital capacity, not labour demand | Spec | ours | G14 probes | open: not used | P2 |
| G16 | Demand growth is not anchored: firms scale demand by forecast growth, an AR(1) over the data history and the model's own realised growth, so extra supply (spare capacity, productivity) becomes faster growth | Spec | ours | exp011; exp014: a slack-aware forecast (MD13) holds unemployment at 5.5–6.9% after five years (2.4% without); a data-only forecast 3.6% | fixed: `SlackAwareGrowthForecastingAutoReg` is the default (MD15) | — |
| G17 | Nothing transmits higher prices or interest rates to spending: wages were paid at the latest CPI (real wages fixed), households spend a fixed share of nominal income, investment ignores interest rates and financing | Spec | ours | exp012, exp013 | partial: wages catch up gradually by default (MD14); consumption and investment channels open | P1 |
| G18 | The initial state is not a fixed point: with no productivity growth and a constant zero growth forecast the economy still grows 0.2–0.3%/q and unemployment falls from 10.3% to 5.8% in five years. Demand grows on its own; candidates: the government plan (AR(1) on past growth, about 0.4%/q), households' unpaid financial income growing with their savings (S9, S31), firms' hoarded profits (F2) | Question | ours | exp022 "no growth" step | partial: in the no-growth run (expected growth exactly 0) government consumption grows 0.39%/q (its plan extends the trend of its own data history: an exogenous demand source by design), household consumption 0.26%/q and investment 0.76%/q (following demand). With the government planning zero growth as well, GDP grows 0.08%/q (near a fixed point) and unemployment ends at 8.6%: the government's planned trend explains most of it; household consumption still drifts up 0.2%/q: in that run wages and transfers are flat, but households' other financial assets grow 12% in five years (savings) and their unpaid income with them (103 → 115 bn a quarter, S9), and consumption follows. The fix is the S9 decision: a payer for financial income (MD6 introduced gradually) or a return that does not compound on unbacked savings. exp031: with the government at zero planned growth too, GDP growth is −0.03%/q (a fixed point up to noise), and with the national-accounts return (S9 option) household consumption drifts 0.04%/q instead of 0.11%/q | P2 |

### P. Prices, expectations and monetary policy

| ID | Problem | Kind | Source | Evidence | Status | Pri |
| --- | --- | --- | --- | --- | --- | --- |
| P1 | 5% per-firm price noise dominated the dynamics | Spec | ours | exp002 | done `60948b7` (0.0005) | — |
| P2 | Realised inflation equals the AR(1) forecast (self-fulfilling; referee R2.4) | Question | ours | exp003; E_AR1 wedge: realised CPI inflation now diverges from expected (correlation −0.96) | partial: cost pass-through (MD14) lets costs reach prices; a wage Phillips curve is built as an option (exp029) and adds little at today's small unemployment gap. exp030: realised inflation converges to the AR(1) expectation, the only nominal anchor (import prices follow domestic prices); prices from costs alone have none (inflation 0) | P2 |
| P3 | Forecast noise draw roughly doubles the inflation error: keep or drop? The paper's expectations are a deterministic AR(1) (`sec:expectations`), so dropping it matches the paper | Question | ours | exp003: CPI ratio 1.8 → 0.95 without it; exp020: it drives the growth engine's investment volatility (quarter-1 investment −14% to +15% across seeds) and the government's spending path | decided: dropped by default (MD15); `assume_zero_noise=False` restores it | — |
| P4 | Taylor rule inert (zero by quarter 3), constant rate by default, and a TODO says `xi_pi` is estimated wrongly | Bug | ours | exp001; `default_synthetic_central_bank.py:187` | fixed: default since MD18. Not a bug: the rule gets quarterly PPI inflation and gross-output growth, the series it is estimated on, and ξ_π = β/(1 − ρ) matches the rule's (1 − ρ) ξ_π form, so the TODO is stale. On France (ρ 0.93, ξ_π 1.51, ξ_γ 4.05) the rate falls from 0.33% to zero within four quarters, as the ECB's did in 2014. The zero lower bound then binds: the rule cannot respond to the economy until inflation rises | — |
| P5 | Firms did not pass cost increases into prices (cost-push weight 0) | Spec | ours | exp007; exp012, exp013, exp015 | done: half pass-through by default (MD14) | — |
| P6 | Cost-push inflation compared unit costs with the sector's price level, so it pulled prices down to costs (−10%/q) instead of passing on cost changes | Bug | ours | unit cost / price 0.895 at t=1; Sam's prior notes "prices cause shit to break" | done: uses unit-cost growth, with test | — |
| P7 | `InflationForecasting.forecast_inflation` applied its upper bound with `np.maximum`, raising every forecast to the cap | Bug | upstream | code reading, 2026-10-22 | fixed, with test; latent: no caller passes bounds (`Economy` clips the forecast itself), so no run changes | — |
| P8 | `HPIForecasting.forecast_hpi_growth` applied its upper bound with `np.maximum` (as P7), and the economy passes `max_hpi_growth = 0.2`: every house price forecast was log growth 0.2, i.e. 22.1% a quarter. In the buy-or-rent comparison buying then looked like a 122% yearly return, so every household deciding chose to buy (M2); asking prices do not use the forecast (M18) | Bug | upstream | M2 probe, 2026-10-22: expected HPI growth 0.2214 at every t | fixed, with test: −0.38% at t = 1, then about +0.07%. Baseline: HH 1.04 → 1.05, gov. 1.66, invest. 1.11; still no rentals (M2) | — |

### S. Initial state and stock-flow consistency

| ID | Problem | Kind | Source | Evidence | Status | Pri |
| --- | --- | --- | --- | --- | --- | --- |
| S1 | Stock-flow consistency: `macromodel/accounting.py` checks every quarter that the loan and deposit ledgers agree, bank equity and government debt move only by their flows, and money changes only by the deficit plus net exports; it separates the by-design unbacked flows from leaks | Gap | both | exp001 `accounts.csv`: all ledgers exact; money residual ≈ unbacked flows (up to 11% of GDP); unexplained ≤ 4% of GDP, early quarters only (S23) | partial: done once S9, S10, S13, S23 are closed | P1 |
| S2 | Firms made about zero profit: initial wages were value added minus investment (labour share 85%; SEA and France ≈ 59%) | Bug | ours | exp005 | done: `labour_share_from_sea` is the default (MD9); firm profits ≈ 24% of GDP | — |
| S3 | The re-initialisation path double-counts bank deposits (liabilities 1.65e16) | Bug | ours | exp004; MD15: `n_industries_default` hard-coded utilisation 1.0, so default runs took this path until fixed | fixed 2026-10-22: the household wealth steps scaled survey columns in place, so re-running them multiplied deposits, mortgages and consumption loans by the scale again (×10,000) and re-derived the financial-income return from model income; now each column is scaled once (`_scale_once`). After a reset, banks, firms, households and the government match a fresh build with the same settings, except the housing match, which is re-drawn. Regression test in `test_data_wrapper.py` | — |
| S4 | Bank deposits are negative on the normal path (−1.17e12) | Question | ours | probe | open | P2 |
| S5 | Initial Demand = Production + Inventory | Question | ours | `firm_tools.py:487` | open | P3 |
| S6 | GDP is forced to balance by adjusting imports/exports, which can hide inconsistencies | Spec | ours | `gdp.trade_adjustment` check: the adjustment is 0 in single-country runs | not active for one country; check in multi-country runs | P3 |
| S7 | Simulations modified their input data | Bug | ours | — | done `62d29d3` | — |
| S8 | Initial inventory read from the wrong parameter | Bug | ours | — | done `62d29d3` | — |
| S9 | Households receive income on "other financial assets" (about 19% of quarterly GDP) that nobody pays | Spec | ours | `money.unbacked_flows`; I1: the return is calibrated from HFCS as income from financial assets over their stock (`set_household_income_from_financial_assets`): 1.9% a quarter, 7.7% a year on the spoofed survey, against about 2.4% a year for French households' property income; the stock (about 2.5 × annual GDP) is plausible | partial: the return is the national accounts' since MD20 (`financial_income_from_national_accounts`, default 2026-10-23; exp031, exp040): the unpaid flow fell from 21% to 4% of GDP. Left: (a) a payer for the remaining 4%: shares in firms paying dividends (MD6, `FirmSharesFinancialAssets`, option; exp039: the payout matched to this income works, but household consumption dips at q2 when dividends take over); (b) households receive this income gross while the government books income tax on it (`accounting.py` counts that tax as unbacked); rents and dividends are paid net. Paying it net (probe, 2026-10-22, before MD20): GDP 1.03 → 1.02, HH 1.05 → 1.07, gov. 1.66 → 1.83, invest. 1.11 → 1.06. Paying net needs the initial income (and so the saving rate, S26) built net too, or consumption jumps at q2 (the exp039 dip): one change to the data and the simulation together | P1 |
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
| S26 | Household consumption jumped about 7% in the first quarter | Spec | ours | the consumption floor (1 − saving rate) × benefits counted every adult as receiving unemployment benefit, exceeded the income of 39.5% of households, and was not in the initial state; without it consumption fell 1.5% instead, because every household was given the simple mean of the data's saving rates (0.432) where the income-weighted mean (0.421) reproduces initial consumption | done: floor off (MD14); income-weighted average saving rate, with test | — |
| S27 | Regression from S12: firms' wage bill lost its CPI factor, so nominal wages were frozen and real wages fell with prices | Bug | ours | the wage setter pays real wages; the CPI factor belonged on the employees' side | done: employees receive real wage × CPI, firms pay the gross-up of that | — |
| S28 | Firm-loan ledger residual (3.5% of GDP, seed 7, one quarter): a firm's written-off loans stayed in its own debt records until the next quarter (households' were fixed in S20) | Bug | ours | seed 7, t = 7 | done: insolvency clears the firm's debt records, with test | — |
| S29 | Unexplained money grew with the policy rate: 15.6% of GDP with the Taylor rule on the engine (exp012, old defaults) | Question | ours | the interest the central bank pays on positive bank reserves (money it creates) was missing from the money identity; with it, the engine + Taylor run's worst unexplained money is 2.8% and the default run's halves (1.3% → 0.7% at q11); the rest grows with reserves, probably deposit interest booked differently by banks and depositors; bank reserves reach 3–5× quarterly GDP in engine runs | partial: identity fixed, with test; rest open | P2 |
| S30 | The capital stock's value was recorded with the intermediate-input stock's function each quarter (about a ninth of the true value); banks use it as collateral for firm loans | Bug | upstream | I1 (mechanism dashboard); `country.py` | fixed `1af901a`, regression test; exp019's "debt above capital value" is suspect; report upstream (E9) | — |
| S31 | Household income is 80% of GDP at t = 1 (net wages 30%, social transfers 29%, income on other financial assets 19%, rents 1%; France: disposable income ≈ 67%, cash benefits ≈ 19%) and households consume 42% of GDP, a saving rate of about 40% (France ≈ 15%): two inflated income sources (F6, S9) offset by a high saving rate. Savings accumulate as other financial assets, whose unpaid income (S9) then grows | Spec | ours | I1: household income statement at t = 1 | partial: F6 fixed (MD17), income 67.5% of GDP; MD20 (the national accounts' financial return) takes household income from 74.6% to 57.8% of GDP (exp031's measure), with initial consumption unchanged. exp040 dashboard: households now net-borrow about 2.5% of GDP each quarter (France 2014: net lending ≈ +3%); the gross–net split of taxes (F7, S9 b) is the next suspect | P1 |
| S32 | Four industries start loss-making under MD9 (profit / sales: I −28.5%, E −17.6%, B −13.9%, D −0.4%); firm I (accommodation and food) loses 7 bn a quarter, runs out of deposits and defaults every 8 quarters (t = 9, 17), its bank absorbing the loss; firm E follows later. (The earlier note that the sample SEA covers only 3 of France's 56 codes was wrong: 55 of 56 have COMP and VA in 2014) | Data | ours | I1: firm accounts over 20 quarters | fixed 2026-10-23: a bug in the investment split, not the data (exp033). Capital compensation was divided by the investment in each industry's product instead of its total, which loaded I, E, B, D with capital costs up to the 93% cap. `investment_shares_from_capital_compensation` (default; False restores the old split, `settings.OLD_INVESTMENT_SPLIT`): no industry loss-making, periodic defaults gone; test in `test_data_wrapper.py`. Baseline: GDP 1.03 → 1.01, invest. 1.11 → 1.03, gov. 1.66 → 1.87 | — |

### M. Markets and trade

| ID | Problem | Kind | Source | Evidence | Status | Pri |
| --- | --- | --- | --- | --- | --- | --- |
| M1 | Housing market initialises and executes poorly (tenure mix, stock quality) | Spec | both | CB7; upstream #93 | partial: #93 merged | P2 |
| M2 | Rental market nearly dead (0–1 rentals/q vs 400–500 sales); some rent/value above 1 | Question | ours | rent probe; possibly spoofed data; I1 cause: the buy-or-rent logit is saturated. Its argument is temperature × (annual cost of renting − annual cost of buying) / 10,000 in model money units (each agent stands for `scale` households), with temperature 1: at t = 1 it ranges from 18,500 to 637,000 for the 1,362 deciding households, so every one of them buys (P(buy) = 1) and no household asks to rent while 844 homes are offered. The cost of buying also leaves out mortgage interest (the paper's formula has it) and subtracts expected appreciation on the whole value | open: diagnosed. Part was P8 (expected house price growth pinned at 22%/q, fixed). After it, per real household the median decider compares renting at €6,137 a year with buying at about €1,000: buying counts only the loan's principal (43% need no loan) and no interest or forgone return on own wealth, so even the paper's φ^B = 0.001 per euro gives P(buy) ≈ 0.99, and no house is newly rented in 12 quarters. The code's sensitivity is 1 per euro (`/ 10000` assumes scale 10,000), 1,000 times the paper's; its μ^PS is 0.1 (paper 0.4). The paper's formula has a sign slip (p^B falls when renting is dearer) and an annuity typo (exponent +m_l; the annuity already includes principal). Fix in phase 4: a user cost of owning (interest or forgone return on the whole value, minus expected appreciation), φ^B per real household. Partial since MD21 (2026-10-23): renters can pay up to 25% of income (was a constant 0.2 money units), so homes are rented: new rentals 1.0% of the stock a quarter (exp040). The logit itself is unchanged | P2 |
| M3 | Consumer credit decays towards 0 even after #104 | Question | ours | probes; I1: the stock falls from 322 to 196 bn in quarter 1 (repayment over 12 quarters plus quarter-1 write-offs, MD8) and to 1 bn by q12, while households ask for 60–120 bn a quarter and receive under 0.5 bn: the cap is 0.5 × average *quarterly* income minus *total* debt, mortgages included (`credit_market/func/clearing.py`), so any household with a mortgage, or with debt above half a quarter's income, gets nothing. Mortgages are rationed too (270 bn asked, 55 bn granted in quarter 1) | open: diagnosed; the code follows the paper's LTI-C rule (the average of the last two quarterly incomes, minus household debt), so the restriction is the paper's: with ρ = 0.5 (paper 0.36) a household may borrow at most half a quarter's income net of all its debt. A ratio on annual income, or on consumer debt only, is a modelling decision; phase 4. exp040: the paper's ρ = 0.36 moves gov. cons. 1.79 → 2.34 although consumer credit is almost nothing: settle the rule's base before its value | P2 |
| M4 | Government consumption still about 2× the AR(1) error | Question | ours | baseline | fixed by MD16 (1.90 → 1.42; F5) | — |
| M5 | Imports, exports and exchange rates need review | Spec | CB7 | see S6 | open | P3 |
| M6 | Housing IDs set to −1 at initialisation | Bug | upstream | — | done: #93 merged `80d8b3d` | — |
| M7 | Credit-supply units bug | Bug | upstream | — | done: #104 merged `a6dca3c` | — |
| M8 | Rent-value regression swapped and fitted through one point | Bug | ours | — | done `21f1f2b`; report upstream (E9) | — |
| M9 | Houses change hands far too often: about 12% of the stock per quarter (real: about 1%), 800–1,400 bn of sales per quarter | Spec | ours | Phase 1 decomposition; M16 | fixed by MD21 (2026-10-23): the paper's moving probabilities (owners 79/80, renters 7/8; were 0.5). Sales 2.5% → 0.27% of the stock a quarter with the MD21 budgets (exp040); France roughly 0.75%. Now on the low side: check once M2's cost of buying is fixed | P3 |
| M10 | Interest on existing loans was an annual rate charged every quarter (4×) | Bug | upstream | now: firm loans 1.0%/yr, consumer loans 4.8%/yr, mortgages 2.3%/yr | done: upstream #83 and #85 merged (`40c8a1e`, `f12f78b`) | — |
| M11 | Poledna layoffs reported the sum of every firm's excess employees, negative ones included, as the number fired (−hires under search frictions); only the reported flows (`num_individuals_newly_fired`, `job_reallocation_rate`) were wrong | Bug | ours | exp010 | done: counts the workers actually fired, with test | — |
| M12 | Layoffs only reset a worker's firm ID, so firms' employee lists kept laid-off workers (and listed rehired workers twice); the lists guard random separations | Bug | ours | engine + frictions, 16 quarters: 95 stale entries, 60 duplicates | done: lists rebuilt after every clearing, with test; defaults unaffected (no random separations) | — |
| M13 | Households all save at one average rate and receive equal social transfers; the paper sets both per household from HFCS characteristics | Spec | upstream | model map; `AverageSavingRatesSetter`, `EqualSocialTransfersSetter` | open: alternatives exist; matter for distribution, less for aggregates | P2 |
| M14 | Rents never change (`ConstantRentSetter`); the paper indexes them partially to CPI and cuts vacant offers | Spec | upstream | model map | open. The rent function in the config (`households.functions.rent`, `ConstantRentSetter`) is never called: rents are indexed by the property function's `partial_rent_inflation_indexation` (default 0). exp034: indexing to the CPI changes little | P3 |
| M15 | The rest of the world sets exports and imports from AR(1) forecasts that still draw noise (`row_configuration.assume_zero_noise=False`); the paper indexes them to modelled production and prices | Spec | upstream | model map; I1 | partial: exp022: the rest of the world's forecast noise changes nothing; trade indexation still differs from the paper | P3 |
| M16 | The automatic housing clearer matched households with homes priced above their willingness to pay: its cost was \|willingness − price\|, never negative, so the `cost < 0` guard never fired, and the optimal assignment paired every household with demand to some home | Bug | upstream | I1 (profiling the housing market); regression test | fixed `e82f780`: sales fall from about 12% to 3–6% of the stock a quarter; baseline GDP 0.94 → 0.97, HH cons. 1.04 → 0.95, gov. cons. 1.42 → 1.53, invest. 1.13 → 1.20; report upstream (E9) | — |
| M17 | The firm return-on-assets test compares expected *quarterly* profit over debt plus equity with `firm_loans_return_on_assets_ratio` 0.05: the median firm earns 1.6% a quarter (about 6.4% a year) and fails; if the 5% is annual (as interest rates were, M10), the test is four times too strict | Question | upstream | exp028 diagnostics | checked 2026-10-22: the code is the paper's rule (`appendix_model_description.tex` l. 415–421: expected profit Π̄_f(t) over L_f(t−1) + E_f(t−1) ≥ ρ^RoA = 0.05, no time unit, so quarterly in a quarterly model). ρ^RoA = 0.05 and ρ^RoE = 0.15 read like annual ratios, so the paper's calibration is likely four times too strict. A modelling decision (annualise the profit in both tests) and a sentence for the paper; matters only once firms ask for credit (G9, F2) | P2 |
| M18 | Property values never change, so the house price index is constant and realised HPI growth is 0 every quarter; the HPI forecast then decays towards 0. Cause: a sale revalues the property at its price, but the asking price is (1 + `price_initial_markup`) × value with the markup 0, and price cuts are off, so every sale is at value; the paper's asking price is (1 + predicted HPI inflation) × value. `DefaultPropertyValueSetter` adds noise with std 0 | Spec | ours | housing probe after P8 | open: the paper's markup (predicted HPI inflation) needs the forecast passed to `compute_initial_sale_price`, as a new rule class; with the forecast near 0 after P8 the index would barely move, and it would be self-fulfilling (as P2). Phase 4 | P2 |

### F. Government and finance

| ID | Problem | Kind | Source | Evidence | Status | Pri |
| --- | --- | --- | --- | --- | --- | --- |
| F1 | Taxes and benefits need review | Spec | both | upstream `bug/government-expenditure` (benefits, deficit fixes; no PR) | open | P2 |
| F2 | Corporate equity not wired between firms and households (profits not redistributed) | Gap | CB7 | Andrea's module; relates to S2; I1 dashboard: firms net-lend about 9.5% of GDP every quarter (profits ≈ 17% of GDP, no dividends; French firms are roughly balanced or net borrowers), and switching on MD6 at once removes 19% of GDP of household income (S9) and collapses demand (exp024) | open exp038: after S9, MD6 cuts firms' net lending to 4% of GDP without collapsing demand, but pays out more than the income it replaces (demand rises; unemployment 7.7% at q20); calibrate the payout first. exp039: with the payout matched to households' property income (option `payout_from_national_accounts`) MD6 pays exactly the S9 income and firms' net lending falls to 5.9% of GDP; HH ratio 1.30, mostly a q2 dip when dividends take over (check the first dividend's timing). | P2 |
| F3 | Government debt, bond issuance, QE | Gap | CB7 | Tom's UK prototype | open | P3 |
| F4 | Fiscal rules | Gap | CB7 | — | open | P3 |
| F5 | The government's spending plan is an AR(1) on log levels of PPI-deflated spending, so planned growth fades (0.10%/q against 0.34%/q) | Spec | ours | exp021: growth rates / CPI takes gov. cons. 1.90 → 1.42 | fixed: `AutoregressiveGrowthGovernmentConsumptionSetter`, `deflator="cpi"`, default (MD16) | — |
| F6 | "Other social benefits" are OECD SOCX total public social expenditure less unemployment benefits, which includes in-kind services (health, care) already in government consumption. At t = 1: benefits 31.0% of GDP (France 2014, Eurostat `gov_10a_main` D62: 19.8%); government consumption 27.6% (P3: 24.4%). With F7 the government runs a deficit of 18.4% of GDP each quarter (B9: 4.6%), and households net-lend about 18% of GDP (S31). The paper describes the same source | Bug | both (paper too) | I1: government accounts at t = 1 against `sample_raw_data/eurostat/gov_10a_main_fr.csv` (downloaded 2026-10-22) | fixed: `cash_social_benefits` (data configuration, default since 2026-10-22, MD17) takes SOCX public cash spending (France 2013: 19.2% of GDP, against 31.6% total); at t = 1 benefits 17.2% + 1.6% unemployment, deficit 6.2%, household income 67.5% of GDP, consumption unchanged; exp024 | — |
| F7 | Revenue is 41.5% of GDP (France 2014 TR: 53.8%): taxes on production and products 9.3% (D2: 15.7%), corporate tax 7.0% (≈ 2.5%), income tax 4.6% (D5 households ≈ 10%), social contributions 20.5% (D61: 18.9%). Corporate tax is charged on profits of about 17–24% of GDP, far above taxable profits | Spec | both | I1: as F6 | open: rates in the data (`tax_data`): profit tax 38% (statutory with surcharges) on accounting profits; national accounts receipts imply about 13%; income tax a flat 9%; VAT 11.1% on household consumption; employer / employee social contributions 41.9% / 14.1%. Fix: effective rates (receipts / model base) from Eurostat `gov_10a_taxag`; changes the initial state: ask first. Partial: `gov_10a_taxag` is in the data (sample and full); the profit tax is done as an option (`effective_profit_tax`, exp032: 12.7%), which alone widens the deficit to 10.7% of GDP. Left: income tax, social contributions and taxes on production and products, which set the gross–net wage split and so the initial state | P1 |

### E. Engineering and workflow

| ID | Problem | Kind | Source | Evidence | Status | Pri |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | Tests pass while dynamics are broken; no behavioural check runs automatically | Infra | ours | housing IDs, rent bug | partial: `make baseline` | P1 |
| E2 | Weak modularity: hard to run experiments on parts of the model | Infra | both | e.g. a firm-stock reset re-runs the whole financial initialisation | open | P2 |
| E3 | No standard Monte Carlo / experiment procedure | Infra | both | CB7: Emma's code, SLURM arrays | partial: `scoring.py` + `provenance.py` | P2 |
| E4 | No systematic sensitivity analysis of dynamics | Gap | both | CB7: Andrea and Marcela; ablations exp002–004 | partial | P2 |
| E5 | Upstream fixes not yet merged: #56/#64/#67, `bug/government-expenditure` (#83 and #85 merged) | Infra | ours | `make upstream` | open | P2 |
| E6 | Scaling effects (1:100 vs 1:100,000) | Question | both | exp001: 10× agents changes nothing, but firms stay at 1 per industry (G5) | partial | P3 |
| E7 | Standardised outputs, dashboards, reporting to non-coders | Infra | CB7 | I4: every experiment writes a forecast fan, a mechanism dashboard and a ratio heatmap; `make figures` (model map, baseline, ladder, robustness) | done for France; country small multiples wait for D1 | P3 |
| E8 | Agent-level reporting; visualising the synthetic population | Gap | CB7 | — | open | P3 |
| E9 | Report our fixes upstream: rent regression, many-firm crash, data mutation, inventory mapping, capital stock valuation (S30), Poledna layoff count and employee lists (M11, M12), insolvent firms' debt (S28), cost-push pricing (P6), quarterly loan rates (M10) | Infra | ours | — | open: one upstream PR per fix, branched from `upstream/main` | P3 |
| E10 | New-user induction; AI workflows not standardised | Infra | CB7 | I5: AGENTS.md (runner, lifecycle, figures, paper repo), PROJECT.md (model map, claims → evidence), `make test-fast`, `make figures` | done for this fork | — |
| E11 | The file merged from #104 is not ruff-formatted | Infra | ours | `credit_market/func/clearing.py` | workaround: excluded from the format check in the Makefile until upstream merges #104 | P3 |
| E12 | Housing market takes 92% of run time (row-wise pandas loops); blocks finer scales | Infra | ours | profile, 408 firms, 8 quarters: 8.2 of 8.9 s | partial: after M16 the optimal assignment takes 0.03 s instead of 0.8 s a call, and a 12-quarter run 5.2 s instead of 24.6 s (same load); housing is still about 80% of run time, mostly row-by-row pandas updates in `process_housing_market_clearing` and `_filter_feasible_current_sales`. Measured 2026-10-22: a 12-quarter run takes 0.8 s and housing is 45% of it, so it no longer blocks at scale 10,000 | P3 |
| E13 | Plugging in behaviour means editing closed `Literal` lists and hard-wired argument passing in `country.py`; god objects (`firms.py` 2,256 lines, 196 time series) | Infra | ours | 54 behaviour slots, 27 with alternatives; 3 files use hooks | open | P3 |
| E14 | Data and simulation configs duplicate firm settings, reconciled by a compatibility check and a re-initialisation path | Infra | ours | G5, S3, S8 all came from this | open | P2 |
| E15 | Stale alternatives: `PolednaCreditMarketClearer` returns a DataFrame where the credit market now expects four loan arrays (fails at the first quarter); other unused rule classes are untested | Infra | upstream | building the Poledna-like ladder rung | open: fix or delete; the Poledna-like rung uses the default clearer without household loans. `ConstantGrowthGovernmentConsumptionSetter` counted the price level twice (real spending grew 1.4%/q at zero growth): fixed with a regression test Configured but never called (2026-10-22 scan): `firms.offered_wage_setter`, `households.rent` (rents are indexed by the property function, M14), `economy.sentiment`; their parameters change nothing. | P3 |

### D. Data

| ID | Problem | Kind | Source | Evidence | Status | Pri |
| --- | --- | --- | --- | --- | --- | --- |
| D1 | The paper needs 2010–2017 and 38 countries with real micro-data; we have the public sources only, and spoofed HFCS and Compustat | Data | ours | `sample_raw_data/`; see Data | partial (interim): full public data built 2026-10-22 (`make data`, ICIO 2011–2017, every country); open: ICIO 2010 (manual download), HFCS and Compustat (licensed; ask INET first), a labour-share source after 2014 | P1 |
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
| 2½ | **Intermezzo: audit, tidy, visualise** (below): check the economic logic of the model as it now runs, clean and document what we own, a small set of standard figures, a paper ↔ model map, and a workflow that turns a change into a scored, plotted, paper-ready result in one step | I1–I5, E13, E7, E10 | done 2026-10-22 (see Next step); left: the interactions-off rung for E_AR1, country small multiples (need D1) |
| 3 | **Prices and money**: prices from costs and demand (not copied from the forecast); a working Taylor rule; decide forecast noise | P2–P4 | inflation emerges from the model and responds to slack; the policy rate reacts |
| 4 | **Markets and government**: housing (rental market, speed), consumer credit, taxes and benefits, trade | M1–M5, F1, E12, E5 | each market passes a plausibility check; remaining upstream fixes merged |
| 5 | **Calibration done properly**: choose parameters by sensitivity analysis, informed priors, fit on 2010–2013, score on held-out years | R2, R3, R4, E4 | sanity gate passed after calibration; target met for France, then several countries |
| 6 | **Reviewer experiments**: ablation ladder (Poledna-like → full), simple-expectations / interactions-off, VAR benchmark, unemployment and growth in the results table, uncertainty | see `revision_plan.md` "Post" entries | the numbers the paper's Post entries wait for |

In parallel: **D1** (full raw data for 2010–2017 and 38 countries), needed by phase 5.

### Intermezzo: audit, tidy, visualise (phase 2½)

Why now: phases 1–2 changed most of the model's behaviour, and phases 3–6 (Taylor rule, calibration, the
38-country ablation ladder, the paper) multiply runs and readers. Pareto rule throughout: do what makes every
later change cheaper or safer, skip polish nobody reads. Upstream-shaped code (`firms.py`, `country.py`) is
not refactored wholesale (merge cost, E13); we clean what we own and document the rest. Order: I1 with I3 (one
pass through the model), then I2, I4, I5.

| # | Work package | What it delivers | Done when |
| --- | --- | --- | --- |
| I1 | **Economic-logic audit** | One walk through a quarter's sequence of events, agent by agent: for each rule in use, what it says, its units, its economic sense, the paper's equation and our MD. Includes the one-at-a-time sensitivity of the MD15–MD16 values (λ, separation rate, productivity growth, slack sensitivity, spare capacity, deflator), 20 quarters and many firms, and the zero-growth fixed point. Known suspects: ROW forecasts still draw noise (`row_configuration.assume_zero_noise=False`); the government plans in CPI terms but buys at expected PPI inflation; investment ignores interest rates (G17); dividends off (MD6); unbacked flows (S9, S10, S13) | every rule in use has a row in the model map (I3) and every doubt is in the register; the sensitivity shows a plateau or a knife edge for each value |
| I2 | **Tidy what we own** | Experiments: one shared step runner in `scoring.py`, so an experiment is its question, its steps and nothing else (today each repeats ~100 lines). `settings.py` grouped and named by MD. Docstrings of our classes state economic meaning and units; dead code we added deleted. Tests: a fast unit subset for every commit, the slow simulation tests before a default change. PROJECT.md "What we have learned" condensed to one paragraph per mechanism | `make check` passes; a new experiment is ≤ 40 lines; PROJECT.md reads top to bottom as the current state |
| I3 | **Paper ↔ model map** | One table in PROJECT.md (replacing "Where the defaults differed from the paper"): paper section / equation `\label` → code (class, file) → default in use → status (as in the paper / changed by MD# / not in the paper) → revision-plan entry (E#, referee IDs). Plus `settings.LADDER`: the ordered switches from a Poledna-like model to today's defaults, so the ablation ladder (phase 6) is one experiment | every equation of `appendix_model_description.tex` has a row; the ladder runs end to end on France |
| I4 | **Visualisation, five figure families** | One plotting module (`experiments/plotting.py`; fixed colours and labels, PDF for the paper, PNG for reviewing), `make figures`: (a) **model map**, one diagram of agents, markets and the quarter's sequence with the rules in use and their MD#s (the paper's `structure.tikz`, updated); (b) **forecast fan**, model median and 10–90% band across seeds, data and AR(1), per aggregate; (c) **mechanism dashboard**, one page on what the economy is doing inside: sectoral net lending (stock-flow), capacity utilisation and the capital gap, labour flows (unemployment, vacancies, hires, separations), prices against unit costs and wages against the CPI, expected against realised growth, the government plan against realised spending, accounting residuals; (d) **comparison heatmap**, sim/AR(1) by step × aggregate, diverging at 1 (experiments, scorecard history, ablation ladder; country × aggregate once D1); (e) **country small multiples**, one row of fans per country (once D1). No interactive dashboard unless static figures prove insufficient | every experiment writes (b) and (c) without extra code; the scorecard history and the ladder render as (d) |
| I5 | **Workflow for agents and for the paper** | AGENTS.md rewritten to be true and short (structure, the runner, figure rules, the experiment lifecycle: question and hypothesis before running → run → experiments row and section → MD row and baseline row if a default changes). "Claims → evidence" lists every revision-plan Post entry (ablation ladder, simplified expectations, VAR benchmark, uncertainty bands, recovery period, country vs area) with its experiment and figure. One checkpoint memory. Upstream-worthy fixes listed (E9) | a fresh session goes from AGENTS.md and PROJECT.md to a new ablation rung with its paper figure without reading the history |

### Calibration plan (phase 5, prepared during the intermezzo)

- **The paper's estimated parameters** (`table:prior`): φ^Q_F, φ^DP, φ^CP (discrete; posterior 0, 0, 0), φ^StY
  (0.10), χ^H, χ^M, χ^K (0.53, 0.03, 0.18; caps on *target production*). The code has no χ on target production
  (G4), and today's defaults use cost pass-through 0.5 (MD14) where the paper's posterior has φ^CP = 0. The
  rewritten paper should say so; calibrating the paper's parameter set here first needs G4.
- **Candidate parameter set for this model**: the values our decisions fixed by economic argument, in-sample:
  λ and demand smoothing (MD10, sensitive: exp022), separation rate (MD11), productivity growth (MD12), slack
  sensitivity (MD13), cost pass-through and wage catch-up speed (MD14), initial utilisation (MD15).
- **Machinery**: `macrocalib.Sampler` (configuration updater + observer, parallel) and `training_pipeline`
  (sbi NPE). Install the `calibration` extra (torch, sbi; not installed). The observer is `scoring.simulate`'s
  scored series; the updater is a `settings`-style function of a parameter vector. Untested (R5).
- **Data**: calibrate on 2010–2013 and score from 2014 on held-out start dates and countries: needs D1.

## Claims → evidence

Every paper claim and revision-plan entry (`../paper-macro-model/docs/revision_plan.md`) that waits on a result,
with what this repository has for it. France on sample data is a diagnostic, never the paper's evidence (D1).

| Claim or entry (referee IDs) | Paper location | Evidence here | Status |
| --- | --- | --- | --- |
| Beats AR(1) and IIASA on forecasting RMSE | `table:forecasting_gdp` | `make baseline`: France, sample data, uncalibrated: GDP 0.97, HH cons. 1.00, gov. cons. 1.79, invest. 1.05, CPI 0.75 | needs D1, calibration (phase 5), 38 countries |
| E1 growth mechanism (R1.2) | §4, App. A.2 | MD10–MD15: spare capacity, partial-adjustment investment, labour-augmenting productivity (+0.25%/q, exogenous) | E1's planned text ("no exogenous TFP, growth endogenous") is no longer true: rewrite once MD12 is settled |
| E2 target vs actual production, the χ parameters (R1.GEN.3) | §3, App. A | MD19: target production is capped as in the paper, at its posterior χ (0.53, 0.03, 0.18); the code also caps intermediate purchases by capital capacity, and investment is not capped (MD15). exp026: χ = 1 stops growth | the text can describe the paper's rule plus the purchase cap. Check: the revision plan's E2 quotes χ^K ≈ 0.56 where `table:prior` has 0.18 |
| E8 live vs dormant mechanisms (R1.1, R2.1, R2.7) | §3 table | "Model map" above: every rule in use and its status; dormant: φ^FM = φ^FK = 0, h^U = h^E = 0, φ^WN = 0, inventory target off | ready; separations and productivity growth are now live (MD11, MD12) |
| E_ATTR ablation ladder (R1.1, R2.1) | §5 table | exp023 on France (`settings.LADDER`, `ratios.png`; result in the Experiments table): P0 IIASA-like (substitutable inputs, no housing, firm credit only, no reservation wages, Taylor rule), P1–P4 the paper's innovations, 1–10 our decisions | method ready; one bank, fixed-markup rates and homogeneous consumption are not switchable yet (P0 is IIASA-like, not IIASA); 38 countries need D1 |
| E_AR1 simplified expectations, interactions off (R2.7) | §4, §5 | `scoring.expectation_wedge`: on France (defaults, 3 seeds, 12 quarters) firms' expected-growth path scores 1.05 × AR(1) and the realised path 0.93 (correlation 0.26); expected inflation 0.98, realised 0.86 (correlation −0.96: expected inflation drifts down, realised rises with cost pass-through). The model does not replay its expectations | diagnostic built; the interactions-off rung is still to design |
| E22 uncertainty bands (R2.4) | Figure 2, Table 5 | `plotting.forecast_fan`: median and 10–90% across seeds | method ready; note that only market matching and price noise are random now (MD15) |
| E23 VAR peer benchmark (R1.9, R2.2) | Table 5 | `scoring.var_forecast`: VAR(p) on the five aggregates, p by AIC; the scorecard reports `sim / VAR`. On France 2000–2013 AIC picks p = 0 (the means): baseline sim/VAR 0.94, 1.09, 1.41, 1.15, 0.86 | built; 38 countries need D1 |
| E24 recovery period (R2.6) | §5 | needs other start dates (D1) | blocked |
| E25 country vs area (R2.5) | future work | — | optional |
| E28 simulation-validity diagnostics (R2.O.4) | appendix | mechanism dashboard (`inside_k.png`), accounting checks, single runs in `series_k.csv` | ready |
| E29 unemployment and GDP growth in Table 5 (R2.O.5) | Table 5 | scorecard has unemployment RMSE and growth | ready |
