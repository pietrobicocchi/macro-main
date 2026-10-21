"""exp010: Do labour-market search frictions keep unemployment plausible while the economy grows? (G13)

exp009 showed that the steady-growth engine (growth expectations, spare capacity 0.85, investment λ = 0.25 with
desired capital on smoothed demand 0.10) hires the whole unemployed pool within two years, because nobody separates
and firms fill every vacancy within the quarter. Here employees separate at rate s per quarter and hires are capped by
a Cobb-Douglas matching function whose efficiency makes the initial unemployment rate (10.3%) a steady state
(`settings.search_frictions`). Work effort is capped at 1.1 (G12) throughout the engine runs.

Steps: frictions on today's defaults (unemployment should stay put); the engine without frictions (exp009's
reference); the engine with frictions at s = 0.03, then s = 0.02 and 0.04, and matching elasticity 0.7.

Usage:
    uv run python experiments/exp010_search_frictions.py [--seeds 5] [--quarters 20]

Writes to outputs/exp010_search_frictions/: run.json, summary.csv, series_<k>.csv, figure_<k>.png
"""

import argparse
import logging
import warnings
from functools import partial

import numpy as np
import pandas as pd
from provenance import record_run
from scoring import COUNTRY, ROOT, START, accounts_summary, load_data, observed, plot, scorecard, simulate
from settings import OMEGA, growth_expectations, investment_engine, search_frictions, spare_capacity, work_effort_cap

from macromodel.configurations import CountryConfiguration

ENGINE = [
    growth_expectations,
    spare_capacity,
    partial(investment_engine, adjustment_speed=0.25, demand_smoothing=0.10),
    partial(work_effort_cap, cap=1.1),
]


def frictions(**kwargs):
    return partial(search_frictions, **kwargs)


# (label, list of config changes applied on top of defaults, initial utilisation built into the data)
STEPS = [
    ("defaults + frictions s 0.03", [frictions(separation_rate=0.03)], 1.0),
    ("engine, no frictions", ENGINE, OMEGA),
    ("engine + frictions s 0.03", ENGINE + [frictions(separation_rate=0.03)], OMEGA),
    ("engine + frictions s 0.02", ENGINE + [frictions(separation_rate=0.02)], OMEGA),
    ("engine + frictions s 0.04", ENGINE + [frictions(separation_rate=0.04)], OMEGA),
    (
        "engine + frictions s 0.03, alpha 0.7",
        ENGINE + [frictions(separation_rate=0.03, matching_elasticity=0.7)],
        OMEGA,
    ),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--quarters", type=int, default=20)
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING)
    warnings.filterwarnings("ignore")
    out_dir = ROOT / "outputs" / "exp010_search_frictions"
    record_run(out_dir, **vars(args), country=COUNTRY, start=START, steps=[s[0] for s in STEPS])

    data = {u: load_data(utilisation_rate=u) for u in {u for *_, u in STEPS}}
    obs = observed(next(iter(data.values())))
    target = obs.loc[obs.index > START]
    scored = min(12, args.quarters)
    rows = []
    for k, (label, changes, utilisation) in enumerate(STEPS):
        config = CountryConfiguration()
        for change in changes:
            change(config)
        audit = []
        try:
            sim = pd.concat(
                [
                    simulate(data[utilisation], config.model_copy(deep=True), s, args.quarters, audit)
                    for s in range(args.seeds)
                ],
                ignore_index=True,
            )
        except (ValueError, FloatingPointError) as error:
            print(f"[{k}] {label}: diverged ({type(error).__name__})")
            rows.append({"step": label, "diverged": True})
            continue
        sim.to_csv(out_dir / f"series_{k}.csv", index=False)
        plot(sim, obs, scored, f"exp010 step {k}: {label}", out_dir / f"figure_{k}.png")
        card = scorecard(sim[sim["t"] <= scored], obs, scored)
        accounts = accounts_summary(audit)
        median_path = sim.groupby("t")[["Real GDP", "Real Investment"]].median()
        rows.append(
            {
                "step": label,
                **{f"{agg} sim/AR1": card.loc[agg, "sim / AR(1)"] for agg in card.index if agg != "Unemployment Rate"},
                "GDP growth/q (12q)": card.loc["Real GDP", "sim mean"],
                f"GDP growth/q ({args.quarters}q)": sim["Real GDP"].mean(),
                "GDP growth/q (last 8q)": median_path["Real GDP"].iloc[-8:].mean(),
                f"investment growth/q ({args.quarters}q)": sim["Real Investment"].mean(),
                "unemployment q12": sim.loc[sim["t"] == scored, "Unemployment Rate"].median(),
                f"unemployment q{args.quarters}": sim.loc[sim["t"] == args.quarters, "Unemployment Rate"].median(),
                "hiring rate/q": sim["Hiring Rate"].mean(),
                "separation rate/q": sim["Separation Rate"].mean(),
                "worst unexplained money/GDP": accounts.loc["money.unexplained", "worst share of GDP"],
                "diverged": False,
            }
        )
        print(
            f"[{k}] {label}: GDP growth/q {rows[-1][f'GDP growth/q ({args.quarters}q)']:+.4f}, "
            f"unemployment {rows[-1][f'unemployment q{args.quarters}']:.3f}"
        )

    summary = pd.DataFrame(rows).set_index("step")
    summary.loc["data (France 2014-)"] = pd.Series(
        {
            "GDP growth/q (12q)": target["Real GDP"].iloc[:12].mean(),
            f"GDP growth/q ({args.quarters}q)": target["Real GDP"].iloc[: args.quarters].mean(),
            f"investment growth/q ({args.quarters}q)": target["Real Investment"].iloc[: args.quarters].mean(),
            "unemployment q12": target["Unemployment Rate"].iloc[scored - 1],
            f"unemployment q{args.quarters}": target["Unemployment Rate"].iloc[args.quarters - 1],
        }
    ).reindex(summary.columns, fill_value=np.nan)
    summary.to_csv(out_dir / "summary.csv")
    pd.set_option("display.width", 250)
    print(summary.T.to_string(float_format=lambda x: f"{x:.3f}"))
    print(f"\nwritten to {out_dir.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
