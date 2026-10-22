"""exp025: Which elements of today's defaults matter, independent of the order they were added? (R1.1, R2.1)

Leave-one-out complement of the ablation ladder (exp023, one order only): today's defaults without one element at a
time, our decisions and the paper's innovations over the IIASA model, plus two additions not in the defaults (the
paper's Taylor rule, cash social benefits F6). Hypothesis (recorded before running): deterministic forecasts and the
price-noise fix matter most for the ratios, spare capacity and productivity growth for growth and unemployment; the
paper's housing and household-credit innovations matter little on France's sample data (dormant in exp023).

Usage:
    uv run python experiments/exp025_leave_one_out.py [--seeds 10] [--quarters 20]
"""

from functools import partial

from scoring import Step, run_experiment
from settings import (
    old_price_noise,
    pre_md14_prices_wages_consumption,
    pre_md16_government_consumption,
    spare_capacity,
    substitutable_inputs,
    taylor_rule,
    with_forecast_noise,
    without_growth_expectations,
    without_household_credit,
    without_housing_market,
    without_partial_adjustment_investment,
    without_productivity_growth,
    without_reservation_wages,
    without_search_frictions,
    without_slack_aware_expectations,
)

STEPS = [
    Step("defaults"),
    Step("without deterministic forecasts (MD15)", [with_forecast_noise]),
    Step("without the price-noise fix (MD1)", [old_price_noise]),
    Step("without MD14 (cost pass-through, wage catch-up, no floor)", [pre_md14_prices_wages_consumption]),
    Step("without spare capacity (MD15)", [partial(spare_capacity, rate=1.0)], {"utilisation_rate": 1.0}),
    Step("without growth expectations (MD15)", [without_growth_expectations]),
    Step("without partial-adjustment investment (MD10)", [without_partial_adjustment_investment]),
    Step("without search frictions (MD11)", [without_search_frictions]),
    Step("without productivity growth (MD12)", [without_productivity_growth]),
    Step("without slack-aware expectations (MD13)", [without_slack_aware_expectations]),
    Step("without the government plan (MD16)", [pre_md16_government_consumption]),
    Step("without SEA labour shares (MD9)", data={"labour_share_from_sea": False}),
    Step("without Leontief production (paper)", [substitutable_inputs]),
    Step("without the housing market (paper)", [without_housing_market]),
    Step("without household credit (paper)", [without_household_credit]),
    Step("without reservation wages (paper)", [without_reservation_wages]),
    Step("with the Taylor rule (paper)", [taylor_rule]),
    Step("with cash social benefits (F6)", data={"cash_social_benefits": True}),
]

if __name__ == "__main__":
    run_experiment(__file__, __doc__, STEPS)
