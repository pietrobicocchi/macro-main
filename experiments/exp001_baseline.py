"""exp001: Does the default model produce plausible macro dynamics?

Runs France initialised in 2014-Q1 (bundled sample data: real national accounts,
spoofed HFCS/Compustat micro-data) with default parameters, several seeds, and
scores quarterly growth rates against the observed French series using the
paper's metric (median over seeds of the per-trajectory RMSE) alongside an
AR(1) benchmark fit on pre-2014 data.

Usage:
    uv run python experiments/exp001_baseline.py [--seeds 10] [--quarters 12] [--scale 10000] [--policy ConstantPolicyRate]

Writes to outputs/exp001_baseline/<policy>_scale<scale>/:
    run.json       commit, dirty files, command line, parameters
    series.csv     simulated quarterly growth rates, one row per (seed, t)
    scorecard.csv  per-aggregate comparison against data and AR(1)
    figure.png     simulated paths vs data
"""

import argparse
import logging
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from provenance import record_run

from macro_data import DataWrapper
from macro_data.configuration_utils import default_data_configuration
from macromodel.configurations import CountryConfiguration, SimulationConfiguration
from macromodel.configurations.central_bank_configuration import (
    CentralBankConfiguration,
    CentralBankFunctions,
    CentralBankPolicy,
)
from macromodel.simulation import Simulation

ROOT = Path(__file__).resolve().parents[1]
RAW_DATA = ROOT / "tests/test_macro_data/unit/sample_raw_data"
COUNTRY = "FRA"
START = pd.Timestamp("2014-01-01")
AR1_FIT_START = pd.Timestamp("2000-07-01")

# aggregate -> (simulated nominal series, deflator, observed nominal column).
# Model and data are deflated the same way (nominal / price index) so the comparison is like-for-like.
AGGREGATES = {
    "Real GDP": ("gdp_output", "ppi", "GDP"),
    "Real Household Cons.": ("total_household_fce", "cpi", "Household Consumption"),
    "Real Government Cons.": ("total_government_fce", "cpi", "Government Consumption"),
    "Real Investment": ("total_gross_fixed_capital_formation", "ppi", "Gross Fixed Capital Formation"),
}


def run_one(data: DataWrapper, seed: int, quarters: int, policy: str) -> pd.DataFrame:
    country_config = CountryConfiguration(
        central_bank=CentralBankConfiguration(
            functions=CentralBankFunctions(policy_rate=CentralBankPolicy(name=policy))
        )
    )
    sim = Simulation.from_datawrapper(
        datawrapper=data,
        simulation_configuration=SimulationConfiguration(
            country_configurations={COUNTRY: country_config}, t_max=quarters, seed=seed
        ),
    )
    sim.run()
    country = sim.countries[COUNTRY]
    ts = country.economy.ts

    def series(name: str) -> np.ndarray:
        return np.asarray(ts.get_aggregate(name), dtype=float).ravel()

    out = {}
    for agg, (nominal, deflator, _) in AGGREGATES.items():
        real = series(nominal) / series(deflator)
        out[agg] = real[1:] / real[:-1] - 1.0
    out["CPI Inflation"] = series("cpi")[1:] / series("cpi")[:-1] - 1.0
    out["Unemployment Rate"] = np.asarray(country.economy.unemployment_rate(), dtype=float).ravel()[1:]
    out["Policy Rate"] = np.asarray(country.central_bank.ts.get_aggregate("policy_rate"), dtype=float).ravel()[1:]
    n = min(len(v) for v in out.values())
    df = pd.DataFrame({k: v[:n] for k, v in out.items()})
    df.insert(0, "t", np.arange(1, n + 1))
    df.insert(0, "seed", seed)
    return df


def observed(data: DataWrapper) -> pd.DataFrame:
    ex = data.synthetic_countries[COUNTRY].exogenous_data
    na = ex.national_accounts
    obs = pd.DataFrame(index=na.index)
    for agg, (_, deflator, col) in AGGREGATES.items():
        real = na[f"{col} (Value)"] / na[f"{deflator.upper()} (Value)"]
        obs[agg] = real / real.shift(1) - 1.0
    obs["CPI Inflation"] = na["CPI (Value)"] / na["CPI (Value)"].shift(1) - 1.0
    obs["Unemployment Rate"] = ex.labour_stats["Unemployment Rate (Value)"].reindex(obs.index)
    return obs


