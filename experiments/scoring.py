"""Shared simulate-and-score routine for experiments.

Runs France initialised in 2014-Q1 on the bundled sample data and scores quarterly
growth rates against the observed French series with the paper's metric: the median
over seeds of the per-trajectory RMSE, alongside an AR(1) benchmark fit on pre-2014 data.
"""

import argparse
import logging
import os
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from macro_data import DataWrapper
from macro_data.configuration_utils import default_data_configuration
from macromodel.accounting import AccountingMonitor, snapshot
from macromodel.configurations import CountryConfiguration, SimulationConfiguration
from macromodel.configurations.row_configuration import RestOfTheWorldConfiguration
from macromodel.simulation import Simulation

ROOT = Path(__file__).resolve().parents[1]
# The test sample by default; MACRO_RAW_DATA=<datasets>/macro_raw_data for the full public data
# (experiments/public_data.py: still the spoofed HFCS and Compustat, D1)
RAW_DATA = Path(os.environ.get("MACRO_RAW_DATA", ROOT / "tests/test_macro_data/unit/sample_raw_data")).expanduser()
COUNTRY = "FRA"
GEO = "FR"  # Eurostat's code for COUNTRY
START = pd.Timestamp("2014-01-01")
AR1_FIT_START = pd.Timestamp("2000-07-01")

# aggregate -> (simulated nominal series, deflator, observed nominal column, Eurostat volume item).
# The model's volumes are its nominal series over its own price index (one price per good). The data's are Eurostat
# chain-linked volumes (R4): nominal / PPI in the data overstates real GDP growth (0.64%/q against 0.28%/q in 2014-16).
AGGREGATES = {
    "Real GDP": ("gdp_output", "ppi", "GDP", "B1GQ"),
    "Real Household Cons.": ("total_household_fce", "cpi", "Household Consumption", "P31_S14_S15"),
    "Real Government Cons.": ("total_government_fce", "cpi", "Government Consumption", "P3_S13"),
    "Real Investment": ("total_gross_fixed_capital_formation", "ppi", "Gross Fixed Capital Formation", "P51G"),
}
# France, chain-linked volumes (2010 euros), seasonally and calendar adjusted; downloaded 2026-10-21 from
# https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/namq_10_gdp/Q.CLV10_MEUR.SCA.B1GQ+P31_S14_S15+P31_S14+P3_S13+P51G.FR/?format=SDMX-CSV&startPeriod=1999-Q1&endPeriod=2019-Q4
VOLUMES = RAW_DATA / "eurostat/namq_10_gdp_clv.csv"
# Seasonally adjusted alternatives for the CPI and unemployment targets (R7), downloaded 2026-10-22: the household
# consumption deflator (namq_10_gdp, PD10_EUR, SCA, P31_S14_S15) and quarterly unemployment (une_rt_q, SA, 15-74)
DEFLATORS = RAW_DATA / "eurostat/namq_10_gdp_deflators.csv"
UNEMPLOYMENT = RAW_DATA / "eurostat/une_rt_q.csv"
SCORED = [*AGGREGATES, "CPI Inflation", "Unemployment Rate"]


def load_data(
    scale: int = 10_000,
    many_firms: bool = False,
    utilisation_rate: float = 0.85,
    inventory_fraction: float = 0.0,
    labour_share_from_sea: bool = True,
    cash_social_benefits: bool = True,
) -> DataWrapper:
    """France 2014 initial state. many_firms uses business-demography firm counts instead of one per industry.

    labour_share_from_sea sets initial wages from the SEA labour share (S2) instead of value added minus investment.
    utilisation_rate and inventory_fraction size the initial input stocks and inventory. Build the data with the
    values the simulation will use: if they differ, Simulation.from_datawrapper re-runs the financial
    initialisation, which double-counts bank deposits (see PROJECT.md).
    """
    configuration = default_data_configuration(countries=[COUNTRY], seed=0, scale=scale)
    configuration.labour_share_from_sea = labour_share_from_sea
    configuration.cash_social_benefits = cash_social_benefits
    # default_data_configuration ignores its single_firm_per_industry argument; the per-country flag is what counts
    for country_configuration in configuration.country_configs.values():
        country_configuration.single_firm_per_industry = not many_firms
        firms = country_configuration.firms_configuration
        firms.capital_inputs_utilisation_rate = utilisation_rate
        firms.intermediate_inputs_utilisation_rate = utilisation_rate
        firms.initial_inventory_to_input_fraction = inventory_fraction
    return DataWrapper.from_config(configuration=configuration, raw_data_path=RAW_DATA, single_hfcs_survey=True)


