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

## Baselines

| Baseline | Why it is the right comparison | Status |
| --- | --- | --- |
| AR(1) on q/q growth, fit 2000-Q3–2014-Q1 | the paper's benchmark | in exp001 |
| Observed French series | ground truth | in exp001 |
| IIASA/Poledna model | the competitor | not set up |

## Experiments

| ID | Question | Status | Result |
| --- | --- | --- | --- |
| exp001 | Does the default model produce plausible dynamics? | done | No. Fails the sanity gate; see below. `outputs/exp001_baseline/` |

## What we have learned

- **Default build fails the sanity gate** (exp001, 10 seeds, 12 quarters):
  - Real GDP: −0.53%/quarter in the model vs +0.64% in the data.
  - Unemployment: 10.3% → 16% (median; data ~10%).
  - Real government consumption: −0.9%/quarter, with swings of ±10–20% per quarter.
  - `sim / AR(1)` RMSE: GDP 1.6, household consumption 3.9, government
    consumption 8.1, investment 1.8, CPI inflation 3.7.
  - Over 20 quarters (one seed): CPI +36%, real output −17%, unemployment 28%.
- **Too few agents is not the cause** (exp001, scale 10,000 vs 1,000): 10× more
  agents leaves the noise and drift unchanged.
- **The Taylor rule is inert** (exp001, `PolednaPolicyRate`): the rate hits zero by
  quarter 3 and the outputs are the same as with a constant rate. The default
  is `ConstantPolicyRate`.
- **Initial state is not a steady state:** aggregate firm profits are negative at
  t=0, mortgage debt halves in the first quarter and consumer credit decays to 0.
  Credit matches upstream PR #104 (a units bug that limits credit supply to near zero).
- **Housing IDs are all −1 on `main`:** a find-replace in `af38e45a` sets every
  house, owner and inhabitant ID to −1 at initialisation
  (`housing_market.py:164-170, 252-255`). Fixed in unmerged upstream PR #93.
  Separately, pandas 3 turns the chained assignment at `housing_market.py:251` into a no-op.
- **The data target may be wrong too:** macro_data's "Real GDP" is GDP deflated by
  PPI, giving +2.6%/yr for France 2014–16, while official real GDP growth was
  about 1%/yr.
- Runs are deterministic per seed. A 12-quarter France run takes about 1 s at
  scale 10,000.

## Open threads

1. **Merge known fixes:** on an integration branch, apply the unmerged upstream PRs
   one at a time and record the `make baseline` scorecard after each:
   - #93 housing IDs
   - #104 consumer credit units
   - #83 Taylor rule, #85 frequency conversion
   - #56, #64, #67 productivity, investment and substitution
   - `bug/government-expenditure` (no open PR)
2. **Initial-state consistency:** why are firm profits negative at t=0? Write a
   t=0 accounting test (stock-flow and sectoral balances).
3. **Government consumption volatility:** this should be the smoothest series but
   is the worst. Check whether goods-market rationing leaves government demand unfilled.
4. **Unemployment drift:** trace firms' labour demand against production targets.
5. **Deflators:** decide the right deflator for each aggregate, on both the data
   side and the model side.
6. **Calibration:** only after the sanity gate passes. Find the paper's posterior
   or calibrated parameters.
7. **Real micro-data:** find out whether HFCS and Compustat access is available.

## Claims → evidence

| Claim in the paper | Figure / table | Experiment |
| --- | --- | --- |
| Beats AR(1) and IIASA on forecasting RMSE | `table:forecasting_gdp` | not yet reproduced |
