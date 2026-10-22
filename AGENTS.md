# AGENTS.md

Rules for any coding agent working in this repository. Loaded every session.
Keep it under ~150 lines, and keep it true.

## What this is

A data-driven macroeconomic agent-based model (Wiese et al.), the main competitor
of the IIASA/Poledna model. The code behind the original paper is not available;
everything is built from this code. The work is to make its dynamics economically
credible, then run the experiments the referees asked for, for a rewritten paper.

Optimise, in this order: **correctness → readability → reproducibility → simplicity.**

## Where things are recorded

[PROJECT.md](PROJECT.md) is the living state. Read it before starting work:
- **Issue register**: every known problem has an ID. Add a row for anything new you
  find, update its status when you fix it, and start commit subjects with the ID (`G1: ...`).
- **Roadmap**: the six phases and their "done when" criteria. Work in phase order.
- **Modelling decisions**: one row per modelling choice, with the economic reason
  written *before* seeing the result. Choices follow economic reasoning, guided by
  the paper and the referee reports, never by what makes the fit look better.
- **Baseline scorecard history**: one row per change to default behaviour.

## Structure

```
macro_data/    raw data -> initial state (DataWrapper)
  readers/       one reader per source (OECD, Eurostat, ICIO, HFCS, Compustat, IMF, ...)
  processing/    synthetic_* builders: population, firms, banks, markets, ROW
macromodel/    the simulation engine
  simulation.py  Simulation: owns countries, ROW, goods market, exchange rates
  country/       Country: one economy; wires agents and markets together
  agents/        firms, households, individuals, banks, central_bank, governments
  markets/       goods, labour, credit, housing
  economy/       national-accounts aggregates and the AR(1) growth/inflation forecasts
  configurations/  pydantic configs; select behaviours and parameters
macrocalib/    NPE calibration (sbi/torch, optional extra `calibration`)
experiments/   expNNN_*.py entrypoints, plus scoring.py (shared metric),
               settings.py (named config changes), provenance.py (run records)
outputs/       generated results, one directory per experiment (gitignored)
extra/         local reference material, never published (gitignored)
```

**Behaviour is pluggable.** Each agent/market has a module with state and step methods,
a time-series module and `func/<behaviour>.py` with alternative rule classes, selected
by name in `configurations/<name>_configuration.py` and loaded by
`macromodel/util/function_mapping.get_functions`. To add a rule: a new class in `func/`,
its name in the config `Literal`, select it in config. **Keep the old rule**: every new
mechanism must be switchable, so it can be ablated. Do not branch on flags in step methods.

**One period** (`Simulation.iterate`): per country initialisation → estimation →
target setting → labour market → planning metrics → housing market → credit market →
prepare goods market; then ROW planning; one global goods market clears; then per
country realised metrics and population update. One period is a quarter.

**Reading results:** `country.shallow_output()` or
`country.economy.ts.get_aggregate("<series>")` (series in `economy/economy_ts.py`).

## Data

Only the test sample data is on this machine: France-relevant public data for 2014 plus
**spoofed** HFCS (households) and Compustat (firms, banks). It is for diagnosing
mechanisms, not for claims in the paper (D1). Defaults: scale 10,000 (≈2.9k households,
1 bank) and **one firm per industry**; use `scoring.load_data(many_firms=True)` for
business-demography counts.

## Experiments

- One question per experiment, stated in its docstring; it writes only to
  `outputs/expNNN_short_name/` and calls `provenance.record_run(out_dir, ...)` first.
- Score with `scoring.py`; take config changes from `settings.py`. Experiments never
  import each other.
- Never edit generated outputs. Record the conclusion in PROJECT.md.
- `make exp EXP=exp004 ARGS="--seeds 5"`; `make baseline` after any behaviour change.

## Validation

**Passing tests do not mean sane dynamics.** The suite passed while every housing ID
was −1 and while a rent bug doubled GDP. Validate behaviour with `make baseline` or an
experiment. Until the accounting checks exist (S1), a matching GDP is not evidence of
consistency. Tests are risk-weighted: accounting identities, unit conversions,
initial-state consistency, determinism per seed; add a regression test for every bug fixed.

## Known traps

- **Firm settings that change initial stocks** (utilisation rates, inventory target)
  must be built into the data with matching values (`scoring.load_data(...)`).
  Otherwise `Simulation.from_datawrapper` re-runs the financial initialisation,
  which double-counts bank deposits and diverges (S3).
- `default_data_configuration` ignores its `single_firm_per_industry` argument (G5).
- Realised inflation equals the AR(1) price forecast (P2); forecast noise is off by
  default since MD15 (`assume_zero_noise=True`).
- Firms start with spare capacity by default (utilisation 0.85, MD15), in both the data and the
  simulation configuration; `scoring.load_data` builds 0.85 unless told otherwise.
- `economy.compute_gdp(always_adjust=True)` forces GDP to balance via imports/exports (S6).
- pandas 3 (Copy-on-Write): chained assignment `df["a"][mask] = x` silently does
  nothing; use `df.loc[mask, "a"] = x`.
- Annual vs quarterly units: check every conversion from data.
- `macromodel/util/` and `macromodel/utils/` both exist. `tests/test_macrocalib` is skipped.

## Git

- `origin` = pietrobicocchi/macro-main (this fork, public); `upstream` = INET-Complexity/macro-main.
- Work and commit directly on `main`; no feature branches. Push to `origin`.
- Commits and PRs are authored by Pietro only: never add `Co-Authored-By` or any AI attribution.
- Before fixing a bug, `make upstream`: an unmerged upstream PR may already fix it.
  Bring those in with `git merge upstream/<branch>` (not cherry-pick), one per commit.
- A fix meant for upstream: branch from `upstream/main`, without the overlay files
  (AGENTS.md, CLAUDE.md, PROJECT.md, experiments/, Makefile).

## Code preferences

Match the surrounding code. Prefer modifying a file over creating one; a function over
a class; duplication over a premature abstraction. Do not create new markdown files:
update README.md, AGENTS.md or PROJECT.md. Ruff, line length 120: `make fmt`.

**EXPLORE** (question open): work in `experiments/`, throwaway code is fine.
**CONSOLIDATE** (it worked): move it into the package as a switchable behaviour, delete
the exploratory copy, add a test for the invariant that matters.

## Decide freely / ask first

Without asking: read code, run tests and experiments, add experiments and tests, fix
lint, fix clear bugs, commit and push to `main`.

Stop and ask before: changing a default behaviour or a model equation; changing the
success metric or gates in PROJECT.md; merging upstream branches; changing data
processing that affects the initial state; adding a major dependency; deleting
experiment results; publishing anything new (the fork is public).

## Finishing a substantial change

`make check` (tests, lint, baseline). Update PROJECT.md: register status, scorecard
history if defaults changed, a modelling-decision row if a choice was made, and the
experiments table. Then report: **Changed** (one line per file), **Effect** (scorecard
before → after), **Assumptions** (to verify), **Run** (exact command).
