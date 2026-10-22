"""The standard figures, rebuilt from experiment outputs without running simulations: `make figures`.

Each entry of FIGURES names a figure and how to draw it; a figure becomes a paper figure by being listed here and
copied from outputs/figures/ (PDF) into the paper repository's img/. Run the experiments a figure reads first.
"""

from pathlib import Path

import pandas as pd
from plotting import forecast_fan, mechanism_dashboard, model_map, ratio_heatmap
from scoring import ROOT, load_data, observed

from macromodel.configurations import CountryConfiguration

OUT = ROOT / "outputs"
BASELINE = OUT / "exp001_baseline" / "ConstantPolicyRate_scale10000"


def _baseline_fan(path: Path) -> None:
    sim = pd.read_csv(BASELINE / "series.csv")
    forecast_fan(sim, observed(load_data()), 12, "Default model, France from 2014-Q1 (10 seeds)", path)


def _baseline_inside(path: Path) -> None:
    mechanism_dashboard(pd.read_csv(BASELINE / "series.csv"), "Default model: inside the economy, France", path)


def _summary_heatmap(experiment: str, title: str):
    def draw(path: Path) -> None:
        ratio_heatmap(pd.read_csv(OUT / experiment / "summary.csv", index_col=0), title, path)

    return draw


FIGURES = {
    "model_map": lambda path: model_map(CountryConfiguration(), path),
    "baseline_fan": _baseline_fan,
    "baseline_inside": _baseline_inside,
    "ablation_ladder": _summary_heatmap("exp023_ablation_ladder", "Ablation ladder, France: sim / AR(1) RMSE"),
    "robustness": _summary_heatmap("exp022_robustness", "Robustness of the defaults: sim / AR(1) RMSE"),
    "leave_one_out": _summary_heatmap("exp025_leave_one_out", "Today's defaults without one element: sim / AR(1) RMSE"),
}


def main() -> None:
    out_dir = OUT / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, draw in FIGURES.items():
        try:
            for suffix in [".pdf", ".png"]:
                draw(out_dir / f"{name}{suffix}")
            print(f"{name}: written")
        except FileNotFoundError as error:
            print(f"{name}: skipped, run its experiment first ({Path(error.filename).relative_to(ROOT)})")
    print(f"figures in {out_dir.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
