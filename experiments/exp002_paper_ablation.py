"""exp002: How much of the gap to the paper is the configuration, not the code?

Starting from the defaults as they were with 5% price noise, switches on the paper's settings one at a time
(cumulatively) and scores each step with the exp001 scorecard. Paper values are
from the submitted manuscript: Table `table:prior` (NPE posterior, Austria),
eqs. `firm_exp_demand_main`, `firm_target_production_main`, `firm_prices`, and the
bank parameters in the appendix.

The settings themselves live in settings.py (see there for the chi mapping caveat).

Usage:
    uv run python experiments/exp002_paper_ablation.py [--seeds 5] [--quarters 12]

Writes to outputs/exp002_paper_ablation/:
    run.json, summary.csv (one row per step), series_<k>.csv, figure_<k>.png
"""

import argparse
import logging
import warnings

import numpy as np
import pandas as pd
from provenance import record_run
from scoring import COUNTRY, ROOT, START, load_data, observed, plot, scorecard, simulate
from settings import (
    growth_expectations,
    input_constraints,
    inventory,
    no_price_noise,
    old_price_noise,
    paper_bank_limits,
    taylor_rule,
)

from macromodel.configurations import CountryConfiguration

# (label, config change, needs many-firm data); applied cumulatively
# Inventory goes last. This experiment builds data with default settings, so the inventory step takes the broken
# re-initialisation path (S3) and diverges; exp004 builds matching data instead.
STEPS = [
    ("defaults with old 5% price noise", old_price_noise, False),
    ("+ growth expectations", growth_expectations, False),
    ("+ input constraints chi", input_constraints, False),
    ("+ no price noise", no_price_noise, False),
    ("+ paper bank limits", paper_bank_limits, False),
    ("+ Taylor rule", taylor_rule, False),
    ("+ many firms", None, True),
    ("+ inventory target", inventory, True),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--quarters", type=int, default=12)
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING)
    warnings.filterwarnings("ignore")
    out_dir = ROOT / "outputs" / "exp002_paper_ablation"
    record_run(out_dir, **vars(args), country=COUNTRY, start=START, steps=[s[0] for s in STEPS])

    data = {False: load_data(), True: None}
    obs = observed(data[False])
    country_config = CountryConfiguration()
    rows = []
    for k, (label, change, many_firms) in enumerate(STEPS):
        if change is not None:
            change(country_config)
        if many_firms and data[True] is None:
            data[True] = load_data(many_firms=True)
        try:
            runs = [
                simulate(data[many_firms], country_config.model_copy(deep=True), seed, args.quarters)
                for seed in range(args.seeds)
            ]
        except (ValueError, FloatingPointError) as error:
            print(f"[{k}] {label}: run diverged ({type(error).__name__}: {error})")
            rows.append({"step": label, "diverged": True})
            continue
        sim = pd.concat(runs, ignore_index=True)
        card = scorecard(sim, obs, args.quarters)
        sim.to_csv(out_dir / f"series_{k}.csv", index=False)
        plot(sim, obs, args.quarters, f"exp002 step {k}: {label}", out_dir / f"figure_{k}.png")

        unemployment_end = sim.loc[sim["t"] == sim["t"].max(), "Unemployment Rate"].median()
        rows.append(
            {
                "step": label,
                **{f"{agg} sim/AR1": card.loc[agg, "sim / AR(1)"] for agg in card.index if agg != "Unemployment Rate"},
                "GDP growth mean": card.loc["Real GDP", "sim mean"],
                "CPI inflation mean": card.loc["CPI Inflation", "sim mean"],
                "unemployment end (median)": unemployment_end,
                "diverged": False,
            }
        )
        print(f"[{k}] {label}: GDP sim/AR1 {rows[-1]['Real GDP sim/AR1']:.2f}, unemployment end {unemployment_end:.3f}")

    summary = pd.DataFrame(rows).set_index("step")
    data_row = {
        "GDP growth mean": obs.loc[obs.index > START, "Real GDP"].iloc[: args.quarters].mean(),
        "CPI inflation mean": obs.loc[obs.index > START, "CPI Inflation"].iloc[: args.quarters].mean(),
        "unemployment end (median)": obs.loc[obs.index > START, "Unemployment Rate"].iloc[args.quarters - 1],
    }
    summary.loc["data"] = pd.Series(data_row).reindex(summary.columns, fill_value=np.nan)
    summary.to_csv(out_dir / "summary.csv")
    pd.set_option("display.width", 250)
    print(summary.to_string(float_format=lambda x: f"{x:.3f}"))
    print(f"\nwritten to {out_dir.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
