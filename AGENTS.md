# AGENTS.md

Rules for any coding agent working in this repository. Loaded every session.
Keep it short (about 160 lines), and keep it true.

## What this is

A data-driven macroeconomic ABM (Wiese et al.), competitor of the IIASA/Poledna model, built
from this code (the paper's own code is not available). The work: make its dynamics
economically credible, then run the experiments the referees asked for, for a rewritten paper.

Optimise, in this order: **correctness → readability → reproducibility → simplicity.**

## Where things are recorded

[PROJECT.md](PROJECT.md) is the living state. Read it before starting work:
- **Issue register**: every known problem has an ID. Add a row for anything new you
  find, update its status when you fix it, and start commit subjects with the ID (`G1: ...`).
- **Roadmap**: the phases (1–6, with the intermezzo 2½) and their "done when" criteria. Work in order.
- **Modelling decisions**: one row per modelling choice, with the economic reason
  written *before* seeing the result. Choices follow economic reasoning, guided by
  the paper and the referee reports, never by what makes the fit look better.
- **Model map**: every rule the default model uses against the paper's equation, with its
  status (as the paper / our decision MD# / upstream departure, register ID). Update its
  row when a default changes.
- **Baseline scorecard history**: one row per change to default behaviour.
- **Claims → evidence**: each paper claim and revision-plan entry with its experiment and figure.

The paper is in `../paper-macro-model` (`main.tex`, `appendix_model_description.tex`,
`docs/revision_plan.md` with entries E# and referee IDs). Read it freely; never edit it
from here (its own CLAUDE.md governs edits).

## Structure

```
macro_data/    raw data -> initial state (readers/ per source, processing/ synthetic_* builders)
macromodel/    the engine: simulation.py, country/, agents/, markets/, economy/ (aggregates,
               forecasts), configurations/ (pydantic: behaviours and parameters), accounting.py
macrocalib/    NPE calibration (optional extra `calibration`, untested: R5)
experiments/   expNNN_*.py entrypoints, plus
  scoring.py     data, simulate, scorecard, Step and run_experiment (the runner)
  settings.py    named config changes: the ablation LADDER, reverts (pre_md*), alternatives
  plotting.py    every figure: forecast fan, mechanism dashboard, ratio heatmap, model map
  figures.py     FIGURES registry, `make figures` -> outputs/figures/ (PDF and PNG)
  provenance.py  run records (commit, dirty files, command, parameters)
  public_data.py `make data`: the full public raw data in ~/Documents/dev/phd/datasets (D1)
outputs/       generated results, one directory per experiment (gitignored)
extra/         local reference material, never published (gitignored)
```

**Behaviour is pluggable.** Each agent/market has a module with state and step methods,
a time-series module and `func/<behaviour>.py` with alternative rule classes, selected
by name in `configurations/<name>_configuration.py` and loaded by
`macromodel/util/function_mapping.get_functions`. To add a rule: a new class in `func/`,
its name in the config `Literal`, select it in config. **Keep the old rule**: every new
mechanism must be switchable, so it can be ablated. Do not branch on flags in step methods.

**One quarter** (`Simulation.iterate`): expectations → targets → labour market → housing
and credit markets → goods market (with ROW) → realised accounts. Read results with
`country.economy.ts.get_aggregate("<series>")`; `scoring.simulate` returns the scored series
and the mechanism-dashboard series.

## Data

Experiments run on the test sample: public data cut to France or 2014, plus **spoofed** HFCS
(households) and Compustat (firms, banks). The full public data (`make data`, opt-in with
`MACRO_RAW_DATA`) still has the spoofed micro-data. Both are interim, for diagnosing mechanisms,
not for claims in the paper; the data discussion lives in PROJECT.md, Data (D1). Defaults: scale 10,000 (≈2.9k households,
1 bank) and **one firm per industry**; use `scoring.load_data(many_firms=True)` for
business-demography counts.

## Experiments

An experiment is its question and its steps; `scoring.run_experiment` does the rest
(provenance, data per step, runs, `fan_k.png`, `inside_k.png`, `summary.csv`, `ratios.png`):

```python
"""exp0NN: <question>. Hypothesis (recorded before running): <what and why>."""
from scoring import Step, run_experiment
from settings import wage_phillips_curve
STEPS = [Step("defaults"), Step("Phillips curve", [wage_phillips_curve])]   # data={...} if initial stocks change
if __name__ == "__main__":
    run_experiment(__file__, __doc__, STEPS)
```

Lifecycle: write the question and hypothesis first → `make exp EXP=exp0NN` (smoke with
`ARGS="--seeds 1 --quarters 2"`) → look at the fans and the mechanism dashboard, not only the
ratios → experiments row and a section in PROJECT.md → if a default changes: MD row,
model-map row, `make baseline`, scorecard-history row. Config changes live in `settings.py`
(never inline); experiments never import each other; never edit outputs. An experiment
reproduces at the commit in its `run.json`; old experiments are not kept in step with new
defaults. The ablation ladder (`settings.LADDER`, exp023) must end at today's defaults
(tested): a new default needs a new rung.

## Figures

Every figure goes through `plotting.py` (one style, `COLORS`, `LABELS`, units on axes,
bands state what they are). Five families: model map, forecast fan, mechanism dashboard,
ratio heatmap, country small multiples (once there are countries). A paper figure is an
entry in `figures.FIGURES`; `make figures` writes it to `outputs/figures/`.

## Validation

**Passing tests do not mean sane dynamics** (the suite passed while every housing ID was −1).
Validate behaviour with `make baseline` or an experiment and its mechanism dashboard; the
accounting checks (`macromodel/accounting.py`) run in every scored run. Tests are
risk-weighted: identities, units, initial-state consistency, determinism; a regression test
for every bug fixed.

## Known traps

- **Firm settings that change initial stocks** (utilisation rates, inventory target)
  must be built into the data with matching values (`scoring.load_data(...)`).
  Otherwise `Simulation.from_datawrapper` re-runs the financial initialisation,
  which double-counts bank deposits and diverges (S3).
- Realised inflation equals the AR(1) price forecast (P2); forecast noise is off by
  default since MD15 (`assume_zero_noise=True`).
- Firms start with spare capacity by default (utilisation 0.85, MD15), in both the data and the
  simulation configuration; `scoring.load_data` builds 0.85 unless told otherwise.
- The rest of the world's forecasts still draw noise (`row_configuration.assume_zero_noise`, M15).
- Social benefits are SOCX cash spending by default (MD17); the data needs
  `oecd_econ/SOCX_AGG_BY_TYPE.csv`. Tax rates are statutory, not effective (F7), and households'
  financial income has no payer (S9): the net-lending panel of the dashboard reflects both.
- Scoring targets are seasonally adjusted (R7): experiments run before 2026-10-22 scored CPI
  against the unadjusted CPI; compare their ratios only within the same experiment.
- `economy.compute_gdp(always_adjust=True)` forces GDP to balance via imports/exports (S6).
- pandas 3 (Copy-on-Write): chained assignment `df["a"][mask] = x` silently does
  nothing; use `df.loc[mask, "a"] = x`.
- Annual vs quarterly units: check every conversion from data.
- `macromodel/util/` and `macromodel/utils/` both exist; `tests/test_macrocalib` is skipped.

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

`make test-fast` while working; `make check` (all tests, lint, baseline) before committing a
behaviour change. Update PROJECT.md: register status, scorecard
history if defaults changed, a modelling-decision row if a choice was made, and the
experiments table. Then report: **Changed** (one line per file), **Effect** (scorecard
before → after), **Assumptions** (to verify), **Run** (exact command).
