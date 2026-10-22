"""Named configuration changes shared by experiments.

Each function edits a CountryConfiguration in place and stands for one modelling choice,
so experiments can apply them one at a time (ablations) or combine them. Values marked
"paper" are from the submitted manuscript: Table `table:prior` (NPE posterior, Austria),
eqs. `firm_exp_demand_main`, `firm_target_production_main`, `firm_prices`,
`firm_target_capital_inputs`, and the appendix parameter sections.

Settings that change initial stocks (utilisation rates, inventory target) must also be
built into the data: use `scoring.load_data(utilisation_rate=..., inventory_fraction=...)`
with matching values, or the simulation takes the broken re-initialisation path (S3).
"""

from macromodel.configurations import CountryConfiguration
from macromodel.configurations.row_configuration import RestOfTheWorldConfiguration

# Paper posterior (Table table:prior)
PHI_STY, CHI_H, CHI_M, CHI_K = 0.10, 0.53, 0.03, 0.18
# Paper appendix: initial utilisation rates, stock top-up weights
OMEGA, PHI_STOCK = 0.85, 1.0


def growth_expectations(c: CountryConfiguration) -> None:
    """Paper: Q_f = (1 + gamma_s) (1 + phi^Q_F gamma_f) Q_f(t-1), with phi^Q_F = 0."""
    c.firms.functions.demand_estimator.parameters = {
        "firm_growth_adjustment_speed": 0.0,
        "sectoral_growth_adjustment_speed": 1.0,
    }


def inventory(c: CountryConfiguration) -> None:
    """Paper: Y_hat = Q_f + phi^StY Y_f(t-1) - S_f(t-1). Changes initial stocks (see module docstring)."""
    p = c.firms.functions.target_production.parameters
    c.firms.functions.target_production.parameters = {
        **p,
        "existing_inventory_fraction": 1.0,
        "target_inventory_to_production_fraction": PHI_STY,
    }


def input_constraints(c: CountryConfiguration) -> None:
    """Paper chi values. The paper caps target production; the code caps labour demand and
    intermediate/capital purchases separately, so the same values are applied to each (G4)."""
    p = c.firms.functions.target_production.parameters
    c.firms.functions.target_production.parameters = {
        **p,
        **{
            f"{target}_target_considers_{inputs}": weight
            for target in ["intermediate_inputs", "capital_inputs"]
            for inputs, weight in [("labour_inputs", CHI_H), ("intermediate_inputs", CHI_M), ("capital_inputs", CHI_K)]
        },
    }
    c.firms.functions.desired_labour.parameters = {
        "consider_intermediate_inputs": CHI_M,
        "consider_capital_inputs": CHI_K,
    }


def capital_constraint(c: CountryConfiguration, weight: float) -> None:
    """How fully capital capacity caps labour demand and input purchases (default 1.0)."""
    p = c.firms.functions.target_production.parameters
    c.firms.functions.target_production.parameters = {
        **p,
        "intermediate_inputs_target_considers_capital_inputs": weight,
        "capital_inputs_target_considers_capital_inputs": weight,
    }
    d = c.firms.functions.desired_labour.parameters
    c.firms.functions.desired_labour.parameters = {**d, "consider_capital_inputs": weight}


def old_price_noise(c: CountryConfiguration) -> None:
    """The default before 2026-10-20 (MD1), kept as exp002's starting point."""
    p = c.firms.functions.prices.parameters
    c.firms.functions.prices.parameters = {**p, "price_setting_noise_std": 0.05}


def no_price_noise(c: CountryConfiguration) -> None:
    """Paper: eq. firm_prices has no noise term."""
    p = c.firms.functions.prices.parameters
    c.firms.functions.prices.parameters = {**p, "price_setting_noise_std": 0.0}


def paper_bank_limits(c: CountryConfiguration) -> None:
    """Paper appendix bank parameters."""
    b = c.banks.parameters
    b.firm_loans_debt_to_equity_ratio = 1.0
    b.firm_loans_return_on_equity_ratio = 0.15
    b.firm_loans_return_on_assets_ratio = 0.05
    b.household_consumption_loans_loan_to_income_ratio = 0.36


