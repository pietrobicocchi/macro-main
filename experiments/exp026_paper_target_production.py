"""exp026: Does the paper's target-production rule change today's model? (G4, revision entry E2)

The paper caps target production at Q + chi (limit - Q) for labour, intermediate inputs and capital
(`eq:firm_target_production`, posterior chi = 0.53, 0.03, 0.18); the code instead caps hiring and input purchases.
Steps: defaults; the paper's caps at its posterior; all chi = 1 (planning fully constrained, as in the IIASA model).
Hypothesis (recorded before running): with spare capacity the capital cap rarely binds, so the posterior caps change
little; chi = 1 slows growth because labour then caps planned output and hiring follows planned output.

Usage:
    uv run python experiments/exp026_paper_target_production.py [--seeds 10] [--quarters 20]
"""

from functools import partial

from scoring import Step, run_experiment
from settings import paper_target_production

STEPS = [
    Step("defaults"),
    Step("paper's caps on target production (posterior)", [paper_target_production]),
    Step("caps with chi = 1 (IIASA-like)", [partial(paper_target_production, chi_h=1.0, chi_m=1.0, chi_k=1.0)]),
]

if __name__ == "__main__":
    run_experiment(__file__, __doc__, STEPS)
