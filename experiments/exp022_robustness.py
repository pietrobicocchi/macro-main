"""exp022: Are today's defaults (MD15-MD16) a plateau or a knife edge?

Every MD15-MD16 value was chosen while looking at the 2014-16 scores. One-at-a-time changes around the defaults:
investment gap adjustment (lambda) and demand smoothing, separation rate, productivity growth, slack sensitivity,
spare capacity, the government's deflator, the rest of the world's forecast noise; one firm per industry against
business-demography firm counts; and no source of growth, where the initial state should be close to a fixed point.
Hypothesis (recorded before running): ratios move by less than 0.1 for halving or doubling a value, except lambda
and spare capacity, which set the size of the start-up investment burst.

Usage:
    uv run python experiments/exp022_robustness.py [--seeds 10] [--quarters 20]
"""

from functools import partial

from scoring import Step, run_experiment
from settings import (
    government_consumption_plan,
    growth_forecast_slack_aware,
    investment_engine,
    labour_productivity_growth,
    no_growth,
    row_no_forecast_noise,
    separation_rate,
    spare_capacity,
)

STEPS = [
    Step("defaults"),
    Step("lambda 0.05", [partial(investment_engine, adjustment_speed=0.05, demand_smoothing=0.10)]),
    Step("lambda 0.20", [partial(investment_engine, adjustment_speed=0.20, demand_smoothing=0.10)]),
    Step("demand smoothing 0.05", [partial(investment_engine, adjustment_speed=0.10, demand_smoothing=0.05)]),
    Step("demand smoothing 0.20", [partial(investment_engine, adjustment_speed=0.10, demand_smoothing=0.20)]),
    Step("separation rate 0.02", [partial(separation_rate, rate=0.02)]),
    Step("separation rate 0.05", [partial(separation_rate, rate=0.05)]),
    Step("productivity growth 0.15%/q", [partial(labour_productivity_growth, rate=0.0015)]),
    Step("productivity growth 0.35%/q", [partial(labour_productivity_growth, rate=0.0035)]),
    Step("slack sensitivity 0.1", [partial(growth_forecast_slack_aware, sensitivity=0.1)]),
    Step("slack sensitivity 0.3", [partial(growth_forecast_slack_aware, sensitivity=0.3)]),
    Step("spare capacity: utilisation 0.80", [partial(spare_capacity, rate=0.80)], {"utilisation_rate": 0.80}),
    Step("spare capacity: utilisation 0.90", [partial(spare_capacity, rate=0.90)], {"utilisation_rate": 0.90}),
    Step("government plan deflated by PPI", [partial(government_consumption_plan, deflator="ppi")]),
    Step("rest of world without forecast noise", row_changes=[row_no_forecast_noise]),
    Step("many firms (business demography)", data={"many_firms": True}),
    Step("no growth (fixed point check)", [no_growth]),
]

if __name__ == "__main__":
    run_experiment(__file__, __doc__, STEPS)
