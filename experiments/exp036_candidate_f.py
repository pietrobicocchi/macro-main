"""exp036: The candidate decisions together (candidate F)

Four candidates await a decision, each tried alone: the investment split by capital compensation (S32, exp033; a bug
in the split), the national-accounts return on household financial assets (S9, exp031), the paper's moving
probabilities for housing (M9, exp034) and the paper's bank limits (exp035). Steps add them in that order (data
fixes first, then behaviour).
Hypothesis (recorded before running): close to additive, as in exp027. S32 removes the periodic default and improves
investment; S9 worsens household consumption by about 0.07; the moving probabilities improve GDP and household
consumption by about 0.05 and bring growth and unemployment to the data; the bank limits improve investment. Together
GDP about 0.97, household consumption about 1.05, investment about 0.95; government consumption stays the noisiest
(1.6–2.0).

Usage:
    uv run python experiments/exp036_candidate_f.py [--seeds 10] [--quarters 20]
"""

from scoring import Step, run_experiment
from settings import (
    INVESTMENT_BY_CAPITAL_COMPENSATION,
    NATIONAL_ACCOUNTS_RETURN,
    paper_bank_limits,
    paper_moving_probabilities,
)

S32_S9 = {**INVESTMENT_BY_CAPITAL_COMPENSATION, **NATIONAL_ACCOUNTS_RETURN}

STEPS = [
    Step("defaults"),
    Step("S32 investment split", data=INVESTMENT_BY_CAPITAL_COMPENSATION),
    Step("+ S9 national-accounts return", data=S32_S9),
    Step("+ paper's moving probabilities", [paper_moving_probabilities], S32_S9),
    Step("+ paper's bank limits (candidate F)", [paper_moving_probabilities, paper_bank_limits], S32_S9),
]

if __name__ == "__main__":
    run_experiment(__file__, __doc__, STEPS)
