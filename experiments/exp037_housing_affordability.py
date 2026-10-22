"""exp037: Can households rent? Affordability in the housing market (M2)

No house is ever newly rented. A household that decides to rent can pay up to 0.2 money units whatever its income
(`maximum_rent_income_coefficient` 0.2, exponent 0), so it never finds a home; a household that decides to buy can pay
up to 5 times its quarterly income (about 47,000 euros against a median home of 161,000), and the buy-or-rent logit
saturates (sensitivity 1 per euro against the paper's 0.001), so every household deciding chooses to buy. Steps:
defaults; rent up to 25% of quarterly income; with purchases up to 5 years of income; with the paper's sensitivity
0.001; with the paper's moving probabilities (exp034); and rent affordability with the moving probabilities only.
Hypothesis (recorded before running): rent affordability alone changes little, since the logit still sends every
decider to buy; with purchases of 5 years of income the cost of buying (loan principal) rises relative to the rent of
a home of that value, and with the paper's sensitivity some deciders rent, so new rentals become positive (of the
order of 1% of the stock a quarter) and sales fall. Macro ratios move little (rents and house purchases are transfers
between households), except through mortgages.

Usage:
    uv run python experiments/exp037_housing_affordability.py [--seeds 10] [--quarters 20]
"""

from scoring import Step, run_experiment
from settings import (
    paper_buy_or_rent_sensitivity,
    paper_moving_probabilities,
    purchase_affordability,
    rent_affordability,
)

STEPS = [
    Step("defaults"),
    Step("rent up to 25% of income", [rent_affordability]),
    Step("+ purchases up to 5 years of income", [rent_affordability, purchase_affordability]),
    Step(
        "+ paper's buy-or-rent sensitivity", [rent_affordability, purchase_affordability, paper_buy_or_rent_sensitivity]
    ),
    Step("rent up to 25% of income, paper's moving probabilities", [rent_affordability, paper_moving_probabilities]),
    Step(
        "+ paper's moving probabilities",
        [rent_affordability, purchase_affordability, paper_buy_or_rent_sensitivity, paper_moving_probabilities],
    ),
]

if __name__ == "__main__":
    run_experiment(__file__, __doc__, STEPS)
