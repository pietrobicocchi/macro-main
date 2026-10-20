"""exp001: Does the default model produce plausible macro dynamics?

Runs France initialised in 2014-Q1 (bundled sample data: real national accounts,
spoofed HFCS/Compustat micro-data) with default parameters, several seeds, and
scores quarterly growth rates against the observed French series (see scoring.py).

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

import pandas as pd
from provenance import record_run
from scoring import COUNTRY, RAW_DATA, ROOT, START, load_data, observed, plot, scorecard, simulate

from macromodel.configurations import CountryConfiguration
from macromodel.configurations.central_bank_configuration import (
    CentralBankConfiguration,
    CentralBankFunctions,
    CentralBankPolicy,
)


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

    data = load_data(scale=args.scale)
    country_config = CountryConfiguration(
        central_bank=CentralBankConfiguration(
            functions=CentralBankFunctions(policy_rate=CentralBankPolicy(name=args.policy))
        )
    )
    sim = pd.concat(
        [simulate(data, country_config, seed, args.quarters) for seed in range(args.seeds)], ignore_index=True
    )
    obs = observed(data)

    card = scorecard(sim, obs, args.quarters)
    sim.to_csv(out_dir / "series.csv", index=False)
    card.to_csv(out_dir / "scorecard.csv")
    title = f"exp001 baseline — {COUNTRY}, default parameters, scale {args.scale} (quarterly rates)"
    plot(sim, obs, args.quarters, title, out_dir / "figure.png")

    pd.set_option("display.width", 200)
    print(
        f"{COUNTRY} from {START.date()}, {args.seeds} seeds x {args.quarters} quarters, "
        f"scale={args.scale}, policy={args.policy}"
    )
    print(card.to_string(float_format=lambda x: f"{x:.4f}"))
    print(f"\nwritten to {out_dir.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