def taylor_rule(c: CountryConfiguration) -> None:
    c.central_bank.functions.policy_rate.name = "PolednaPolicyRate"


def spare_capacity(c: CountryConfiguration, rate: float = OMEGA) -> None:
    """Paper: omega^K = omega^M = 0.85 (default since MD15). Changes initial stocks (see module docstring)."""
    c.firms.parameters.capital_inputs_utilisation_rate = rate
    c.firms.parameters.intermediate_inputs_utilisation_rate = rate


def stock_top_up(c: CountryConfiguration) -> None:
    """Paper: phi^K = phi^M = 1. Explodes as implemented (G2)."""
    k = c.firms.functions.target_capital_inputs.parameters
    c.firms.functions.target_capital_inputs.parameters = {**k, "target_capital_inputs_fraction": PHI_STOCK}
    m = c.firms.functions.target_intermediate_inputs.parameters
    c.firms.functions.target_intermediate_inputs.parameters = {**m, "target_intermediate_inputs_fraction": PHI_STOCK}


def no_forecast_noise(c: CountryConfiguration) -> None:
    """Drop the random draw added to the AR(1) growth and inflation forecasts (P3)."""
    c.assume_zero_noise = True


def investment_engine(
    c: CountryConfiguration,
    adjustment_speed: float = 0.25,
    demand_smoothing: float = 1.0,
    credit_gap_fraction: float = 0.0,
) -> None:
    """Flexible-accelerator investment (MD10 candidate): capital purchases are replacement plus a fraction of the gap
    to desired capital, planned on expected demand rather than capped by current capacity."""
    c.firms.functions.target_capital_inputs.name = "PartialAdjustmentTargetCapitalInputsSetter"
    c.firms.functions.target_capital_inputs.parameters = {
        "capital_gap_adjustment_speed": adjustment_speed,
        "demand_smoothing": demand_smoothing,  # G10: smoothed demand sizes desired capital
        "credit_gap_fraction": credit_gap_fraction,  # G9: purchases cut by credit applied for but not received
    }
    p = c.firms.functions.target_production.parameters
    c.firms.functions.target_production.parameters = {
        **p,
        "capital_inputs_target_considers_labour_inputs": 0.0,
        "capital_inputs_target_considers_intermediate_inputs": 0.0,
        "capital_inputs_target_considers_capital_inputs": 0.0,
    }


def firm_shares(c: CountryConfiguration) -> None:
    """Households' other financial assets are shares in firms paying dividends (MD6)."""
    c.households.functions.financial_assets.name = "FirmSharesFinancialAssets"


def wage_brake(c: CountryConfiguration, tightness_scale: float = 0.5) -> None:
    """Existing employees' wages rise with their firm's recent hiring shortfalls (G8), as offered wages already do."""
    p = c.firms.functions.wage_setter.parameters
    c.firms.functions.wage_setter.parameters = {**p, "labour_market_tightness_markup_scale": tightness_scale}


def work_effort_cap(c: CountryConfiguration, cap: float = 1.1) -> None:
    """Most extra output per worker from effort and overtime (G12; default allows +50%)."""
    p = c.firms.functions.labour_productivity.parameters
    c.firms.functions.labour_productivity.parameters = {**p, "max_increase_in_work_effort": cap}


def search_frictions(
    c: CountryConfiguration,
    separation_rate: float = 0.03,
    matching_elasticity: float = 0.5,
    unemployment_rate: float = 0.103,
) -> None:
    """Labour-market search frictions (G13): a share of employees separates into unemployment each quarter, and hires
    are capped by a Cobb-Douglas matching function M = mu U^alpha V^(1 - alpha).

    mu makes `unemployment_rate` (France at t=0) a steady state. There, firms' vacancies are the replacements for
    separations, V = s E, the job seekers are the unemployed plus the newly separated, U + s E, and the market fills
    every vacancy, M = V. So mu = (V / (U + V))^alpha, and a job seeker finds a job within the quarter with
    probability V / (U + V) (0.21 at s = 0.03). alpha = 0.5 is the middle of the Petrongolo-Pissarides (2001) range.
    """
    u = unemployment_rate
    job_finding_rate = separation_rate * (1.0 - u) / (u + separation_rate * (1.0 - u))
    c.labour_market.functions.clearing.name = "SearchFrictionsLabourMarketClearer"
    p = c.labour_market.functions.clearing.parameters
    c.labour_market.functions.clearing.parameters = {
        **p,
        "random_firing_probability": separation_rate,
        "matching_efficiency": job_finding_rate**matching_elasticity,
        "matching_elasticity": matching_elasticity,
    }


