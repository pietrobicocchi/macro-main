"""exp035: The paper's stated values for wages and banks (parameter audit, 2026-10-22)

The audit in PROJECT.md (Parameters in use) lists defaults that differ from the values the paper states. This
experiment tries those not yet tried, one at a time and together: no offered-wage markup when firms miss their labour
targets (φ^WN = 0; default 0.5), the paper's bank limits (firm debt-to-equity 1.0, return on equity 0.15, consumer
loans 0.36 of income; exp019 tried them on older defaults), and its bank solvency ratio 0.1 (default 0.05).
Hypothesis (recorded before running): each moves the ratios by less than 0.03. The wage markup only acts when firms
cannot hire, which is rare at 10% unemployment; healthy firms do not ask for credit (G9), so the firm limits do not
bind; the tighter consumer-loan limit lowers household credit, which already decays to almost nothing (M3); the
solvency ratio matters only if a bank's equity falls below 5–10% of its assets, which the one bank's does not.

Usage:
    uv run python experiments/exp035_paper_parameters.py [--seeds 10] [--quarters 20]
"""

from scoring import Step, run_experiment
from settings import paper_bank_limits, paper_bank_solvency, paper_offered_wage

STEPS = [
    Step("defaults"),
    Step("no offered-wage markup (φ^WN = 0)", [paper_offered_wage]),
    Step("paper's bank limits", [paper_bank_limits]),
    Step("paper's solvency ratio 0.1", [paper_bank_solvency]),
    Step("all three", [paper_offered_wage, paper_bank_limits, paper_bank_solvency]),
]

if __name__ == "__main__":
    run_experiment(__file__, __doc__, STEPS)
