"""Shared simulate-and-score routine for experiments.

Runs France initialised in 2014-Q1 on the bundled sample data and scores quarterly
growth rates against the observed French series with the paper's metric: the median
over seeds of the per-trajectory RMSE, alongside an AR(1) benchmark fit on pre-2014 data.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from macro_data import DataWrapper
from macro_data.configuration_utils import default_data_configuration
from macromodel.accounting import AccountingMonitor
from macromodel.configurations import CountryConfiguration, SimulationConfiguration
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
SCORED = [*AGGREGATES, "CPI Inflation", "Unemployment Rate"]


def load_data(
    scale: int = 10_000, many_firms: bool = False, utilisation_rate: float = 1.0, inventory_fraction: float = 0.0
) -> DataWrapper:
    """France 2014 initial state. many_firms uses business-demography firm counts instead of one per industry.

    utilisation_rate and inventory_fraction size the initial input stocks and inventory. Build the data with the
    values the simulation will use: if they differ, Simulation.from_datawrapper re-runs the financial
    initialisation, which double-counts bank deposits (see PROJECT.md).
    """
    configuration = default_data_configuration(countries=[COUNTRY], seed=0, scale=scale)
    # default_data_configuration ignores its single_firm_per_industry argument; the per-country flag is what counts
    for country_configuration in configuration.country_configs.values():
        country_configuration.single_firm_per_industry = not many_firms
        firms = country_configuration.firms_configuration
        firms.capital_inputs_utilisation_rate = utilisation_rate
        firms.intermediate_inputs_utilisation_rate = utilisation_rate
        firms.initial_inventory_to_input_fraction = inventory_fraction
    return DataWrapper.from_config(configuration=configuration, raw_data_path=RAW_DATA, single_hfcs_survey=True)


def simulate(
    data: DataWrapper,
    country_config: CountryConfiguration,
    seed: int,
    quarters: int,
    audit: list[pd.DataFrame] | None = None,
) -> pd.DataFrame:
    """One run; returns quarterly real growth rates, CPI inflation, unemployment and policy rate for t = 1..quarters.

    If `audit` is a list, the run's accounting report (macromodel.accounting) is appended to it.
    """
    sim = Simulation.from_datawrapper(
        datawrapper=data,
        simulation_configuration=SimulationConfiguration(
            country_configurations={COUNTRY: country_config}, t_max=quarters, seed=seed
        ),
    )
    monitor = AccountingMonitor()
    monitor.record(sim, t=-1)
    sim.posthooks.append(monitor)
    sim.run()
    if audit is not None:
        audit.append(monitor.report().assign(seed=seed))
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
    for agg in SCORED:
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


def plot(sim: pd.DataFrame, obs: pd.DataFrame, quarters: int, title: str, path: Path) -> None:
    target = obs.loc[obs.index > START].iloc[:quarters]
    fig, axes = plt.subplots(2, 3, figsize=(14, 7), sharex=True)
    for ax, agg in zip(axes.flat, SCORED):
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
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def accounts_summary(audit: list[pd.DataFrame]) -> pd.DataFrame:
    """Worst residual of each accounting check over all seeds and periods, as a share of quarterly GDP."""
    report = pd.concat(audit, ignore_index=True)
    worst = report.loc[report.groupby("check")["share_of_gdp"].apply(lambda s: s.abs().idxmax())]
    return worst.set_index("check")[["share_of_gdp", "t", "seed"]].rename(
        columns={"share_of_gdp": "worst share of GDP"}
    )
