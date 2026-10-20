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
| exp001 | Does the default model produce plausible dynamics? | done, re-run after each fix | Fails the sanity gate; see the scorecard history. `outputs/exp001_baseline/` |

### Baseline scorecard history

`make baseline` run after each change on `main`: `sim / AR(1)` RMSE ratio, plus the
mean quarterly real GDP growth (data: +0.64%) and the median unemployment rate after
12 quarters (data: ~10%).

| State of `main` | GDP | HH cons. | Gov. cons. | Invest. | CPI | GDP growth | Unemp. q12 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| upstream `76ac000` | 1.63 | 3.92 | 8.10 | 1.81 | 3.65 | −0.53% | 16.0% |
| + PR #93 housing IDs | 1.68 | 4.03 | 8.83 | 1.99 | 3.67 | −0.62% | — |
| + PR #104 credit units | 7.00 | 3.37 | 8.32 | 2.06 | 3.78 | explodes | 15.8% |
| + rent-regression fixes (ours) | **1.46** | 3.54 | 8.40 | 1.88 | 3.73 | −0.34% | 15.0% |

## What we have learned

- **The model still fails the sanity gate** after #93, #104 and the rent fixes
  (exp001, 10 seeds, 12 quarters):
  - Real GDP: −0.34%/quarter in the model vs +0.64% in the data.
  - Unemployment: 10.3% → 15% (median).
  - Real government consumption: −0.65%/quarter, with swings of ±10–20% per quarter.
  - Household consumption growth now matches the data on average (+0.38% vs +0.40%).
  - On the original upstream `main`, over 20 quarters (one seed): CPI +36%, real
    output −17%, unemployment 28%.
- **Rent-regression bugs (ours, not fixed upstream):**
  `HousingMarket.compute_observed_fraction_rent_value` had two problems:
  - It fitted value on rent (arguments swapped), while its coefficients are used as
    rent = slope × value + intercept.
  - It fitted a line through a single rental, giving an arbitrary slope.

  Once #104 lets households buy, the vacated houses were listed at 35–72% of their
  value per quarter. Imputed rent rose 11× in 8 quarters and output GDP doubled.
  Fixed: correct orientation, and re-estimate only with at least two distinct
  property values (the same guard is applied to the sale-price fit). Both have tests.
- **The rental market is nearly dead:** 0–1 rentals per quarter vs 400–500 sales.
  Some initial houses have quarterly rent above their value (rent/value up to 2.8),
  possibly an artefact of the spoofed data.
- **Too few agents is not the cause** (exp001, scale 10,000 vs 1,000): 10× more
  agents leaves the noise and drift unchanged.
- **The Taylor rule is inert** (exp001, `PolednaPolicyRate`): the rate hits zero by
  quarter 3 and the outputs are the same as with a constant rate. The default
  is `ConstantPolicyRate`.
- **Initial state is not a steady state:** aggregate firm profits are negative at t=0
  and stay negative, and consumer credit still decays towards 0 after #104. Mortgage
  debt drops about 27% in quarter 1 and then recovers slowly.
- **Housing IDs (fixed by #93):** a find-replace in `af38e45a` had set every house,
  owner and inhabitant ID to −1 at initialisation.
- **The data target may be wrong too:** macro_data's "Real GDP" is GDP deflated by
  PPI, giving +2.6%/yr for France 2014–16, while official real GDP growth was
  about 1%/yr.
- Runs are deterministic per seed. A 12-quarter France run takes about 1 s at
  scale 10,000.

## Open threads

1. **Merge the remaining upstream fixes** one at a time, recording the scorecard
   after each:
   - #83 Taylor rule, #85 frequency conversion
   - #56, #64, #67 productivity, investment and substitution
   - `bug/government-expenditure` (no open PR)
2. **Report the rent-regression fixes upstream** (a PR from a branch off `upstream/main`).
3. **Initial-state consistency:** why are firm profits negative at t=0? Write a
   t=0 accounting test (stock-flow and sectoral balances).
4. **Government consumption volatility:** this should be the smoothest series but
   is the worst. Check whether goods-market rationing leaves government demand unfilled.
5. **Unemployment drift:** trace firms' labour demand against production targets.
6. **Consumer credit decay** despite #104: is demand or supply the binding side?
7. **Deflators:** decide the right deflator for each aggregate, on both the data
   side and the model side.
8. **Calibration:** only after the sanity gate passes. Find the paper's posterior
   or calibrated parameters.
9. **Real micro-data:** find out whether HFCS and Compustat access is available.

## Claims → evidence

| Claim in the paper | Figure / table | Experiment |
| --- | --- | --- |
| Beats AR(1) and IIASA on forecasting RMSE | `table:forecasting_gdp` | not yet reproduced |
