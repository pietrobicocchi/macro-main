"""exp021: Can the government's spending plan track 2014-16 (gov. cons. ratio 1.90, the worst)?

The government plans real consumption as an AR(1) on the log level of its past consumption deflated by the PPI.
Hypothesis (recorded before running): two things make planned growth too low (0.10%/q against 0.34%/q): an AR(1)
on log levels mean-reverts, so planned growth fades, and the PPI fell with oil prices in 2014-16. Offline, from
pre-2014 data only: levels / PPI 1.69 x the AR(1) RMSE, levels / CPI 1.35, growth rates / PPI 1.29, growth rates /
CPI 1.03. Steps: defaults (MD15); log levels, CPI; growth rates, PPI; growth rates, CPI.

Usage:
    uv run python experiments/exp021_government_consumption.py [--seeds 10] [--quarters 20]

Writes to outputs/exp021_government_consumption/: run.json, summary.csv, series_<k>.csv, figure_<k>.png
"""

import argparse
import logging
import warnings
from functools import partial

import numpy as np
import pandas as pd
from provenance import record_run
from scoring import COUNTRY, ROOT, START, accounts_summary, load_data, observed, plot, scorecard, simulate
from settings import government_consumption_plan

from macromodel.configurations import CountryConfiguration

# (label, list of config changes applied on top of defaults, initial utilisation built into the data)
STEPS = [
    ("defaults", [], 0.85),
    ("log levels, CPI", [partial(government_consumption_plan, growth_rates=False, deflator="cpi")], 0.85),
    ("growth rates, PPI", [partial(government_consumption_plan, deflator="ppi")], 0.85),
    ("growth rates, CPI", [partial(government_consumption_plan, deflator="cpi")], 0.85),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--quarters", type=int, default=20)
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING)
    warnings.filterwarnings("ignore")
    out_dir = ROOT / "outputs" / "exp021_government_consumption"
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
        plot(sim, obs, scored, f"exp021 step {k}: {label}", out_dir / f"figure_{k}.png")
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
