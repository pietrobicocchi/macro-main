"""exp029: Does inflation respond to slack once wages do? A wage Phillips curve (P2, phase 3)

Nominal wages grow by kappa times the gap between the initial and the latest unemployment rate each quarter
(`unemployment_gap_sensitivity`); with cost pass-through (MD14) wage costs reach prices. Steps: defaults; kappa
0.05, 0.1, 0.2; kappa 0.1 with the paper's Taylor rule, so the policy rate can respond to the extra inflation.
Hypothesis (recorded before running): unemployment falls below its initial level under the growth engine, so wages
and then CPI inflation rise by a few hundredths of a point a quarter at kappa 0.1; the CPI ratio worsens slightly
(2014-16 inflation fell with oil prices, which the model cannot see) and unemployment barely moves (G17: higher
prices do not cut spending).

Usage:
    uv run python experiments/exp029_wage_phillips_curve.py [--seeds 10] [--quarters 20]
"""

from functools import partial

from scoring import Step, run_experiment
from settings import taylor_rule, wage_phillips_curve

STEPS = [
    Step("defaults"),
    Step("Phillips curve 0.05", [partial(wage_phillips_curve, sensitivity=0.05)]),
    Step("Phillips curve 0.1", [partial(wage_phillips_curve, sensitivity=0.1)]),
    Step("Phillips curve 0.2", [partial(wage_phillips_curve, sensitivity=0.2)]),
    Step("Phillips curve 0.1, Taylor rule", [partial(wage_phillips_curve, sensitivity=0.1), taylor_rule]),
]

if __name__ == "__main__":
    run_experiment(__file__, __doc__, STEPS)