def labour_productivity_growth(c: CountryConfiguration, rate: float = 0.0025) -> None:
    """Labour-augmenting technical progress (G14): output per worker grows at `rate` per quarter in every industry,
    and real wages per worker grow with it. 0.0025 is about 1% a year, France's output per person employed in the
    2000s-2010s (to verify against OECD data: the bundled sample has no employment series)."""
    c.firms.functions.productivity_growth.name = "LabourAugmentingGrowth"
    c.firms.functions.productivity_growth.parameters = {"labour_productivity_growth": rate}


def price_brakes(c: CountryConfiguration, cost_pass_through: float = 0.5, demand_pull: float = 0.0) -> None:
    """Prices follow costs and demand, not only the inflation forecast (P5): a share `cost_pass_through` of unit-cost
    growth replaces the same share of expected inflation (weights sum to one, so steady inflation is unchanged), and
    firms with excess demand raise prices by `demand_pull` times it."""
    p = c.firms.functions.prices.parameters
    c.firms.functions.prices.parameters = {
        **p,
        "price_setting_speed_gf": 1.0 - cost_pass_through,
        "price_setting_speed_cp": cost_pass_through,
        "price_setting_speed_dp": demand_pull,
    }


def lagged_wage_indexation(c: CountryConfiguration, speed: float = 0.25) -> None:
    """Nominal wages catch up with prices gradually (G17): each quarter they close `speed` of the gap between their
    price index and the latest CPI (default 1: last quarter's CPI in full). 0.25 is about one wage round a year."""
    p = c.firms.functions.wage_setter.parameters
    c.firms.functions.wage_setter.parameters = {**p, "cpi_indexation_speed": speed}


def growth_forecast_data_only(c: CountryConfiguration) -> None:
    """Firms' expected growth is the AR(1) forecast from pre-simulation data only, h quarters ahead (G16): it does
    not feed on the growth the simulation produces. No lookahead: only data before the start is used."""
    c.economy.functions.growth.name = "DataOnlyGrowthForecastingAutoReg"
    c.economy.functions.growth.parameters = {"lags": 1}


def growth_forecast_slack_aware(c: CountryConfiguration, sensitivity: float = 0.2) -> None:
    """Expected growth falls when unemployment is below its initial level (G16): AR(1) forecast minus
    `sensitivity` times the gap. 0.2 = Okun coefficient 2 times a 10% quarterly closing of the output gap."""
    c.economy.functions.growth.name = "SlackAwareGrowthForecastingAutoReg"
    c.economy.functions.growth.parameters = {"lags": 1, "slack_sensitivity": sensitivity}


def no_consumption_floor(c: CountryConfiguration) -> None:
    """Drop the consumption floor of (1 - saving rate) x benefits (S26): it counts every adult as receiving
    unemployment benefit, exceeds the income of 40% of households, and was not in the initial state, so consumption
    jumped 7% in the first quarter."""
    p = c.households.functions.consumption.parameters
    c.households.functions.consumption.parameters = {**p, "minimum_consumption_fraction": 0.0}


def pre_md14_prices_wages_consumption(c: CountryConfiguration) -> None:
    """The defaults before MD14 (2026-10-21): prices follow expected inflation only, wages follow last quarter's CPI
    in full, and households consume at least (1 - saving rate) x benefits."""
    p = c.firms.functions.prices.parameters
    c.firms.functions.prices.parameters = {**p, "price_setting_speed_gf": 1.0, "price_setting_speed_cp": 0.0}
    w = c.firms.functions.wage_setter.parameters
    c.firms.functions.wage_setter.parameters = {**w, "cpi_indexation_speed": 1.0}
    h = c.households.functions.consumption.parameters
    c.households.functions.consumption.parameters = {**h, "minimum_consumption_fraction": 1.0}


