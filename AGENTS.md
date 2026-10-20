# AGENTS.md

Rules for any coding agent working in this repository. Loaded every session.
Keep it under ~150 lines, and keep it true.

## What this is

A data-driven macroeconomic agent-based model (Wiese et al.), the main competitor
of the IIASA/Poledna model. It runs, but its dynamics are not yet credible. The
work is to make them credible, understand why they are not, and keep the code
publication-quality.

Optimise, in this order: **correctness → readability → reproducibility → simplicity.**

Current scientific state, open questions and next steps live in [PROJECT.md](PROJECT.md).

## Structure

```
macro_data/    raw data -> calibrated initial state (DataWrapper)
  readers/       one reader per source (OECD, Eurostat, ICIO, HFCS, Compustat, IMF, ...)
  processing/    synthetic_* builders: population, firms, banks, markets, ROW
macromodel/    the simulation engine
  simulation.py  Simulation: owns countries, ROW, goods market, exchange rates
  country/       Country: one economy; wires agents and markets together
  agents/        firms, households, individuals, banks, central_bank,
                 central_government, government_entities
  markets/       goods, labour, credit, housing
  economy/       national-accounts aggregates (GDP, CPI/PPI, unemployment)
  configurations/  pydantic configs; select behaviours and parameters
macrocalib/    NPE calibration (sbi/torch, optional extra `calibration`)
experiments/   entrypoints: one question per file, writes only to outputs/<exp>/
outputs/       generated results (gitignored)
tests/         unit tests (incl. sample raw data at tests/test_macro_data/unit/sample_raw_data)
```

**Behaviour is pluggable.** Each agent/market has `<name>.py` (state + step
methods), `<name>_ts.py` (recorded time series) and `func/<behaviour>.py`
(alternative rule classes). The class used is selected by name in
`configurations/<name>_configuration.py` (e.g. `CentralBankPolicy.name =
"ConstantPolicyRate" | "PolednaPolicyRate"`), loaded by
`macromodel/util/function_mapping.get_functions`. To change a rule, add a class
in `func/`, add its name to the `Literal`, select it in config. Do not branch on
flags inside the step methods.

**One period** (`Simulation.iterate`): per country initialisation → estimation →
target setting → labour market → planning metrics → housing market → credit
market → prepare goods market; then ROW planning; then a single global goods
market clears; then per country realised metrics and population update.
Default period is a quarter (`time_unit` 4).

**Reading results:** `sim.countries["FRA"].shallow_output()` (DataFrame of key
aggregates) or `country.economy.ts.get_aggregate("<series>")` for anything in
`economy/economy_ts.py`.

## Data

Only the bundled sample data is on this machine: real public sources plus
**spoofed** HFCS (households) and Compustat (firms/banks). Results on it are
for diagnosing mechanisms, not for claims in the paper. Default `scale=10_000`
(≈2.9k households, 1 bank for France); scale is not the cause of noise or drift
(exp001).

## Experiments

- One experiment answers one question, stated in its docstring.
- `experiments/expNNN_short_name.py` writes only to `outputs/expNNN_short_name/`
  and calls `provenance.record_run(out_dir, ...)` before writing results.
- Never edit a generated output by hand. Record the conclusion in PROJECT.md.
- Run with `make exp EXP=exp001 ARGS="..."`. `make baseline` is the reference
  check after any change to model behaviour.

## Validation

**Passing tests do not mean sane dynamics.** The suite passed while every
housing ID was silently set to -1. A behavioural change is validated by
`make baseline` (or a dedicated experiment) and its scorecard, not by `make test`.

Tests: risk-weighted. Test where a silent error would invalidate a conclusion:
accounting identities (stock-flow consistency, GDP output = expenditure),
unit/frequency conversions, initial-state consistency, determinism per seed.

## Known traps

- pandas 3 (Copy-on-Write) is installed: chained assignment
  `df["a"][mask] = x` silently does nothing. Use `df.loc[mask, "a"] = x`.
  Watch for `ChainedAssignmentError` warnings in test output.
- Annual vs quarterly units: rates and flows from data are often annual;
  check every conversion against `time_unit`.
- `economy.compute_gdp(always_adjust=True)` forces expenditure GDP to equal
  output GDP by adjusting imports/exports; a GDP match is not evidence of
  consistency.
- `macromodel/util/` and `macromodel/utils/` both exist; check both.
- Calibration tests (`tests/test_macrocalib`) are excluded by default.

## Git

- `origin` = pietrobicocchi/macro-main (this fork). `upstream` = INET-Complexity/macro-main.
- Before fixing a model bug, run `make upstream` and check open upstream PRs:
  many known bugs already have unmerged fixes there.
- Work on a branch, never directly on `main`. Commit or push only when asked.
- Fixes meant for upstream: branch from `upstream/main` and keep overlay files
  (AGENTS.md, CLAUDE.md, PROJECT.md, experiments/, Makefile) out of the PR.

## Code preferences

Match the surrounding code. Prefer modifying a file over creating one; a
function over a class; duplication over a premature abstraction. Delete
obsolete code rather than preserve compatibility, unless upstream needs it.
Do not create new markdown files: update README.md, AGENTS.md or PROJECT.md.
Ruff, line length 120: `make fmt`, `make lint`.

## Two modes

**EXPLORE**: the question is open. Work in `experiments/`; throwaway code is
fine. Do not refactor `macromodel/` or `macro_data/`.

**CONSOLIDATE**: something worked. Move it into the package, delete the
exploratory copy, add a test for the invariant that matters.

## Decide freely / ask first

Without asking: read code, run tests and experiments, write targeted tests,
fix lint, produce plots, add experiments, fix clear bugs on a branch.

Stop and ask before: changing a model equation or default behaviour;
changing a metric definition or the success metric in PROJECT.md; merging
upstream branches; changing data processing that affects the initial state;
adding a major dependency; deleting experiment results; anything that touches
the paper's claims.

## Finishing a substantial change

Run `make test`, `make lint`, `make baseline`. Update PROJECT.md (experiments
table, what we have learned, open threads). Then report briefly:

**Changed**: one line per file: what and why
**Effect**: baseline scorecard before → after
**Assumptions**: anything decided that should be verified
**Run**: the exact command to reproduce it
