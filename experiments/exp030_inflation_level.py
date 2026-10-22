"""exp030: Where does the inflation level come from? (P2, phase 3; next step 3)

Realised CPI inflation is 0.22%/q against 0.07%/q in the data (2014-16). Prices grow by 0.5 expected PPI inflation
plus 0.5 unit-cost growth (MD14); expected inflation is the AR(1) on 2000-2013 PPI (0.38-0.42%/q in the run), and
import prices follow the domestic price level (as in the paper), so nothing else anchors prices. Steps: defaults;
prices from unit costs only; prices from expected inflation only; without productivity growth (MD12); wages
indexed to the latest CPI in full every quarter instead of a quarter of the gap.
Hypothesis (recorded before running): the expectation term sets the level. With expectations only, realised
inflation is about expected inflation (0.4%/q) and the markup rises faster; with unit costs only, inflation follows
wage and input costs and falls well below 0.2%/q, closer to the data, and the markup stays flat. Productivity growth
changes little (wages grow with it, so unit labour costs barely move); full wage indexation raises inflation
slightly.

Usage:
    uv run python experiments/exp030_inflation_level.py [--seeds 10] [--quarters 20]
"""

from functools import partial

from scoring import Step, run_experiment
from settings import lagged_wage_indexation, price_brakes, without_productivity_growth

STEPS = [
    Step("defaults"),
    Step("prices from unit costs only", [partial(price_brakes, cost_pass_through=1.0)]),
    Step("prices from expected inflation only", [partial(price_brakes, cost_pass_through=0.0)]),
    Step("without productivity growth (MD12)", [without_productivity_growth]),
    Step("wages fully indexed each quarter", [partial(lagged_wage_indexation, speed=1.0)]),
]

if __name__ == "__main__":
    run_experiment(__file__, __doc__, STEPS)
