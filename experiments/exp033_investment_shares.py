"""exp033: Firms' investment split by capital compensation (S32)

Firms' investment is split across industries in proportion to SEA capital compensation divided by the investment in
each industry's *product*, so industries whose products are rarely capital goods (accommodation and food I, water
and waste E, mining B, energy D) get most of it, up to a cap of 93% of their value added in capital costs, and start
loss-making (profit / sales I −28.5%, E −17.6%, B −13.9%, D −0.4%). The data option splits it by capital
compensation over its total: capital costs are then 13–31% of value added in those industries, 46% in real estate,
and no industry starts with a loss; totals do not change. Steps: defaults; the option.
Hypothesis (recorded before running): the periodic default of firm I (every 8 quarters, t = 9 and 17), its bank's
loss and the spikes in firms' and banks' net lending disappear. Aggregate ratios move little (the total of capital
costs and of investment by product is unchanged), but the sectoral pattern of capital purchases changes, so
investment growth may shift.

Usage:
    uv run python experiments/exp033_investment_shares.py [--seeds 10] [--quarters 20]
"""

from scoring import Step, run_experiment
from settings import INVESTMENT_BY_CAPITAL_COMPENSATION

STEPS = [
    Step("defaults"),
    Step("investment split by capital compensation (S32)", data=INVESTMENT_BY_CAPITAL_COMPENSATION),
]

if __name__ == "__main__":
    run_experiment(__file__, __doc__, STEPS)
