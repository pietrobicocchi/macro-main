"""exp034: The paper's housing parameters (M9, M14, M2)

Households reconsider their home with probability 0.5 a quarter, owners and renters alike; the paper uses 79/80 for
owners (20 years) and 7/8 for renters (2 years). Its psychological pressure of renting is 0.4 (default 0.1), and it
indexes rents to last quarter's CPI (the defaults keep rents constant, M14). Steps: defaults; the paper's moving
probabilities; with its renting pressure as well; with rents indexed to the CPI as well. (The paper's price and rent
cuts for unsold properties, 1 − exp(ε) with ε ~ N(1.45, 0.49), would cut by 80% or more and make rents negative, a
missing /100; they stay off. Its income elasticities for prices and rents are in units we cannot place.)
Hypothesis (recorded before running): with owners moving once in 20 years house sales fall from about 3% of the
stock a quarter towards the paper's 1%, and the rented stock stops shrinking as fast; rentals stay near zero, since
buying still looks far cheaper than renting (M2), and the pressure of renting only strengthens that. Macro ratios move
little: house purchases are transfers between households, except through mortgages and their repayments, which fall
with turnover, so household consumption may rise slightly.

Usage:
    uv run python experiments/exp034_paper_housing.py [--seeds 10] [--quarters 20]
"""

from scoring import Step, run_experiment
from settings import paper_moving_probabilities, paper_renting_pressure, rents_indexed_to_cpi

STEPS = [
    Step("defaults"),
    Step("paper's moving probabilities", [paper_moving_probabilities]),
    Step("+ renting pressure 0.4", [paper_moving_probabilities, paper_renting_pressure]),
    Step("+ rents indexed to the CPI", [paper_moving_probabilities, paper_renting_pressure, rents_indexed_to_cpi]),
]

if __name__ == "__main__":
    run_experiment(__file__, __doc__, STEPS)
