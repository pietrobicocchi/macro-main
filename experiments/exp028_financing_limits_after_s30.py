"""exp028: With the capital stock valued correctly (S30), do firms get credit, and do financing limits brake
investment? (G9; repeats exp019, whose firms' collateral was a ninth of its value)

Steps: defaults; the paper's bank limits (firm debt-to-equity 1.0); the paper's limits with capital purchases cut by
half the long-term credit applied for but not received (credit gap 0.5), and fully (1.0).
Hypothesis (recorded before running): with true collateral firms receive the long-term credit they ask for, so the
credit gap rarely binds and the limits change little; exp019's recession came from S30.

Usage:
    uv run python experiments/exp028_financing_limits_after_s30.py [--seeds 10] [--quarters 20]
"""

from functools import partial

from scoring import Step, run_experiment
from settings import investment_engine, paper_bank_limits


def credit_gap(fraction: float):
    return partial(investment_engine, adjustment_speed=0.10, demand_smoothing=0.10, credit_gap_fraction=fraction)


STEPS = [
    Step("defaults"),
    Step("paper bank limits", [paper_bank_limits]),
    Step("paper bank limits, credit gap 0.5", [paper_bank_limits, credit_gap(0.5)]),
    Step("paper bank limits, credit gap 1", [paper_bank_limits, credit_gap(1.0)]),
]

if __name__ == "__main__":
    run_experiment(__file__, __doc__, STEPS)