def pre_md15_no_growth_engine(c: CountryConfiguration) -> None:
    """The defaults before MD15 (2026-10-21): firms at full capacity, capital purchases that replace depreciation
    only, no growth in expected demand, a frictionless labour market, no productivity growth, an AR(1) growth
    forecast on realised growth, and a random draw in every forecast. Build the data with
    `scoring.load_data(utilisation_rate=1.0)`."""
    c.firms.parameters.capital_inputs_utilisation_rate = 1.0
    c.firms.parameters.intermediate_inputs_utilisation_rate = 1.0
    c.firms.functions.demand_estimator.parameters = {
        "firm_growth_adjustment_speed": 0.0,
        "sectoral_growth_adjustment_speed": 0.0,
    }
    c.firms.functions.target_capital_inputs.name = "FinancialTargetCapitalInputsSetter"
    c.firms.functions.target_capital_inputs.parameters = {
        "target_capital_inputs_fraction": 0.0,
        "credit_gap_fraction": 0.0,
    }
    p = c.firms.functions.target_production.parameters
    c.firms.functions.target_production.parameters = {**p, "capital_inputs_target_considers_capital_inputs": 1.0}
    c.firms.functions.productivity_growth.name = "NoOpTFPGrowth"
    c.firms.functions.productivity_growth.parameters = {}
    c.labour_market.functions.clearing.name = "PolednaLabourMarketClearer"
    m = c.labour_market.functions.clearing.parameters
    c.labour_market.functions.clearing.parameters = {
        **{k: v for k, v in m.items() if k not in ("matching_efficiency", "matching_elasticity")},
        "random_firing_probability": 0.0,
    }
    c.economy.functions.growth.name = "GrowthManualForecastingAutoReg"
    c.economy.functions.growth.parameters = {"value": 0.0, "lags": 1}
    c.assume_zero_noise = False


def government_consumption_plan(c: CountryConfiguration, growth_rates: bool = True, deflator: str = "cpi") -> None:
    """The government plans real consumption from an AR(1) fitted on its past growth rates (`growth_rates`) rather
    than on log levels, which mean-revert so planned growth fades; history deflated by `deflator` ("cpi" or "ppi").
    The default fits log levels deflated by the PPI, which fell with oil prices in 2014-16."""
    c.government_entities.functions.consumption.name = (
        "AutoregressiveGrowthGovernmentConsumptionSetter"
        if growth_rates
        else "AutoregressiveGovernmentConsumptionSetter"
    )
    c.government_entities.functions.consumption.parameters = {"consistency": 1.0, "deflator": deflator}


def pre_md16_government_consumption(c: CountryConfiguration) -> None:
    """The default before MD16 (2026-10-22): the government plans an AR(1) on log levels of PPI-deflated spending."""
    government_consumption_plan(c, growth_rates=False, deflator="ppi")


def separation_rate(c: CountryConfiguration, rate: float) -> None:
    """Share of employees separating into unemployment each quarter (MD11, default 0.03); the matching efficiency is
    recalibrated so the initial unemployment rate stays a steady state."""
    p = c.labour_market.functions.clearing.parameters
    c.labour_market.functions.clearing.parameters = {
        **p,
        "random_firing_probability": rate,
        "matching_efficiency": None,
    }


def no_growth(c: CountryConfiguration) -> None:
    """No source of growth: no productivity growth and a constant zero growth forecast. The initial state should then
    be (close to) a fixed point."""
    c.firms.functions.productivity_growth.name = "NoOpTFPGrowth"
    c.firms.functions.productivity_growth.parameters = {}
    c.economy.functions.growth.name = "GrowthForecastingConstant"
    c.economy.functions.growth.parameters = {"value": 0.0, "lags": 1}


def row_no_forecast_noise(r: RestOfTheWorldConfiguration) -> None:
    """The rest of the world's forecasts without a random draw, like the country's since MD15 (P3)."""
    r.assume_zero_noise = True
