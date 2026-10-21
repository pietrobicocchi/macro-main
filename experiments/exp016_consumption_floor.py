"""exp016: Does removing the consumption floor (S26) fix the start-up jump, for today's defaults and the candidates?

Households consume at least (1 - saving rate) x benefits, with benefits counted as if every adult received
unemployment benefit; the floor exceeds the income of 40% of households and was not in the initial state, so household
consumption jumps 7% in the first quarter. In candidate B the jump, with the release of spare capacity, sends
unemployment from 10.3% to 7.7% within five quarters (exp015). Steps: defaults, defaults without the floor, candidate
A (cost pass-through, yearly wage catch-up) with and without the floor, candidate B without the floor.

Usage:
    uv run python experiments/exp016_consumption_floor.py [--seeds 10] [--quarters 20]

Writes to outputs/exp016_consumption_floor/: run.json, summary.csv, series_<k>.csv, figure_<k>.png
"""

import argparse
import logging
import warnings
from functools import partial

import numpy as np
import pandas as pd
from provenance import record_run
from scoring import COUNTRY, ROOT, START, accounts_summary, load_data, observed, plot, scorecard, simulate
from settings import (
    OMEGA,
    growth_expectations,
    growth_forecast_slack_aware,
    investment_engine,
    labour_productivity_growth,
    lagged_wage_indexation,
    no_consumption_floor,
    price_brakes,
    search_frictions,
    spare_capacity,
    work_effort_cap,
)

from macromodel.configurations import CountryConfiguration

PRICES_AND_WAGES = [partial(price_brakes, cost_pass_through=0.5), partial(lagged_wage_indexation, speed=0.25)]
ENGINE = [
    growth_expectations,
    spare_capacity,
    partial(investment_engine, adjustment_speed=0.25, demand_smoothing=0.10),
]
EFFORT_CAP = [partial(work_effort_cap, cap=1.1)]
FRICTIONS = [search_frictions]
PRODUCTIVITY = [partial(labour_productivity_growth, rate=0.0025)]
SLACK_FORECAST = [partial(growth_forecast_slack_aware, sensitivity=0.2)]
PARTS = {
    "slack-aware forecast": SLACK_FORECAST,
    "search frictions": FRICTIONS,
    "productivity growth": PRODUCTIVITY,
    "prices and wages": PRICES_AND_WAGES,
    "work-effort cap": EFFORT_CAP,
}
CANDIDATE_B = ENGINE + [change for part in PARTS.values() for change in part]

# (label, list of config changes applied on top of defaults, initial utilisation built into the data)
STEPS = [
    ("defaults", [], 1.0),
    ("defaults, no floor", [no_consumption_floor], 1.0),
    ("A", PRICES_AND_WAGES, 1.0),
    ("A, no floor", PRICES_AND_WAGES + [no_consumption_floor], 1.0),
    ("B, no floor", CANDIDATE_B + [no_consumption_floor], OMEGA),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--quarters", type=int, default=20)
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING)
    warnings.filterwarnings("ignore")
    out_dir = ROOT / "outputs" / "exp016_consumption_floor"
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
        plot(sim, obs, scored, f"exp016 step {k}: {label}", out_dir / f"figure_{k}.png")
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
                "CPI inflation/q": sim["CPI Inflation"].mean(),
                "policy rate (last)": sim.loc[sim["t"] == args.quarters, "Policy Rate"].median(),
                "hiring rate/q": sim["Hiring Rate"].mean(),
                "separation rate/q": sim["Separation Rate"].mean(),
                "worst unexplained money/GDP": accounts.loc["money.unexplained", "worst share of GDP"],
                "worst ledger residual/GDP": accounts.loc[
                    [c for c in accounts.index if c.startswith(("loans.", "deposits."))], "worst share of GDP"
                ]
                .abs()
                .max(),
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
            "CPI inflation/q": target["CPI Inflation"].iloc[: args.quarters].mean(),
            f"unemployment q{args.quarters}": target["Unemployment Rate"].iloc[args.quarters - 1],
        }
    ).reindex(summary.columns, fill_value=np.nan)
    summary.to_csv(out_dir / "summary.csv")
    pd.set_option("display.width", 250)
    print(summary.T.to_string(float_format=lambda x: f"{x:.3f}"))
    print(f"\nwritten to {out_dir.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
