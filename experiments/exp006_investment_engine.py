"""exp006: Does a flexible-accelerator investment rule give the economy a stable growth engine?

Starting from today's defaults (realistic initial wages, MD9), cumulatively:
  1  growth expectations (firms scale expected demand by the growth forecast)
  2  spare capacity (initial utilisation 0.85, built into the data and the simulation)
  3  investment engine: capital purchases = replacement + λ x (desired - current capital), planned on expected
     demand (PartialAdjustmentTargetCapitalInputsSetter), with λ = 0.25; λ = 0.1 and 0.5 as sensitivity
  4  dividends: other financial assets are shares in firms (MD6), so retained profits must fund investment

Usage:
    uv run python experiments/exp006_investment_engine.py [--seeds 5] [--quarters 20]

Writes to outputs/exp006_investment_engine/: run.json, summary.csv, series_<k>.csv, figure_<k>.png
"""

import argparse
import logging
import warnings
from functools import partial

import numpy as np
import pandas as pd
from provenance import record_run
from scoring import COUNTRY, ROOT, START, accounts_summary, load_data, observed, plot, scorecard, simulate
from settings import OMEGA, firm_shares, growth_expectations, investment_engine, spare_capacity

from macromodel.configurations import CountryConfiguration

# (label, list of config changes applied on top of defaults, initial utilisation built into the data)
ENGINE = [growth_expectations, spare_capacity]
STEPS = [
    ("defaults (realistic wages)", [], 1.0),
    ("+ growth expectations", [growth_expectations], 1.0),
    ("+ spare capacity 0.85", ENGINE, OMEGA),
    ("+ investment engine λ=0.10", ENGINE + [partial(investment_engine, adjustment_speed=0.10)], OMEGA),
    ("+ investment engine λ=0.25", ENGINE + [partial(investment_engine, adjustment_speed=0.25)], OMEGA),
    ("+ investment engine λ=0.50", ENGINE + [partial(investment_engine, adjustment_speed=0.50)], OMEGA),
    ("+ λ=0.25 + dividends", ENGINE + [partial(investment_engine, adjustment_speed=0.25), firm_shares], OMEGA),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--quarters", type=int, default=20)
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING)
    warnings.filterwarnings("ignore")
    out_dir = ROOT / "outputs" / "exp006_investment_engine"
    record_run(out_dir, **vars(args), country=COUNTRY, start=START, steps=[s[0] for s in STEPS])

    data = {u: load_data(utilisation_rate=u) for u in {u for *_, u in STEPS}}
    obs = observed(data[1.0])
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
        plot(sim, obs, scored, f"exp006 step {k}: {label}", out_dir / f"figure_{k}.png")
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
                f"unemployment q{args.quarters}": sim.loc[sim["t"] == args.quarters, "Unemployment Rate"].median(),
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
            f"unemployment q{args.quarters}": target["Unemployment Rate"].iloc[args.quarters - 1],
        }
    ).reindex(summary.columns, fill_value=np.nan)
    summary.to_csv(out_dir / "summary.csv")
    pd.set_option("display.width", 250)
    print(summary.T.to_string(float_format=lambda x: f"{x:.3f}"))
    print(f"\nwritten to {out_dir.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
