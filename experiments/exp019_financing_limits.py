"""exp019: Do financing limits with realistic bank lending limits tame the growth engine's investment? (G9)

Candidate B's investment forecast is poor (exp017, exp018): investment bursts early and grows 1.1%/q (data 0.8%).
Capital purchases are not limited by financing (`credit_gap_fraction` 0); switching that on with today's bank limits
(firm debt/equity 0.03) caused a recession (exp008). Here B with the paper's bank limits (debt/equity 1.0), then with
capital purchases cut by half or all of the long-term credit applied for but not received.

Usage:
    uv run python experiments/exp019_financing_limits.py [--seeds 10] [--quarters 20]

Writes to outputs/exp019_financing_limits/: run.json, summary.csv, series_<k>.csv, figure_<k>.png
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
    paper_bank_limits,
    search_frictions,
    spare_capacity,
)

from macromodel.configurations import CountryConfiguration

FRICTIONS = [search_frictions]
PRODUCTIVITY = [partial(labour_productivity_growth, rate=0.0025)]
SLACK = [partial(growth_forecast_slack_aware, sensitivity=0.2)]


def b(credit_gap_fraction: float = 0.0, bank_limits: bool = False) -> list:
    engine = partial(
        investment_engine, adjustment_speed=0.25, demand_smoothing=0.10, credit_gap_fraction=credit_gap_fraction
    )
    return [growth_expectations, engine, spare_capacity, *FRICTIONS, *PRODUCTIVITY, *SLACK] + (
        [paper_bank_limits] if bank_limits else []
    )


# (label, list of config changes applied on top of defaults, initial utilisation built into the data)
STEPS = [
    ("B", b(), OMEGA),
    ("B, paper bank limits", b(bank_limits=True), OMEGA),
    ("B, paper bank limits, credit gap 0.5", b(0.5, bank_limits=True), OMEGA),
    ("B, paper bank limits, credit gap 1", b(1.0, bank_limits=True), OMEGA),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--quarters", type=int, default=20)
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING)
    warnings.filterwarnings("ignore")
    out_dir = ROOT / "outputs" / "exp019_financing_limits"
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
        plot(sim, obs, scored, f"exp019 step {k}: {label}", out_dir / f"figure_{k}.png")
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