def _mechanisms(country) -> dict[str, float]:
    """What the economy is doing inside, at the end of a quarter: the series of the mechanism dashboard."""
    firms, economy, government = country.firms.ts, country.economy.ts, country.government_entities.ts
    books = snapshot(country)
    production = np.asarray(firms.current("production"), dtype=float)
    capacity = np.minimum(firms.current("limiting_capital_inputs"), firms.current("limiting_intermediate_inputs"))
    costs = np.asarray(firms.current("unit_costs"), dtype=float) * production
    employed = np.sum(country.individuals.states["Corresponding Firm ID"] >= 0)
    return {
        "gdp_lcu": books["gdp"],
        "households_net_financial_position": books["household_deposits"]
        - books["household_consumption_debt"]
        - books["household_mortgage_debt"],
        "firms_net_financial_position": books["firm_deposits"] - books["firm_debt"],
        "government_net_financial_position": -books["government_debt"],
        "banks_net_financial_position": books["bank_equity"],
        "capacity_utilisation": production.sum() / max(np.sum(capacity), 1e-12),
        "investment_rate": float(np.sum(firms.current("gross_fixed_capital_formation")))
        / max(float(np.sum(firms.current("capital_inputs_stock_value"))), 1e-12),
        "markup": float(np.sum(np.asarray(firms.current("price")) * production)) / max(float(costs.sum()), 1e-12) - 1,
        "nominal_wage_per_worker": float(np.sum(firms.current("total_wage"))) / max(employed, 1),
        "cpi": float(economy.current("cpi")[0]),
        "expected_growth": float(economy.current("estimated_growth")[0]),
        "expected_inflation": float(economy.current("estimated_cpi_inflation")[0]),
        "government_spending_fulfilment": float(np.sum(government.current("consumption_in_lcu")))
        / max(float(np.sum(government.current("desired_consumption_in_lcu"))), 1e-12),
    }


def simulate(
    data: DataWrapper,
    country_config: CountryConfiguration,
    seed: int,
    quarters: int,
    audit: list[pd.DataFrame] | None = None,
    row_config: RestOfTheWorldConfiguration | None = None,
) -> pd.DataFrame:
    """One run; returns quarterly real growth rates, CPI inflation, unemployment, policy rate and labour flows (hires
    and separations as shares of employment) for t = 1..quarters.

    If `audit` is a list, the run's accounting report (macromodel.accounting) is appended to it.
    """
    sim = Simulation.from_datawrapper(
        datawrapper=data,
        simulation_configuration=SimulationConfiguration(
            country_configurations={COUNTRY: country_config},
            row_configuration=row_config or RestOfTheWorldConfiguration(),
            t_max=quarters,
            seed=seed,
        ),
    )
    monitor = AccountingMonitor()
    monitor.record(sim, t=-1)
    mechanisms = [_mechanisms(sim.countries[COUNTRY])]
    sim.posthooks.append(monitor)
    sim.posthooks.append(lambda simulation, *_: mechanisms.append(_mechanisms(simulation.countries[COUNTRY])))
    sim.run()
    report = monitor.report()
    if audit is not None:
        audit.append(report.assign(seed=seed))
    country = sim.countries[COUNTRY]
    ts = country.economy.ts

    def series(name: str) -> np.ndarray:
        return np.asarray(ts.get_aggregate(name), dtype=float).ravel()

    out = {}
    for agg, (nominal, deflator, *_) in AGGREGATES.items():
        real = series(nominal) / series(deflator)
        out[agg] = real[1:] / real[:-1] - 1.0
    out["CPI Inflation"] = series("cpi")[1:] / series("cpi")[:-1] - 1.0
    out["Unemployment Rate"] = np.asarray(country.economy.unemployment_rate(), dtype=float).ravel()[1:]
    out["Policy Rate"] = np.asarray(country.central_bank.ts.get_aggregate("policy_rate"), dtype=float).ravel()[1:]
    labour = country.labour_market.ts
    employed = np.asarray(labour.get_aggregate("num_employed_individuals_before_clearing"), dtype=float).ravel()[1:]
    for flow, name in [
        ("Hiring Rate", "num_individuals_newly_joining"),
        ("Separation Rate", "num_individuals_newly_leaving"),
    ]:
        out[flow] = np.asarray(labour.get_aggregate(name), dtype=float).ravel()[1:] / employed
    # Mechanism dashboard: levels at the end of each quarter, and each sector's net lending (the change in its net
    # financial position) as a share of quarterly GDP; the rest of the world is minus the sum by stock-flow identity
    inside = pd.DataFrame(mechanisms)
    for sector in ["households", "firms", "government", "banks"]:
        position = inside[f"{sector}_net_financial_position"].to_numpy()
        out[f"net lending: {sector}"] = np.diff(position) / inside["gdp_lcu"].to_numpy()[1:]
    # The residual sector: the rest of the world, plus any flow the books above do not record
    out["net lending: rest of world"] = -sum(
        out[f"net lending: {s}"] for s in ["households", "firms", "government", "banks"]
    )
    wage = inside["nominal_wage_per_worker"].to_numpy()
    out["real wage growth"] = (wage[1:] / wage[:-1]) / (
        inside["cpi"].to_numpy()[1:] / inside["cpi"].to_numpy()[:-1]
    ) - 1
    for name in [
        "capacity_utilisation",
        "investment_rate",
        "markup",
        "expected_growth",
        "expected_inflation",
        "government_spending_fulfilment",
    ]:
        out[name.replace("_", " ")] = inside[name].to_numpy()[1:]
    unexplained = report[report["check"] == "money.unexplained"].set_index("t")["share_of_gdp"]
    out["unexplained money / GDP"] = unexplained.reindex(np.arange(1, len(wage))).to_numpy()
    n = min(len(v) for v in out.values())
    df = pd.DataFrame({k: v[:n] for k, v in out.items()})
    df.insert(0, "t", np.arange(1, n + 1))
    df.insert(0, "seed", seed)
    return df