def ar1_forecast(history: pd.Series, horizon: int) -> np.ndarray:
    """Iterated multi-step AR(1) forecast with intercept, fit by OLS."""
    y = history.dropna().to_numpy()
    slope, intercept = np.polyfit(y[:-1], y[1:], 1)
    preds, last = [], y[-1]
    for _ in range(horizon):
        last = intercept + slope * last
        preds.append(last)
    return np.array(preds)


def scorecard(sim: pd.DataFrame, obs: pd.DataFrame, quarters: int) -> pd.DataFrame:
    # sim t=1 is the first simulated quarter after initialisation, i.e. START itself is t=0
    target = obs.loc[obs.index > START].iloc[:quarters]
    history = obs.loc[(obs.index >= AR1_FIT_START) & (obs.index <= START)]
    rows = []
    for agg in [*AGGREGATES, "CPI Inflation", "Unemployment Rate"]:
        y = target[agg].to_numpy()
        paths = sim.pivot(index="t", columns="seed", values=agg).to_numpy()[: len(y)]
        rmse_by_seed = np.sqrt(np.nanmean((paths - y[:, None]) ** 2, axis=0))
        row = {
            "aggregate": agg,
            "data mean": np.nanmean(y),
            "sim mean": np.nanmean(paths),
            "sim std across seeds": np.nanstd(paths.mean(axis=0)),
            "sim RMSE (median seed)": np.median(rmse_by_seed),
        }
        if agg != "Unemployment Rate":
            ar1 = ar1_forecast(history[agg], len(y))
            row["AR(1) RMSE"] = np.sqrt(np.nanmean((ar1 - y) ** 2))
            row["sim / AR(1)"] = row["sim RMSE (median seed)"] / row["AR(1) RMSE"]
        rows.append(row)
    return pd.DataFrame(rows).set_index("aggregate")


def plot(sim: pd.DataFrame, obs: pd.DataFrame, quarters: int, scale: int, path: Path) -> None:
    target = obs.loc[obs.index > START].iloc[:quarters]
    cols = [*AGGREGATES, "CPI Inflation", "Unemployment Rate"]
    fig, axes = plt.subplots(2, 3, figsize=(14, 7), sharex=True)
    for ax, agg in zip(axes.flat, cols):
        paths = sim.pivot(index="t", columns="seed", values=agg)
        ax.plot(paths.index, paths.values, color="tab:blue", alpha=0.25, lw=0.8)
        ax.plot(paths.index, paths.median(axis=1), color="tab:blue", lw=2, label="model (median)")
        ax.plot(np.arange(1, len(target) + 1), target[agg].values, color="black", lw=2, label="data")
        ax.axhline(0, color="grey", lw=0.5)
        ax.set_title(agg)
        ax.grid(alpha=0.3)
    axes.flat[0].legend()
    for ax in axes[-1]:
        ax.set_xlabel(f"quarters after {START.date()}")
    fig.suptitle(f"exp001 baseline — {COUNTRY}, default parameters, scale {scale} (quarterly rates)")
    fig.tight_layout()
    fig.savefig(path, dpi=120)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--quarters", type=int, default=12)
    parser.add_argument("--scale", type=int, default=10_000, help="real-world agents per model agent")
    parser.add_argument("--policy", default="ConstantPolicyRate", choices=["ConstantPolicyRate", "PolednaPolicyRate"])
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING)
    warnings.filterwarnings("ignore")
    out_dir = ROOT / "outputs" / "exp001_baseline" / f"{args.policy}_scale{args.scale}"
    record_run(out_dir, **vars(args), country=COUNTRY, start=START, raw_data=RAW_DATA)

    data = DataWrapper.from_config(
        configuration=default_data_configuration(countries=[COUNTRY], seed=0, scale=args.scale),
        raw_data_path=RAW_DATA,
        single_hfcs_survey=True,
    )
    sim = pd.concat([run_one(data, seed, args.quarters, args.policy) for seed in range(args.seeds)], ignore_index=True)
    obs = observed(data)

    card = scorecard(sim, obs, args.quarters)
    sim.to_csv(out_dir / "series.csv", index=False)
    card.to_csv(out_dir / "scorecard.csv")
    plot(sim, obs, args.quarters, args.scale, out_dir / "figure.png")

    pd.set_option("display.width", 200)
    print(
        f"{COUNTRY} from {START.date()}, {args.seeds} seeds x {args.quarters} quarters, scale={args.scale}, policy={args.policy}"
    )
    print(card.to_string(float_format=lambda x: f"{x:.4f}"))
    print(f"\nwritten to {out_dir.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
