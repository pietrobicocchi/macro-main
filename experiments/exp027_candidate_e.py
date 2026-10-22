"""exp027: The decision options together: cash benefits (F6), the paper's Taylor rule (P4) and the paper's caps on
target production (G4).

Each improves realism or matches the paper and each was tried alone (exp024, exp025, exp026). Candidate E combines
them. Hypothesis (recorded before running): the effects are close to additive; E tracks unemployment at least as well
as the paper's caps alone (9.7% / 8.6% at q12 / q20) with government consumption near the cash-benefits run (1.3).

Usage:
    uv run python experiments/exp027_candidate_e.py [--seeds 10] [--quarters 20]
"""

from scoring import Step, run_experiment
from settings import paper_target_production, taylor_rule

CASH = {"cash_social_benefits": True}
STEPS = [
    Step("defaults"),
    Step("cash benefits (F6)", data=CASH),
    Step("Taylor rule (P4)", [taylor_rule]),
    Step("paper's target-production caps (G4)", [paper_target_production]),
    Step("E: all three", [taylor_rule, paper_target_production], CASH),
]

if __name__ == "__main__":
    run_experiment(__file__, __doc__, STEPS)