def _eurostat_quarterly(path: Path, item: str | None = None) -> pd.Series:
    df = pd.read_csv(path)
    df = df[df["geo"] == GEO]
    if item is not None:
        df = df[df["na_item"] == item]
    series = df.set_index("TIME_PERIOD")["OBS_VALUE"]
    series.index = pd.PeriodIndex(series.index, freq="Q").to_timestamp()
    return series


def observed(data: DataWrapper, volumes: bool = True, adjusted: bool = True) -> pd.DataFrame:
    """Observed quarterly growth rates. volumes=False deflates nominal data by PPI/CPI as before R4. adjusted=True
    (default since 2026-10-22, R7) takes CPI inflation from the seasonally adjusted household consumption deflator
    and unemployment from the quarterly series, since the model has no seasons; adjusted=False keeps the CPI (not
    seasonally adjusted) and annual unemployment."""
    ex = data.synthetic_countries[COUNTRY].exogenous_data
    na = ex.national_accounts
    obs = pd.DataFrame(index=na.index)
    clv = pd.read_csv(VOLUMES).query("geo == @GEO").pivot(index="TIME_PERIOD", columns="na_item", values="OBS_VALUE")
    clv.index = pd.PeriodIndex(clv.index, freq="Q").to_timestamp()
    for agg, (_, deflator, col, item) in AGGREGATES.items():
        real = clv[item].reindex(na.index) if volumes else na[f"{col} (Value)"] / na[f"{deflator.upper()} (Value)"]
        obs[agg] = real / real.shift(1) - 1.0
    obs["CPI Inflation"] = na["CPI (Value)"] / na["CPI (Value)"].shift(1) - 1.0
    obs["Unemployment Rate"] = ex.labour_stats["Unemployment Rate (Value)"].reindex(obs.index)
    if adjusted:
        deflator = _eurostat_quarterly(DEFLATORS, "P31_S14_S15").reindex(na.index)
        obs["CPI Inflation"] = deflator / deflator.shift(1) - 1.0
        obs["Unemployment Rate"] = _eurostat_quarterly(UNEMPLOYMENT).reindex(obs.index) / 100.0
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


