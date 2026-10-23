"""exp040: The decisions adopted on 2026-10-23 together (candidate G)

Pietro asked to adopt the waiting candidates where the economic mechanism is sound. Steps start from the defaults
before 2026-10-23 and add them in order, data fixes first: the investment split by capital compensation (S32, a bug in
the split; exp033); households' financial income at the national accounts' return (S9, MD20; exp031); the paper's
housing rules (MD21: owners and renters keep their home with probability 79/80 and 7/8 a quarter, renters can pay up to
25% of their income in rent, buyers up to 5 years of their income; exp034, exp037); the paper's firm-loan limits
(MD22: debt up to the capital stock's value, return on equity 0.15; exp035). The last step adds the paper's
consumer-loan ratio (0.36 of income, default 0.5), not adopted: the rule's base is in question (M3). Also not adopted:
dividends (MD6, exp039: the first dividend's timing) and the effective profit tax alone (F7, exp032).
Hypothesis (recorded before running): candidate F (exp036) plus the housing affordability rules. GDP about 0.98,
household consumption about 0.95-1.00, investment about 1.05-1.10, government consumption the worst ratio (about
2.0-2.3, rationing noise); growth and unemployment within the sanity gate (unemployment near 9.8% at q12); house sales
about 0.4% and new rentals about 0.9% of the stock a quarter; no periodic firm default.

Usage:
    uv run python experiments/exp040_candidate_g.py [--seeds 10] [--quarters 20]
"""

from scoring import Step, run_experiment
from settings import (
    OLD_INVESTMENT_SPLIT,
    SURVEY_RETURN,
    paper_bank_limits,
    pre_md21_housing_rules,
    pre_md22_bank_limits,
)

BEFORE = [pre_md21_housing_rules, pre_md22_bank_limits]

STEPS = [
    Step("defaults before 2026-10-23", BEFORE, {**OLD_INVESTMENT_SPLIT, **SURVEY_RETURN}),
    Step("+ S32 investment split (bug fix)", BEFORE, SURVEY_RETURN),
    Step("+ MD20 national-accounts return", BEFORE),
    Step("+ MD21 paper's housing rules", [pre_md22_bank_limits]),
    Step("+ MD22 paper's firm-loan limits (today's defaults)"),
    Step("+ paper's consumer-loan ratio (not adopted)", [paper_bank_limits]),
]

if __name__ == "__main__":
    run_experiment(__file__, __doc__, STEPS)
