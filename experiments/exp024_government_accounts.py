"""exp024: Do realistic government and household accounts change the dynamics (F6, S9, S31)?

At t = 1 the government pays 31% of GDP in benefits (France 2014: 19.8%) because SOCX total public social spending
counts in-kind services that are also government consumption; the deficit is 18% of GDP (France 4.6%), household
income 80% of GDP (France about 67%) and households save about 40% of it. Steps: defaults; benefits from SOCX
cash spending only (data option `cash_social_benefits`); and in addition households' other financial assets as
shares in firms that pay dividends (MD6), so their financial income has a payer (S9).
Hypothesis (recorded before running): cash benefits bring the deficit to about 6% of GDP and household income to
about 67% of GDP without moving consumption at t = 1 (saving rates are fitted to initial consumption); growth and
the ratios move little over 12 quarters, but household saving (net lending) falls by about 10 points of GDP.
Firm shares cut household income further (dividends are far smaller than today's unpaid financial income).

Usage:
    uv run python experiments/exp024_government_accounts.py [--seeds 10] [--quarters 20]
"""

from scoring import Step, run_experiment
from settings import firm_shares

STEPS = [
    Step("defaults"),
    Step("cash benefits (F6)", data={"cash_social_benefits": True}),
    Step("cash benefits, firm shares (F6, MD6)", [firm_shares], data={"cash_social_benefits": True}),
]

if __name__ == "__main__":
    run_experiment(__file__, __doc__, STEPS)