def expectation_wedge(sim: pd.DataFrame, obs: pd.DataFrame, quarters: int = 12) -> pd.DataFrame:
    """How far the model's realised path is from the expectations its agents hold (revision entry E_AR1, R2.7): for
    real GDP growth and CPI inflation, the RMSE against the data of the expectation path and of the realised path,
    both over AR(1)'s, and the correlation between the two paths across quarters and seeds. A model that only
    replays its AR(1) expectations has realised = expected."""
    target = obs.loc[obs.index > START].iloc[:quarters]
    history = obs.loc[(obs.index >= AR1_FIT_START) & (obs.index <= START)]
    rows = []
    for realised, expected in [("Real GDP", "expected growth"), ("CPI Inflation", "expected inflation")]:
        if expected not in sim:
            continue
        y = target[realised].to_numpy()
        ar1 = np.sqrt(np.mean((ar1_forecast(history[realised], len(y)) - y) ** 2))

        def rmse(column: str) -> float:
            paths = sim.pivot(index="t", columns="seed", values=column).to_numpy()[: len(y)]
            return np.median(np.sqrt(np.nanmean((paths - y[:, None]) ** 2, axis=0)))

        both = sim[sim["t"] <= quarters][[realised, expected]].dropna()
        rows.append(
            {
                "aggregate": realised,
                "expectation path / AR(1)": rmse(expected) / ar1,
                "realised path / AR(1)": rmse(realised) / ar1,
                "correlation expected-realised": both[realised].corr(both[expected]),
            }
        )
    return pd.DataFrame(rows).set_index("aggregate")


def var_forecast(history: pd.DataFrame, horizon: int, maxlags: int = 4) -> pd.DataFrame:
    """Iterated multi-step VAR(p) forecast of the scored aggregates, p by AIC up to `maxlags` (the peer benchmark of
    revision entry E23; Poledna et al. 2023 compare with a VAR)."""
    from statsmodels.tsa.api import VAR

    y = history.dropna().reset_index(drop=True)
    fit = VAR(y).fit(maxlags=maxlags, ic="aic")
    if fit.k_ar == 0:
        return pd.DataFrame([y.mean().to_numpy()] * horizon, columns=y.columns)
    return pd.DataFrame(fit.forecast(y.to_numpy()[-fit.k_ar :], horizon), columns=y.columns)


def scorecard(sim: pd.DataFrame, obs: pd.DataFrame, quarters: int) -> pd.DataFrame:
    # sim t=1 is the first simulated quarter after initialisation, i.e. START itself is t=0
    target = obs.loc[obs.index > START].iloc[:quarters]
    history = obs.loc[(obs.index >= AR1_FIT_START) & (obs.index <= START)]
    var = var_forecast(history[[agg for agg in SCORED if agg != "Unemployment Rate"]], len(target))
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
            row["VAR RMSE"] = np.sqrt(np.nanmean((var[agg].to_numpy()[: len(y)] - y) ** 2))
            row["sim / VAR"] = row["sim RMSE (median seed)"] / row["VAR RMSE"]
        rows.append(row)
    return pd.DataFrame(rows).set_index("aggregate")


def plot(sim: pd.DataFrame, obs: pd.DataFrame, quarters: int, title: str, path: Path) -> None:
    """Forecast fan of one step (kept for the experiments written before `run_experiment`)."""
    from plotting import forecast_fan

    forecast_fan(sim, obs, quarters, title, path)


def accounts_summary(audit: list[pd.DataFrame]) -> pd.DataFrame:
    """Worst residual of each accounting check over all seeds and periods, as a share of quarterly GDP."""
    report = pd.concat(audit, ignore_index=True)
    worst = report.loc[report.groupby("check")["share_of_gdp"].apply(lambda s: s.abs().idxmax())]
    return worst.set_index("check")[["share_of_gdp", "t", "seed"]].rename(
        columns={"share_of_gdp": "worst share of GDP"}
    )


@dataclass
class Step:
    """One configuration of an experiment: config changes applied on top of the defaults, and the arguments of
    `load_data` that build its initial state (settings that change initial stocks must be built into the data)."""

    label: str
    changes: list[Callable[[CountryConfiguration], None]] = field(default_factory=list)
    data: dict = field(default_factory=dict)
    row_changes: list[Callable[[RestOfTheWorldConfiguration], None]] = field(default_factory=list)


