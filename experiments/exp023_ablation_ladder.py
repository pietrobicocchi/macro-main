"""exp023: What does each modelling decision contribute? The ablation ladder on France (phase 6, R1.1, R2.1).

From an IIASA-like model (P0: the IIASA rules the code has, `settings.poledna_like`), adding the paper's innovations
(P1-P4: Leontief production, housing market, household credit, reservation wages) to reach the model as forked
(rung 0, with our accounting fixes), then our decisions one at a time to today's defaults (`settings.LADDER`; the
order is the order the decisions were made; the reviewers' ladder is order-agnostic).
Hypothesis (recorded before running): MD1 (price noise) and MD15's deterministic forecasts carry most of the gain
in the ratios; the growth-engine rungs (MD15 capacity, MD10-MD13) carry the gain in growth and unemployment.
France only, sample data: a diagnostic for the 38-country ladder, not its result.

Usage:
    uv run python experiments/exp023_ablation_ladder.py [--seeds 10] [--quarters 20]
"""

from scoring import run_experiment
from settings import LADDER

if __name__ == "__main__":
    run_experiment(__file__, __doc__, LADDER)
