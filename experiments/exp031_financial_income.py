"""exp031: Households' financial income at the national accounts' level (S9, S31, G18; next step 2)

Households earn a return on their other financial assets (about 2.5 times annual GDP) that nobody pays. The return
comes from the spoofed survey: 1.9% a quarter, so the income is 19% of quarterly GDP (about 103 bn a quarter). French
households' property income net of interest was 20.7 bn a quarter in 2014 (Eurostat D4 - D41; interest is paid
separately on deposits). The option sets the return so the income matches it: 0.39% a quarter. Steps: defaults; the
national accounts' return; the fixed-point check of exp022 (no productivity growth, zero growth forecast, no
government trend), with each return.
Hypothesis (recorded before running): household income falls by about 15% of GDP while initial consumption is
unchanged (it is matched to the input-output tables), so the saving rate falls from about 30% towards France's 15%.
Household consumption then grows more slowly: its drift in the fixed-point run (0.2%/q, income compounding on
savings, G18) mostly disappears, and the economy is closer to a fixed point. In the default run GDP and household
consumption growth fall, unemployment ends higher; the ratios move by a few hundredths.

Usage:
    uv run python experiments/exp031_financial_income.py [--seeds 10] [--quarters 20]
"""

from scoring import Step, run_experiment
from settings import NATIONAL_ACCOUNTS_RETURN, government_no_growth, no_growth

STEPS = [
    Step("defaults"),
    Step("return from national accounts (S9)", data=NATIONAL_ACCOUNTS_RETURN),
    Step("no growth sources", [no_growth, government_no_growth]),
    Step("no growth sources, national accounts return", [no_growth, government_no_growth], NATIONAL_ACCOUNTS_RETURN),
]

if __name__ == "__main__":
    run_experiment(__file__, __doc__, STEPS)