def summarise(label: str, sim: pd.DataFrame, obs: pd.DataFrame, audit: list[pd.DataFrame], quarters: int) -> dict:
    """One row of an experiment's summary: ratios over the first 12 quarters, growth, unemployment, accounts."""
    scored = min(12, quarters)
    card = scorecard(sim[sim["t"] <= scored], obs, scored)
    accounts = accounts_summary(audit)
    median_path = sim.groupby("t")["Real GDP"].median()
    return {
        "step": label,
        **{f"{agg} sim/AR1": card.loc[agg, "sim / AR(1)"] for agg in card.index if agg != "Unemployment Rate"},
        "GDP growth/q (12q)": card.loc["Real GDP", "sim mean"],
        f"GDP growth/q ({quarters}q)": sim["Real GDP"].mean(),
        "GDP growth/q (last 8q)": median_path.iloc[-8:].mean(),
        f"investment growth/q ({quarters}q)": sim["Real Investment"].mean(),
        "unemployment q12": sim.loc[sim["t"] == scored, "Unemployment Rate"].median(),
        f"unemployment q{quarters}": sim.loc[sim["t"] == quarters, "Unemployment Rate"].median(),
        "CPI inflation/q": sim["CPI Inflation"].mean(),
        "policy rate (last)": sim.loc[sim["t"] == quarters, "Policy Rate"].median(),
        "capacity utilisation (last)": sim.loc[sim["t"] == quarters, "capacity utilisation"].median(),
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


def run_experiment(file: str, doc: str, steps: list[Step], seeds: int = 10, quarters: int = 20) -> pd.DataFrame:
    """Run every step over `seeds` seeds and write outputs/<experiment>/: run.json, series_<k>.csv, fan_<k>.png,
    inside_<k>.png, summary.csv and ratios.png (sim/AR(1) by step and aggregate). Returns the summary."""
    from plotting import forecast_fan, mechanism_dashboard, ratio_heatmap
    from provenance import record_run

    name = Path(file).stem
    parser = argparse.ArgumentParser(description=doc, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seeds", type=int, default=seeds)
    parser.add_argument("--quarters", type=int, default=quarters)
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)
    warnings.filterwarnings("ignore")
    out_dir = ROOT / "outputs" / name
    record_run(out_dir, **vars(args), country=COUNTRY, start=START, steps=[step.label for step in steps])

    data = {}
    for step in steps:
        key = tuple(sorted(step.data.items()))
        if key not in data:
            data[key] = load_data(**step.data)
    obs = observed(next(iter(data.values())))
    rows = []
    for k, step in enumerate(steps):
        config, row_config = CountryConfiguration(), RestOfTheWorldConfiguration()
        for change in step.changes:
            change(config)
        for change in step.row_changes:
            change(row_config)
        audit = []
        try:
            sim = pd.concat(
                [
                    simulate(
                        data[tuple(sorted(step.data.items()))],
                        config.model_copy(deep=True),
                        seed,
                        args.quarters,
                        audit,
                        row_config.model_copy(deep=True),
                    )
                    for seed in range(args.seeds)
                ],
                ignore_index=True,
            )
        except (ValueError, FloatingPointError) as error:
            print(f"[{k}] {step.label}: diverged ({type(error).__name__})")
            rows.append({"step": step.label, "diverged": True})
            continue
        sim.to_csv(out_dir / f"series_{k}.csv", index=False)
        title = f"{name.split('_')[0]} step {k}: {step.label}"
        forecast_fan(sim, obs, min(12, args.quarters), title, out_dir / f"fan_{k}.png")
        mechanism_dashboard(sim, title, out_dir / f"inside_{k}.png")
        rows.append(summarise(step.label, sim, obs, audit, args.quarters))
        print(
            f"[{k}] {step.label}: GDP growth/q {rows[-1][f'GDP growth/q ({args.quarters}q)']:+.4f}, "
            f"unemployment q{args.quarters} {rows[-1][f'unemployment q{args.quarters}']:.3f}"
        )

    summary = pd.DataFrame(rows).set_index("step")
    target = obs.loc[obs.index > START]
    summary.loc["data (France 2014-)"] = pd.Series(
        {
            "GDP growth/q (12q)": target["Real GDP"].iloc[:12].mean(),
            f"GDP growth/q ({args.quarters}q)": target["Real GDP"].iloc[: args.quarters].mean(),
            f"investment growth/q ({args.quarters}q)": target["Real Investment"].iloc[: args.quarters].mean(),
            "unemployment q12": target["Unemployment Rate"].iloc[min(12, args.quarters) - 1],
            f"unemployment q{args.quarters}": target["Unemployment Rate"].iloc[args.quarters - 1],
            "CPI inflation/q": target["CPI Inflation"].iloc[: args.quarters].mean(),
        }
    ).reindex(summary.columns, fill_value=np.nan)
    summary.to_csv(out_dir / "summary.csv")
    ratio_heatmap(summary, f"{name}: sim / AR(1) RMSE, first 12 quarters", out_dir / "ratios.png")
    pd.set_option("display.width", 250)
    print(summary.T.to_string(float_format=lambda x: f"{x:.3f}"))
    print(f"\nwritten to {out_dir.relative_to(ROOT)}/")
    return summary
