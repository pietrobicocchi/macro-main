"""exp005: Do realistic initial wages give firms realistic profits, and can profits pay households?

Today's initial state sets wages to value added minus investment (labour share 85%, France's is about 59%), so
firms start with no operating profit (S2) and households receive income on financial assets that nobody pays (S9).
Variants:
  A  today's defaults
  B  wages from the SEA labour share of value added (labour_share_from_sea)
  C  B, and households' other financial assets are shares in firms paying dividends (FirmSharesFinancialAssets)

Usage:
    uv run python experiments/exp005_firm_profits.py [--seeds 5] [--quarters 20]

Writes to outputs/exp005_firm_profits/: run.json, summary.csv, paths.csv, series_<variant>.csv, figure_<variant>.png
"""

import argparse
import logging
import warnings

import numpy as np
import pandas as pd
from provenance import record_run
from scoring import COUNTRY, ROOT, START, accounts_summary, load_data, observed, plot, scorecard, simulate

from macromodel.configurations import CountryConfiguration, SimulationConfiguration
from macromodel.simulation import Simulation


def firm_shares(c: CountryConfiguration) -> None:
    c.households.functions.financial_assets.name = "FirmSharesFinancialAssets"


VARIANTS = {
    "A_today": (False, None),
    "B_sea_wages": (True, None),
    "C_sea_wages_firm_shares": (True, firm_shares),
}


def income_paths(data, config: CountryConfiguration, seed: int, quarters: int) -> pd.DataFrame:
    """Quarterly totals for firms' profits, dividends and household income components (one seed)."""
    sim = Simulation.from_datawrapper(
        datawrapper=data,
        simulation_configuration=SimulationConfiguration(
            country_configurations={COUNTRY: config}, t_max=quarters, seed=seed
        ),
    )
    country = sim.countries[COUNTRY]
    rows = []
    for t in range(quarters):
        sim.iterate(t)
        f, h, e = country.firms.ts, country.households.ts, country.economy.ts

        def total(ts, key):
            return float(np.sum(ts.current(key)))

        gdp = total(e, "gdp_output")
        rows.append(
            {
                "t": t + 1,
                "firm profits / GDP": total(f, "profits") / gdp,
                "wages / GDP": total(f, "total_wage") / gdp,
                "household financial income / GDP": total(h, "income_financial_assets") / gdp,
                "household income / GDP": total(h, "income") / gdp,
                "household consumption / GDP": total(h, "total_consumption") / gdp,
                "nominal GDP (bn)": gdp / 1e9,
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--quarters", type=int, default=20)
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING)
    warnings.filterwarnings("ignore")
    out_dir = ROOT / "outputs" / "exp005_firm_profits"
    record_run(out_dir, **vars(args), country=COUNTRY, start=START, variants=list(VARIANTS))

    data = {flag: load_data(labour_share_from_sea=flag) for flag in {f for f, _ in VARIANTS.values()}}
    obs = observed(data[False])
    scored_quarters = min(12, args.quarters)
    rows, paths = [], []
    for name, (sea_wages, change) in VARIANTS.items():
        config = CountryConfiguration()
        if change is not None:
            change(config)
        audit = []
        sim = pd.concat(
            [
                simulate(data[sea_wages], config.model_copy(deep=True), s, args.quarters, audit)
                for s in range(args.seeds)
            ],
            ignore_index=True,
        )
        sim.to_csv(out_dir / f"series_{name}.csv", index=False)
        plot(sim, obs, scored_quarters, f"exp005 {name}", out_dir / f"figure_{name}.png")
        card = scorecard(sim[sim["t"] <= scored_quarters], obs, scored_quarters)
        accounts = accounts_summary(audit)
        path = income_paths(data[sea_wages], config.model_copy(deep=True), 0, args.quarters).assign(variant=name)
        paths.append(path)
        last = sim[sim["t"] == args.quarters]
        rows.append(
            {
                "variant": name,
                **{f"{agg} sim/AR1": card.loc[agg, "sim / AR(1)"] for agg in card.index if agg != "Unemployment Rate"},
                "GDP growth mean (12q)": card.loc["Real GDP", "sim mean"],
                f"GDP growth mean ({args.quarters}q)": sim["Real GDP"].mean(),
                f"unemployment at q{args.quarters}": last["Unemployment Rate"].median(),
                "firm profits / GDP (avg)": path["firm profits / GDP"].mean(),
                "wages / GDP (avg)": path["wages / GDP"].mean(),
                "household financial income / GDP (avg)": path["household financial income / GDP"].mean(),
                "household consumption / GDP (avg)": path["household consumption / GDP"].mean(),
                "worst unexplained money / GDP": accounts.loc["money.unexplained", "worst share of GDP"],
            }
        )
        print(
            f"{name}: GDP sim/AR1 {rows[-1]['Real GDP sim/AR1']:.2f}, profits/GDP {rows[-1]['firm profits / GDP (avg)']:.3f}"
        )

    summary = pd.DataFrame(rows).set_index("variant")
    summary.to_csv(out_dir / "summary.csv")
    pd.concat(paths, ignore_index=True).to_csv(out_dir / "paths.csv", index=False)
    pd.set_option("display.width", 250)
    print(summary.T.to_string(float_format=lambda x: f"{x:.3f}"))
    print(f"\nwritten to {out_dir.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
