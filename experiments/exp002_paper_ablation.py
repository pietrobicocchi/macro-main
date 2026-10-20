"""exp002: How much of the gap to the paper is the configuration, not the code?

Starting from today's defaults, switches on the paper's settings one at a time
(cumulatively) and scores each step with the exp001 scorecard. Paper values are
from the submitted manuscript: Table `table:prior` (NPE posterior, Austria),
eqs. `firm_exp_demand_main`, `firm_target_production_main`, `firm_prices`, and the
bank parameters in the appendix.

Mapping caveat: the paper caps *target production* by chi^H, chi^M, chi^K. The code
instead caps labour demand and intermediate/capital purchases separately, so the
same chi values are applied to each of those targets.

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

from macromodel.configurations import CountryConfiguration

# Paper posterior (Table table:prior) and appendix bank parameters
PHI_STY, CHI_H, CHI_M, CHI_K = 0.10, 0.53, 0.03, 0.18


def growth_expectations(c: CountryConfiguration) -> None:
    # Q_f = (1 + gamma_s) (1 + phi^Q_F gamma_f) Q_f(t-1), with phi^Q_F = 0
    c.firms.functions.demand_estimator.parameters = {
        "firm_growth_adjustment_speed": 0.0,
        "sectoral_growth_adjustment_speed": 1.0,
    }


def inventory(c: CountryConfiguration) -> None:
    # Y_hat = Q_f + phi^StY Y_f(t-1) - S_f(t-1)
    p = c.firms.functions.target_production.parameters
    c.firms.functions.target_production.parameters = {
        **p,
        "existing_inventory_fraction": 1.0,
        "target_inventory_to_production_fraction": PHI_STY,
    }


def input_constraints(c: CountryConfiguration) -> None:
    p = c.firms.functions.target_production.parameters
    c.firms.functions.target_production.parameters = {
        **p,
        **{
            f"{target}_target_considers_{inputs}": weight
            for target in ["intermediate_inputs", "capital_inputs"]
            for inputs, weight in [("labour_inputs", CHI_H), ("intermediate_inputs", CHI_M), ("capital_inputs", CHI_K)]
        },
    }
    c.firms.functions.desired_labour.parameters = {
        "consider_intermediate_inputs": CHI_M,
        "consider_capital_inputs": CHI_K,
    }


def no_price_noise(c: CountryConfiguration) -> None:
    # eq. firm_prices has no noise term
    p = c.firms.functions.prices.parameters
    c.firms.functions.prices.parameters = {**p, "price_setting_noise_std": 0.0}


def paper_bank_limits(c: CountryConfiguration) -> None:
    b = c.banks.parameters
    b.firm_loans_debt_to_equity_ratio = 1.0
    b.firm_loans_return_on_equity_ratio = 0.15
    b.firm_loans_return_on_assets_ratio = 0.05
    b.household_consumption_loans_loan_to_income_ratio = 0.36


def taylor_rule(c: CountryConfiguration) -> None:
    c.central_bank.functions.policy_rate.name = "PolednaPolicyRate"


# (label, config change, needs many-firm data); applied cumulatively
# Inventory goes last: with initial inventories of about one quarter of output, the paper's rule
# (subtract all inventory) collapses production in quarter 1 and the run diverges.
STEPS = [
    ("today's defaults", None, False),
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
