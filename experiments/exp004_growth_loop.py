"""exp004: Does the paper's capacity setup let the growth loop run?

exp003 found production pinned at capital capacity in every firm: initial stocks
are sized for full utilisation and capital purchases only replace depreciation.
The paper (appendix, around eq. firm_target_capital_inputs) starts firms with
spare capacity (omega^K = omega^M = 0.85) and tops up stocks that fall below their
initial ratio to output (phi^K = phi^M = 1). This adds the paper's growth
machinery cumulatively to today's defaults, with forecast noise on as in the
paper's runs, and switches forecast noise off as a final step.

Usage:
    uv run python experiments/exp004_growth_loop.py [--seeds 5] [--quarters 12]

Writes to outputs/exp004_growth_loop/: run.json, summary.csv, series_<k>.csv, figure_<k>.png
"""

import argparse
import logging
import warnings

import numpy as np
import pandas as pd
from exp002_paper_ablation import growth_expectations, input_constraints, inventory
from provenance import record_run
from scoring import COUNTRY, ROOT, START, load_data, observed, plot, scorecard, simulate

from macromodel.configurations import CountryConfiguration

OMEGA, PHI_STOCK = 0.85, 1.0  # paper appendix: initial utilisation rates, stock top-up weights


def spare_capacity(c: CountryConfiguration) -> None:
    c.firms.parameters.capital_inputs_utilisation_rate = OMEGA
    c.firms.parameters.intermediate_inputs_utilisation_rate = OMEGA


def stock_top_up(c: CountryConfiguration) -> None:
    k = c.firms.functions.target_capital_inputs.parameters
    c.firms.functions.target_capital_inputs.parameters = {**k, "target_capital_inputs_fraction": PHI_STOCK}
    m = c.firms.functions.target_intermediate_inputs.parameters
    c.firms.functions.target_intermediate_inputs.parameters = {**m, "target_intermediate_inputs_fraction": PHI_STOCK}


def no_forecast_noise(c: CountryConfiguration) -> None:
    c.assume_zero_noise = True


# (label, config change, needs many-firm data); applied cumulatively
STEPS = [
    ("today's defaults", None, False),
    ("+ growth expectations", growth_expectations, False),
    ("+ spare capacity (omega 0.85)", spare_capacity, False),
    ("+ stock top-up (phi^K = phi^M = 1)", stock_top_up, False),
    ("+ input constraints chi", input_constraints, False),
    ("+ inventory target", inventory, False),
    ("+ many firms", None, True),
    ("+ no forecast noise", no_forecast_noise, True),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--quarters", type=int, default=12)
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING)
    warnings.filterwarnings("ignore")
    out_dir = ROOT / "outputs" / "exp004_growth_loop"
    record_run(out_dir, **vars(args), country=COUNTRY, start=START, steps=[s[0] for s in STEPS])

    # Initial stocks are built into the data, so each (firms, utilisation, inventory) setting gets its own
    # data object matching the simulation config (a mismatch triggers the broken re-initialisation path)
    cache = {}

    def data_for(c: CountryConfiguration, many_firms: bool):
        key = (
            many_firms,
            c.firms.parameters.capital_inputs_utilisation_rate,
            c.firms.functions.target_production.parameters["target_inventory_to_production_fraction"],
        )
        if key not in cache:
            cache[key] = load_data(many_firms=key[0], utilisation_rate=key[1], inventory_fraction=key[2])
        return cache[key]

    obs = observed(load_data())
    target = obs.loc[obs.index > START].iloc[: args.quarters]
    country_config = CountryConfiguration()
    rows = []
    for k, (label, change, many_firms) in enumerate(STEPS):
        if change is not None:
            change(country_config)
        data = data_for(country_config, many_firms)
        try:
            runs = [
                simulate(data, country_config.model_copy(deep=True), seed, args.quarters) for seed in range(args.seeds)
            ]
        except (ValueError, FloatingPointError) as error:
            print(f"[{k}] {label}: run diverged ({type(error).__name__}: {error})")
            rows.append({"step": label, "diverged": True})
            continue
        sim = pd.concat(runs, ignore_index=True)
        card = scorecard(sim, obs, args.quarters)
        sim.to_csv(out_dir / f"series_{k}.csv", index=False)
        plot(sim, obs, args.quarters, f"exp004 step {k}: {label}", out_dir / f"figure_{k}.png")
        unemployment_end = sim.loc[sim["t"] == sim["t"].max(), "Unemployment Rate"].median()
        rows.append(
            {
                "step": label,
                **{f"{agg} sim/AR1": card.loc[agg, "sim / AR(1)"] for agg in card.index if agg != "Unemployment Rate"},
                "GDP growth mean": card.loc["Real GDP", "sim mean"],
                "investment growth mean": card.loc["Real Investment", "sim mean"],
                "CPI inflation mean": card.loc["CPI Inflation", "sim mean"],
                "unemployment end (median)": unemployment_end,
                "diverged": False,
            }
        )
        print(
            f"[{k}] {label}: GDP sim/AR1 {rows[-1]['Real GDP sim/AR1']:.2f}, GDP growth {rows[-1]['GDP growth mean']:+.4f}"
        )

    summary = pd.DataFrame(rows).set_index("step")
    data_row = {
        "GDP growth mean": target["Real GDP"].mean(),
        "investment growth mean": target["Real Investment"].mean(),
        "CPI inflation mean": target["CPI Inflation"].mean(),
        "unemployment end (median)": target["Unemployment Rate"].iloc[-1],
    }
    summary.loc["data"] = pd.Series(data_row).reindex(summary.columns, fill_value=np.nan)
    summary.to_csv(out_dir / "summary.csv")
    pd.set_option("display.width", 250)
    print(summary.to_string(float_format=lambda x: f"{x:.3f}"))
    print(f"\nwritten to {out_dir.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
