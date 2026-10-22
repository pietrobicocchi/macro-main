"""exp038: Can households' financial assets pay dividends once their return is the national accounts' (S9, MD6, F2)

With the survey's return, switching households' other financial assets to shares in firms that pay dividends (MD6,
`firm_shares`) removed 19% of GDP of household income at once and collapsed demand (exp024: unemployment 21%). With the
national-accounts return (S9 option, exp031) that income is 4% of GDP. Steps: defaults; the national-accounts return;
with firm shares; with the investment split by capital compensation as well (S32: no firm starts loss-making).
Hypothesis (recorded before running): with firm shares, dividends (paid out of after-tax profits at the Eurostat payout
ratio) replace the 4% of GDP of unpaid income; if they are near that size household consumption barely changes and the
money residual (unbacked flows) falls, and firms stop net lending about 10% of GDP every quarter (F2). If dividends are
much larger, household consumption and GDP rise.

Usage:
    uv run python experiments/exp038_dividends_after_s9.py [--seeds 10] [--quarters 20]
"""

from scoring import Step, run_experiment
from settings import INVESTMENT_BY_CAPITAL_COMPENSATION, NATIONAL_ACCOUNTS_RETURN, firm_shares

S32_S9 = {**INVESTMENT_BY_CAPITAL_COMPENSATION, **NATIONAL_ACCOUNTS_RETURN}

STEPS = [
    Step("defaults"),
    Step("national-accounts return (S9)", data=NATIONAL_ACCOUNTS_RETURN),
    Step("+ firm shares paying dividends (MD6)", [firm_shares], NATIONAL_ACCOUNTS_RETURN),
    Step("+ investment split by capital compensation (S32)", [firm_shares], S32_S9),
]

if __name__ == "__main__":
    run_experiment(__file__, __doc__, STEPS)
