"""exp039: Dividends that pay exactly households' financial income (F2, MD6, S9)

exp038: after the national-accounts return (S9), firm shares paying dividends (MD6) overpay, because the Eurostat payout
ratio (0.46) counts households' own operating surplus and mixed income (imputed rents, the self-employed) as
distributed profits. The data option `payout_from_national_accounts` sets the payout so that initial dividends equal
households' property income net of interest (D4 − D41), the income S9 pays: 0.37 with the S32 investment split.
Steps: defaults; S9 and S32; with firm shares at the Eurostat payout; with firm shares at the matched payout.
Hypothesis (recorded before running): with the matched payout, dividends replace the unpaid income almost one for
one, so household consumption, growth and unemployment are close to the S9-and-S32 step, the money residual for
unbacked flows (S9) disappears, and firms' net lending falls from about 10% to about 6% of GDP (F2).

Usage:
    uv run python experiments/exp039_dividends_matched.py [--seeds 10] [--quarters 20]
"""

from scoring import Step, run_experiment
from settings import INVESTMENT_BY_CAPITAL_COMPENSATION, NATIONAL_ACCOUNTS_PAYOUT, NATIONAL_ACCOUNTS_RETURN, firm_shares

S32_S9 = {**INVESTMENT_BY_CAPITAL_COMPENSATION, **NATIONAL_ACCOUNTS_RETURN}

STEPS = [
    Step("defaults"),
    Step("S9 return, S32 investment split", data=S32_S9),
    Step("+ firm shares, Eurostat payout", [firm_shares], S32_S9),
    Step("+ firm shares, matched payout", [firm_shares], {**S32_S9, **NATIONAL_ACCOUNTS_PAYOUT}),
]

if __name__ == "__main__":
    run_experiment(__file__, __doc__, STEPS)
