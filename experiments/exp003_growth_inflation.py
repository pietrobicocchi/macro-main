"""exp003: Can the model grow, and where does its inflation come from?

Factorial over three switches on top of today's defaults (price noise 0.0005):
  growth   firms scale expected demand by the economy's growth forecast
           (sectoral_growth_adjustment_speed 0 -> 1; the paper always does)
  chi_K    how fully capital capacity caps labour demand and input purchases
           (today 1.0 everywhere -> paper posterior 0.18)
  fc_noise random draw added to the AR(1) growth/inflation forecasts each quarter
           (on by default -> off via assume_zero_noise)

Firms set prices as previous price x (1 + forecast PPI inflation), so realised
inflation is the forecast; forecast noise therefore enters inflation directly.

Usage:
    uv run python experiments/exp003_growth_inflation.py [--seeds 5] [--quarters 12]

Writes to outputs/exp003_growth_inflation/: run.json, summary.csv, series_<cell>.csv
"""

import argparse
import itertools
import logging
import warnings

import pandas as pd
from exp002_paper_ablation import CHI_K, growth_expectations
from provenance import record_run
from scoring import COUNTRY, ROOT, START, load_data, observed, scorecard, simulate

from macromodel.configurations import CountryConfiguration


def capital_constraint(c: CountryConfiguration, weight: float) -> None:
    p = c.firms.functions.target_production.parameters
    c.firms.functions.target_production.parameters = {
        **p,
        "intermediate_inputs_target_considers_capital_inputs": weight,
        "capital_inputs_target_considers_capital_inputs": weight,
    }
    d = c.firms.functions.desired_labour.parameters
    c.firms.functions.desired_labour.parameters = {**d, "consider_capital_inputs": weight}


def configure(growth: bool, chi_k: float, forecast_noise: bool) -> CountryConfiguration:
    c = CountryConfiguration()
    if growth:
        growth_expectations(c)
    capital_constraint(c, chi_k)
    c.assume_zero_noise = not forecast_noise
    return c


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--quarters", type=int, default=12)
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING)
    warnings.filterwarnings("ignore")
    out_dir = ROOT / "outputs" / "exp003_growth_inflation"
    record_run(out_dir, **vars(args), country=COUNTRY, start=START)

    data = load_data()
    obs = observed(data)
    target = obs.loc[obs.index > START].iloc[: args.quarters]
    rows = []
    for growth, chi_k, forecast_noise in itertools.product([False, True], [1.0, CHI_K], [True, False]):
        cell = f"growth{int(growth)}_chiK{chi_k}_fcnoise{int(forecast_noise)}"
        config = configure(growth, chi_k, forecast_noise)
        try:
            sim = pd.concat(
                [simulate(data, config.model_copy(deep=True), seed, args.quarters) for seed in range(args.seeds)],
                ignore_index=True,
            )
        except (ValueError, FloatingPointError) as error:
            print(f"{cell}: diverged ({type(error).__name__})")
            rows.append({"growth": growth, "chi_K": chi_k, "forecast noise": forecast_noise, "diverged": True})
            continue
        sim.to_csv(out_dir / f"series_{cell}.csv", index=False)
        card = scorecard(sim, obs, args.quarters)
        rows.append(
            {
                "growth": growth,
                "chi_K": chi_k,
                "forecast noise": forecast_noise,
                **{f"{agg} sim/AR1": card.loc[agg, "sim / AR(1)"] for agg in card.index if agg != "Unemployment Rate"},
                "GDP growth mean": card.loc["Real GDP", "sim mean"],
                "investment growth mean": card.loc["Real Investment", "sim mean"],
                "CPI inflation mean": card.loc["CPI Inflation", "sim mean"],
                "unemployment end (median)": sim.loc[sim["t"] == args.quarters, "Unemployment Rate"].median(),
                "diverged": False,
            }
        )
        print(f"{cell}: GDP sim/AR1 {rows[-1]['Real GDP sim/AR1']:.2f}, GDP growth {rows[-1]['GDP growth mean']:+.4f}")

    summary = pd.DataFrame(rows)
    summary.to_csv(out_dir / "summary.csv", index=False)
    pd.set_option("display.width", 250)
    print(summary.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print(
        f"\ndata: GDP growth {target['Real GDP'].mean():+.4f}, investment growth {target['Real Investment'].mean():+.4f}, "
        f"CPI inflation {target['CPI Inflation'].mean():+.4f}, unemployment end {target['Unemployment Rate'].iloc[-1]:.3f}"
    )
    print(f"written to {out_dir.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
