"""Every figure goes through this module: one style, fixed colours and labels, so figures compare across experiments.

Figure families (PROJECT.md, I4):
- `forecast_fan`: model median and 10-90% band across seeds, data and the AR(1) benchmark, per scored aggregate.
- `mechanism_dashboard`: what the economy does inside (sector balances, capacity, labour, prices, expectations,
  government, accounts).
- `ratio_heatmap`: sim/AR(1) RMSE ratio by step and aggregate, diverging at 1.
- `model_map`: agents, markets and the quarter's sequence of events, with the rules a configuration uses.
Write `.png` to look at, `.pdf` for the paper.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LogNorm

COLORS = {
    "model": "#1f5fa8",
    "data": "#111111",
    "AR(1)": "#8c8c8c",
    "households": "#1f5fa8",
    "firms": "#d9822b",
    "government": "#2e8b57",
    "banks": "#8e44ad",
    "rest of world": "#8c8c8c",
}
LABELS = {
    "Real GDP": "Real GDP growth",
    "Real Household Cons.": "Household consumption growth",
    "Real Government Cons.": "Government consumption growth",
    "Real Investment": "Investment growth",
    "CPI Inflation": "CPI inflation",
    "Unemployment Rate": "Unemployment rate",
}
SECTORS = ["households", "firms", "government", "banks", "rest of world"]

plt.rcParams.update(
    {
        "font.size": 9,
        "axes.titlesize": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "legend.frameon": False,
        "figure.dpi": 120,
    }
)


def _save(fig: plt.Figure, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def _band(ax: plt.Axes, sim: pd.DataFrame, column: str, scale: float, color: str, label: str) -> None:
    """Median over seeds and the 10-90% band across seeds."""
    paths = sim.pivot(index="t", columns="seed", values=column) * scale
    ax.fill_between(paths.index, paths.quantile(0.1, axis=1), paths.quantile(0.9, axis=1), color=color, alpha=0.2, lw=0)
    ax.plot(paths.index, paths.median(axis=1), color=color, lw=1.8, label=label)


def forecast_fan(sim: pd.DataFrame, obs: pd.DataFrame, quarters: int, title: str, path: Path) -> None:
    """Scored aggregates in % per quarter (unemployment in %): model band across seeds, data, AR(1) forecast."""
    from scoring import AR1_FIT_START, SCORED, START, ar1_forecast

    target = obs.loc[obs.index > START].iloc[:quarters]
    history = obs.loc[(obs.index >= AR1_FIT_START) & (obs.index <= START)]
    t = np.arange(1, len(target) + 1)
    fig, axes = plt.subplots(2, 3, figsize=(12, 6), sharex=True)
    for ax, agg in zip(axes.flat, SCORED):
        _band(ax, sim[sim["t"] <= quarters], agg, 100, COLORS["model"], "model (median, 10-90% of seeds)")
        ax.plot(t, 100 * target[agg].to_numpy(), color=COLORS["data"], lw=1.8, label="data")
        if agg != "Unemployment Rate":
            ax.plot(t, 100 * ar1_forecast(history[agg], len(t)), color=COLORS["AR(1)"], ls="--", lw=1.4, label="AR(1)")
        ax.set_title(LABELS[agg])
        ax.set_ylabel("%" if agg == "Unemployment Rate" else "% per quarter")
    for ax in axes[-1]:
        ax.set_xlabel(f"quarters after {START.date()}")
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.03))
    fig.suptitle(title)
    _save(fig, path)


def mechanism_dashboard(sim: pd.DataFrame, title: str, path: Path) -> None:
    """One page on what the economy does inside; medians over seeds, bands 10-90% across seeds."""
    fig, axes = plt.subplots(3, 3, figsize=(13, 9), sharex=True)
    ax = axes[0, 0]
    for sector in SECTORS:
        paths = sim.pivot(index="t", columns="seed", values=f"net lending: {sector}") * 100
        ax.plot(paths.index, paths.median(axis=1), color=COLORS[sector], lw=1.6, label=sector)
    ax.axhline(0, color="black", lw=0.6)
    ax.set_title("Net lending by sector (rest of world: the residual)")
    ax.set_ylabel("% of quarterly GDP")
    ax.legend(fontsize=7, ncol=2)

    panels = [
        (axes[0, 1], [("capacity utilisation", "capacity used", COLORS["model"])], "Capacity utilisation", "%"),
        (
            axes[0, 2],
            [("investment rate", "investment / capital", COLORS["firms"])],
            "Investment rate",
            "% per quarter",
        ),
        (
            axes[1, 0],
            [
                ("Unemployment Rate", "unemployment", COLORS["model"]),
                ("Hiring Rate", "hires / employment", COLORS["government"]),
                ("Separation Rate", "separations / employment", COLORS["firms"]),
            ],
            "Labour market",
            "%",
        ),
        (axes[1, 1], [("markup", "price over unit cost - 1", COLORS["firms"])], "Markup", "%"),
        (
            axes[1, 2],
            [
                ("real wage growth", "real wage per worker", COLORS["households"]),
                ("CPI Inflation", "CPI inflation", COLORS["data"]),
                ("expected inflation", "expected CPI inflation", COLORS["AR(1)"]),
            ],
            "Wages and prices",
            "% per quarter",
        ),
        (
            axes[2, 0],
            [
                ("expected growth", "firms' expected growth", COLORS["firms"]),
                ("Real GDP", "realised real GDP growth", COLORS["model"]),
            ],
            "Expectations",
            "% per quarter",
        ),
        (
            axes[2, 1],
            [("government spending fulfilment", "realised / planned", COLORS["government"])],
            "Government spending",
            "% of plan",
        ),
        (
            axes[2, 2],
            [("unexplained money / GDP", "unexplained money", COLORS["banks"])],
            "Accounts (stock-flow residual)",
            "% of quarterly GDP",
        ),
    ]
    for ax, series, panel_title, unit in panels:
        for column, label, color in series:
            if column in sim:  # series written before a column existed lack it
                _band(ax, sim, column, 100, color, label)
        ax.set_title(panel_title)
        ax.set_ylabel(unit)
        if len(series) > 1:
            ax.legend(fontsize=7)
    for ax in axes[-1]:
        ax.set_xlabel("quarter")
    fig.suptitle(title)
    _save(fig, path)


SHORT_LABELS = {
    "Real GDP": "GDP",
    "Real Household Cons.": "HH cons.",
    "Real Government Cons.": "Gov. cons.",
    "Real Investment": "Invest.",
    "CPI Inflation": "CPI",
}


def ratio_heatmap(summary: pd.DataFrame, title: str, path: Path) -> None:
    """sim/AR(1) RMSE ratio by step (rows) and aggregate (columns); blue beats AR(1), red loses, log scale clipped
    to [0.5, 2]."""
    from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator

    columns = [c for c in summary.columns if c.endswith("sim/AR1")]
    table = summary[columns].dropna(how="all").astype(float)
    norm = LogNorm(vmin=0.5, vmax=2.0)
    fig, ax = plt.subplots(figsize=(1.1 * len(columns) + 4.5, 0.4 * len(table) + 1.6))
    image = ax.imshow(table.to_numpy(), cmap="RdBu_r", norm=norm, aspect="auto")
    for (i, j), value in np.ndenumerate(table.to_numpy()):
        if np.isfinite(value):
            dark = abs(np.log(np.clip(value, 0.5, 2.0))) > 0.45
            ax.text(j, i, f"{value:.2f}", ha="center", va="center", fontsize=8, color="white" if dark else "black")
    ax.set_xticks(range(len(columns)), [SHORT_LABELS.get(c.replace(" sim/AR1", ""), c) for c in columns])
    ax.xaxis.tick_top()
    ax.set_yticks(range(len(table)), table.index)
    ax.grid(False)
    bar = fig.colorbar(image, ax=ax, label="sim / AR(1) RMSE (log scale; < 1 beats AR(1))", fraction=0.04)
    bar.ax.yaxis.set_major_locator(FixedLocator([0.5, 0.75, 1.0, 1.5, 2.0]))
    bar.ax.yaxis.set_minor_locator(NullLocator())
    bar.ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax.set_title(title, pad=24)
    _save(fig, path)


# What each rule in use does, in a few words, and its decision or register tag (PROJECT.md, "Model map"): an MD
# number is our decision; "paper: ..." an upstream default that departs from the paper; untagged rules follow it
RULES = {
    "SlackAwareGrowthForecastingAutoReg": ("AR(1) on growth, lowered when unemployment is low", "MD13"),
    "GrowthManualForecastingAutoReg": ("AR(1) on growth", ""),
    "InflationManualForecastingAutoReg": ("AR(1)", ""),
    "DefaultHouseholdConsumption": ("share of expected income, no floor", "MD14"),
    "AverageSavingRatesSetter": ("one average rate", "paper: per household (M13)"),
    "EqualSocialTransfersSetter": ("equal split", "paper: per household (M13)"),
    "DefaultHouseholdDemandForProperty": ("buy-or-rent logit", ""),
    "ConstantRentSetter": ("constant", "paper: indexed (M14)"),
    "UnableToPayHouseholdInsolvencyHandler": ("default when unable to pay", "MD8"),
    "DefaultDemandEstimator": ("previous demand x expected growth", ""),
    "PureLeontief": ("Leontief", ""),
    "DefaultTargetProductionSetter": ("expected demand", "paper: chi caps (G4)"),
    "PaperTargetProductionSetter": ("demand, capped by inputs (chi)", "MD19"),
    "DefaultPriceSetter": ("expected inflation and unit-cost growth", "MD14"),
    "WorkEffortFirmWageSetter": ("gradual CPI catch-up, work effort", "MD14"),
    "FinancialTargetCapitalInputsSetter": ("replace depreciation", ""),
    "PartialAdjustmentTargetCapitalInputsSetter": ("close 10% of the gap to desired capital", "MD10"),
    "NoOpTFPGrowth": ("constant", ""),
    "LabourAugmentingGrowth": ("output per worker +0.25%/q", "MD12"),
    "AutoregressiveGovernmentConsumptionSetter": ("AR(1) on log real spending", ""),
    "AutoregressiveGrowthGovernmentConsumptionSetter": ("AR(1) on growth of real spending", "MD16"),
    "GrowthSocialBenefitsSetter": ("grow with expected growth", "cash only: MD17"),
    "DefaultInterestRatesSetter": ("error correction on the policy rate", ""),
    "MinimumCapitalBankDemography": ("state recapitalises", "MD5"),
    "ConstantPolicyRate": ("constant", "paper: Taylor rule (P4)"),
    "PolednaPolicyRate": ("Taylor rule", "MD18"),
    "SearchFrictionsLabourMarketClearer": ("separations and a matching function", "MD11"),
    "PolednaLabourMarketClearer": ("fire to target, hire at random", ""),
    "WaterBucketGoodsMarketClearer": ("search and matching by price and size", ""),
    "WaterBucketCreditMarketClearer": ("search and matching by rate", ""),
    "AutomaticHousingMarketClearer": ("optimal assignment", "paper: random (E12)"),
    "GrowthRoWExportsSetter": ("AR(1) forecast", "paper: index (M15)"),
    "InflationRoWImportsSetter": ("AR(1) forecast", "paper: index (M15)"),
}
# (box title, box centre, [(label, config path of the rule)]); the rest of the world is in the simulation config
MAP_BOXES = [
    (
        "Expectations",
        (0.5, 0.86),
        [("growth", "economy.functions.growth"), ("inflation", "economy.functions.inflation")],
    ),
    (
        "Households",
        (0.1, 0.58),
        [
            ("consumption", "households.functions.consumption"),
            ("saving", "households.functions.saving_rates"),
            ("transfers", "households.functions.social_transfers"),
            ("housing", "households.functions.property"),
            ("rents", "households.functions.rent"),
            ("default", "households.functions.insolvency"),
        ],
    ),
    (
        "Firms",
        (0.31, 0.58),
        [
            ("demand", "firms.functions.demand_estimator"),
            ("target output", "firms.functions.target_production"),
            ("production", "firms.functions.production"),
            ("prices", "firms.functions.prices"),
            ("wages", "firms.functions.wage_setter"),
            ("investment", "firms.functions.target_capital_inputs"),
            ("productivity", "firms.functions.productivity_growth"),
        ],
    ),
    (
        "Government",
        (0.52, 0.58),
        [
            ("consumption", "government_entities.functions.consumption"),
            ("benefits", "central_government.functions.social_benefits"),
        ],
    ),
    (
        "Banks, central bank",
        (0.72, 0.58),
        [
            ("loan rates", "banks.functions.interest_rates"),
            ("failure", "banks.functions.demography"),
            ("policy rate", "central_bank.functions.policy_rate"),
        ],
    ),
    ("Rest of the world", (0.91, 0.58), [("exports", "row.exports"), ("imports", "row.imports")]),
    ("Housing market", (0.1, 0.28), [("", "housing_market.functions.clearing")]),
    ("Labour market", (0.3, 0.28), [("", "labour_market.functions.clearing")]),
    ("Goods market", (0.55, 0.28), [("", "goods")]),
    ("Credit market", (0.8, 0.28), [("", "credit_market.functions.clearing")]),
]
MAP_LINKS = [
    ("Households", "Housing market"),
    ("Households", "Labour market"),
    ("Firms", "Labour market"),
    ("Households", "Goods market"),
    ("Firms", "Goods market"),
    ("Government", "Goods market"),
    ("Rest of the world", "Goods market"),
    ("Households", "Credit market"),
    ("Firms", "Credit market"),
    ("Banks, central bank", "Credit market"),
]
SEQUENCE = [
    "expectations",
    "targets: production, prices,\nwages, inputs, plans",
    "labour market",
    "housing and\ncredit markets",
    "goods market\n(with rest of world)",
    "realised accounts: profits,\ntaxes, deposits, defaults",
]


def _rule(config, row_config, path: str) -> str:
    if path == "goods":
        return "WaterBucketGoodsMarketClearer"
    obj = row_config.functions if path.startswith("row.") else config
    for name in path.removeprefix("row.").split("."):
        obj = getattr(obj, name)
    return obj.name


def model_map(config, path: Path, row_config=None, title: str = "Model map: the rules in use") -> None:
    """Agents, markets and a quarter's sequence of events, with what each rule in `config` does and its tag."""
    from macromodel.configurations.row_configuration import RestOfTheWorldConfiguration

    row_config = row_config or RestOfTheWorldConfiguration()
    fig, ax = plt.subplots(figsize=(16, 9))
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    centres = {}
    for box_title, (x, y), rules in MAP_BOXES:
        lines = []
        for label, rule_path in rules:
            name = _rule(config, row_config, rule_path)
            words, tag = RULES.get(name, (name, ""))
            lines.append((f"{label}: " if label else "") + words + (f"\n   [{tag}]" if tag else ""))
        if box_title == "Expectations":
            lines.append("forecast noise: " + ("none [MD15]" if config.assume_zero_noise else "random draw"))
        is_market = box_title.endswith("market")
        ax.text(
            x,
            y,
            box_title.upper() + "\n" + "\n".join(lines),
            ha="center",
            va="center",
            fontsize=7.5,
            linespacing=1.35,
            wrap=True,
            bbox={
                "boxstyle": "round,pad=0.5",
                "fc": "#eef3fa" if is_market else "#fbf6ee",
                "ec": COLORS["model"] if is_market else COLORS["firms"],
            },
        )
        centres[box_title] = (x, y)
    arrow = {"arrowstyle": "<->", "color": "#9a9a9a", "lw": 0.9}
    for start, end in MAP_LINKS:
        (x0, y0), (x1, y1) = centres[start], centres[end]
        ax.annotate("", xy=(x1, y1 + 0.05), xytext=(x0, y0 - 0.15), arrowprops=arrow)
    x0, y0 = centres["Expectations"]
    for name in ["Households", "Firms", "Government", "Banks, central bank"]:
        x1, y1 = centres[name]
        ax.annotate("", xy=(x1, y1 + 0.14), xytext=(x0, y0 - 0.05), arrowprops={"arrowstyle": "->", "color": "#c4c4c4"})
    for k, step in enumerate(SEQUENCE):
        x = 0.08 + k * 0.168
        ax.text(
            x,
            0.06,
            f"{k + 1}. {step}",
            ha="center",
            va="center",
            fontsize=8,
            bbox={"boxstyle": "round", "fc": "white", "ec": "#888888"},
        )
        if k:
            ax.annotate("", xy=(x - 0.075, 0.06), xytext=(x - 0.093, 0.06), arrowprops={"arrowstyle": "->"})
    ax.text(0.5, 0.125, "one quarter", ha="center", fontsize=9, style="italic")
    ax.text(0.99, 0.95, "[MD#]: our decision\n[paper: ...]: differs from the paper", ha="right", va="top", fontsize=8)
    ax.set_title(title)
    _save(fig, path)
