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
            _band(ax, sim, column, 100, color, label)
        ax.set_title(panel_title)
        ax.set_ylabel(unit)
        if len(series) > 1:
            ax.legend(fontsize=7)
    for ax in axes[-1]:
        ax.set_xlabel("quarter")
    fig.suptitle(title)
    _save(fig, path)


def ratio_heatmap(summary: pd.DataFrame, title: str, path: Path) -> None:
    """sim/AR(1) RMSE ratio by step (rows) and aggregate (columns); blue beats AR(1), red loses, log scale."""
    columns = [c for c in summary.columns if c.endswith("sim/AR1")]
    table = summary[columns].dropna(how="all").astype(float)
    fig, ax = plt.subplots(figsize=(1.4 * len(columns) + 3, 0.45 * len(table) + 1.5))
    image = ax.imshow(table.to_numpy(), cmap="RdBu_r", norm=LogNorm(vmin=0.5, vmax=2.0), aspect="auto")
    for (i, j), value in np.ndenumerate(table.to_numpy()):
        if np.isfinite(value):
            ax.text(j, i, f"{value:.2f}", ha="center", va="center", fontsize=8)
    ax.set_xticks(
        range(len(columns)), [LABELS.get(c.replace(" sim/AR1", ""), c).replace(" growth", "") for c in columns]
    )
    ax.set_yticks(range(len(table)), table.index)
    ax.grid(False)
    fig.colorbar(image, ax=ax, label="sim / AR(1) RMSE (log scale)", ticks=[0.5, 0.75, 1, 1.5, 2], format="%.2g")
    ax.set_title(title)
    _save(fig, path)
