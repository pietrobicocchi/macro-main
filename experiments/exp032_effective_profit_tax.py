"""exp032: The profit tax at the national accounts' effective rate (F7; next step 4)

The profit tax is the statutory 38% on accounting profits, so firms and banks pay 8.5% of quarterly GDP; French
corporate income tax receipts were 2.8% (Eurostat gov_10a_taxag D51B_C2, 55.3 bn in 2014). The option sets the rate
that raises the receipts on the model's initial profits: 12.7%. Steps: defaults; effective profit tax; effective
profit tax with the national-accounts return on household financial assets (S9, exp031).
Hypothesis (recorded before running): firms keep 5.7% of GDP more each quarter, which goes to their deposits; their
spending does not depend on cash (financing limits are off), so GDP, consumption and investment move by less than
0.02 in the ratios. Government revenue falls by the same amount; government consumption follows its plan, not its
revenue, so the deficit widens (net lending of the government falls by about 5.7 points of GDP). Fixing this tax
alone moves the fiscal balance away from the data, because the other taxes raise too little (F7).

Usage:
    uv run python experiments/exp032_effective_profit_tax.py [--seeds 10] [--quarters 20]
"""

from scoring import Step, run_experiment
from settings import EFFECTIVE_PROFIT_TAX, NATIONAL_ACCOUNTS_RETURN

STEPS = [
    Step("defaults"),
    Step("effective profit tax (F7)", data=EFFECTIVE_PROFIT_TAX),
    Step(
        "effective profit tax, national-accounts return (F7, S9)",
        data={**EFFECTIVE_PROFIT_TAX, **NATIONAL_ACCOUNTS_RETURN},
    ),
]

if __name__ == "__main__":
    run_experiment(__file__, __doc__, STEPS)
