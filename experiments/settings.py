"""Named configuration changes shared by experiments, organised by modelling decision (PROJECT.md).

Each function edits a CountryConfiguration in place and stands for one modelling choice, so experiments can apply
them one at a time or combine them. Sections:
1. The ablation ladder: today's defaults rebuilt one decision at a time from the model before our decisions.
2. Reverts to earlier defaults (`pre_md*`, `old_price_noise`).
3. Alternatives explored, by register issue (growth G, prices P, labour, government F, rest of the world).
Values marked "paper" are from the submitted manuscript: Table `table:prior` (NPE posterior, Austria) and the
appendix (`appendix_model_description.tex`).

Settings that change initial stocks (utilisation rates, inventory target) must also be built into the data: give
`scoring.Step(data=...)` or `scoring.load_data(...)` matching values, or the simulation takes the broken
re-initialisation path (S3).
"""

import copy

from scoring import Step

from macromodel.configurations import CountryConfiguration
from macromodel.configurations.row_configuration import RestOfTheWorldConfiguration

# Paper posterior (Table table:prior)
PHI_STY, CHI_H, CHI_M, CHI_K = 0.10, 0.53, 0.03, 0.18
# Paper appendix: initial utilisation rates, stock top-up weights
OMEGA, PHI_STOCK = 0.85, 1.0
DEFAULTS = CountryConfiguration()


# 1. The ablation ladder ----------------------------------------------------------------------------------------------


def restore(c: CountryConfiguration, path: str, keys: list[str] | None = None) -> None:
    """Set the configuration at dotted `path` (or only `keys` of a parameter dict there) to today's default."""
    *parents, last = path.split(".")
    target, default = c, DEFAULTS
    for name in parents:
        target, default = getattr(target, name), getattr(default, name)
    value = copy.deepcopy(getattr(default, last))
    if keys is not None:
        value = {**getattr(target, last), **{key: value[key] for key in keys}}
    setattr(target, last, value)


def before_our_decisions(c: CountryConfiguration) -> None:
    """The model as forked, with our accounting fixes (MD2-MD5, MD7, MD8) but none of our behavioural decisions."""
    pre_md16_government_consumption(c)
    pre_md15_no_growth_engine(c)
    pre_md14_prices_wages_consumption(c)
    old_price_noise(c)


def poledna_like(c: CountryConfiguration) -> None:
    """The IIASA model's rules where the code has them (paper `table:comp_to_iiasa`), for the ladder's bottom rung:
    production that substitutes between inputs (`Linear`), no housing market, firm loans only (no consumer loans or
    mortgages), Poledna's labour market without reservation wages, and Poledna's Taylor rule. Not switchable yet:
    one bank, fixed-markup loan rates, fixed-fraction consumption without household heterogeneity
    (`PolednaCreditMarketClearer` no longer fits the credit market's interface: E15)."""
    c.firms.functions.production.name = "Linear"
    c.housing_market.functions.clearing.name = "NoHousingMarketClearer"
    k = c.credit_market.functions.clearing.parameters
    c.credit_market.functions.clearing.parameters = {**k, "allow_household_loans": False}
    c.labour_market.functions.clearing.name = "PolednaLabourMarketClearer"
    m = c.labour_market.functions.clearing.parameters
    c.labour_market.functions.clearing.parameters = {
        **{k: v for k, v in m.items() if k not in ("matching_efficiency", "matching_elasticity")},
        "random_firing_probability": 0.0,
        "consider_reservation_wages": False,
    }
    c.central_bank.functions.policy_rate.name = "PolednaPolicyRate"


def md1_price_noise(c: CountryConfiguration) -> None:
    restore(c, "firms.functions.prices.parameters", ["price_setting_noise_std"])


def md14_costs_wages_consumption(c: CountryConfiguration) -> None:
    restore(c, "firms.functions.prices.parameters", ["price_setting_speed_gf", "price_setting_speed_cp"])
    restore(c, "firms.functions.wage_setter.parameters", ["cpi_indexation_speed"])
    restore(c, "households.functions.consumption.parameters", ["minimum_consumption_fraction"])


def md15_spare_capacity_and_growth_expectations(c: CountryConfiguration) -> None:
    restore(c, "firms.parameters.capital_inputs_utilisation_rate")
    restore(c, "firms.parameters.intermediate_inputs_utilisation_rate")
    restore(c, "firms.functions.demand_estimator")


def md10_investment(c: CountryConfiguration) -> None:
    restore(c, "firms.functions.target_capital_inputs")
    restore(c, "firms.functions.target_production")


def md11_search_frictions(c: CountryConfiguration) -> None:
    restore(c, "labour_market.functions.clearing")


def md12_productivity_growth(c: CountryConfiguration) -> None:
    restore(c, "firms.functions.productivity_growth")


def md13_slack_aware_expectations(c: CountryConfiguration) -> None:
    restore(c, "economy.functions.growth")


def md15_deterministic_forecasts(c: CountryConfiguration) -> None:
    restore(c, "assume_zero_noise")


def md16_government_plan(c: CountryConfiguration) -> None:
    restore(c, "government_entities.functions.consumption")


def paper_leontief_production(c: CountryConfiguration) -> None:
    restore(c, "firms.functions.production")


def paper_housing_market(c: CountryConfiguration) -> None:
    restore(c, "housing_market.functions.clearing")


def paper_household_credit(c: CountryConfiguration) -> None:
    restore(c, "credit_market.functions.clearing.parameters", ["allow_household_loans"])


def paper_reservation_wages(c: CountryConfiguration) -> None:
    restore(c, "labour_market.functions.clearing.parameters", ["consider_reservation_wages"])


def forked_constant_policy_rate(c: CountryConfiguration) -> None:
    restore(c, "central_bank.functions.policy_rate")


# Cumulative rungs: (label, change added, data the rung's initial state needs). P-rungs add the paper's innovations
# over the IIASA model (`table:comp_to_iiasa`) to an IIASA-like model; numbered rungs add our decisions to the model
# as forked. The last rung is today's defaults.
_FORKED_DATA = {"utilisation_rate": 1.0, "labour_share_from_sea": False}
_RUNGS = [
    ("P0 IIASA-like rules", None, _FORKED_DATA),
    ("P1 + Leontief production", paper_leontief_production, _FORKED_DATA),
    ("P2 + housing market", paper_housing_market, _FORKED_DATA),
    ("P3 + consumer loans and mortgages", paper_household_credit, _FORKED_DATA),
    ("P4 + reservation wages", paper_reservation_wages, _FORKED_DATA),
    ("0 + constant policy rate (model as forked)", forked_constant_policy_rate, _FORKED_DATA),
    ("1 + MD1 price noise 0.05%", md1_price_noise, _FORKED_DATA),
    ("2 + MD9 wages from SEA labour shares", None, {"utilisation_rate": 1.0}),
    ("3 + MD14 cost pass-through, wage catch-up, no floor", md14_costs_wages_consumption, {"utilisation_rate": 1.0}),
    ("4 + MD15 spare capacity, growth expectations", md15_spare_capacity_and_growth_expectations, {}),
    ("5 + MD10 partial-adjustment investment", md10_investment, {}),
    ("6 + MD11 search frictions", md11_search_frictions, {}),
    ("7 + MD12 productivity growth", md12_productivity_growth, {}),
    ("8 + MD13 slack-aware expectations", md13_slack_aware_expectations, {}),
    ("9 + MD15 deterministic forecasts", md15_deterministic_forecasts, {}),
    ("10 + MD16 government plan (defaults)", md16_government_plan, {}),
]
LADDER = [
    Step(label, [before_our_decisions, poledna_like] + [change for _, change, _ in _RUNGS[: k + 1] if change], data)
    for k, (label, _, data) in enumerate(_RUNGS)
]


# Leave-one-out: today's defaults without one element (exp025), the order-free complement of the ladder


def without_growth_expectations(c: CountryConfiguration) -> None:
    c.firms.functions.demand_estimator.parameters = {
        **c.firms.functions.demand_estimator.parameters,
        "sectoral_growth_adjustment_speed": 0.0,
    }


def without_partial_adjustment_investment(c: CountryConfiguration) -> None:
    c.firms.functions.target_capital_inputs.name = "FinancialTargetCapitalInputsSetter"
    c.firms.functions.target_capital_inputs.parameters = {
        "target_capital_inputs_fraction": 0.0,
        "credit_gap_fraction": 0.0,
    }
    p = c.firms.functions.target_production.parameters
    c.firms.functions.target_production.parameters = {**p, "capital_inputs_target_considers_capital_inputs": 1.0}


def without_search_frictions(c: CountryConfiguration) -> None:
    c.labour_market.functions.clearing.name = "PolednaLabourMarketClearer"
    m = c.labour_market.functions.clearing.parameters
    c.labour_market.functions.clearing.parameters = {
        **{k: v for k, v in m.items() if k not in ("matching_efficiency", "matching_elasticity")},
        "random_firing_probability": 0.0,
    }


def without_productivity_growth(c: CountryConfiguration) -> None:
    c.firms.functions.productivity_growth.name = "NoOpTFPGrowth"
    c.firms.functions.productivity_growth.parameters = {}


def without_slack_aware_expectations(c: CountryConfiguration) -> None:
    c.economy.functions.growth.name = "GrowthManualForecastingAutoReg"
    c.economy.functions.growth.parameters = {"value": 0.0, "lags": 1}


def with_forecast_noise(c: CountryConfiguration) -> None:
    c.assume_zero_noise = False


def substitutable_inputs(c: CountryConfiguration) -> None:
    c.firms.functions.production.name = "Linear"


def without_housing_market(c: CountryConfiguration) -> None:
    c.housing_market.functions.clearing.name = "NoHousingMarketClearer"


def without_household_credit(c: CountryConfiguration) -> None:
    k = c.credit_market.functions.clearing.parameters
    c.credit_market.functions.clearing.parameters = {**k, "allow_household_loans": False}


def without_reservation_wages(c: CountryConfiguration) -> None:
    m = c.labour_market.functions.clearing.parameters
    c.labour_market.functions.clearing.parameters = {**m, "consider_reservation_wages": False}


# 2. Reverts to earlier defaults --------------------------------------------------------------------------------------


def old_price_noise(c: CountryConfiguration) -> None:
    """The default before 2026-10-20 (MD1), kept as exp002's starting point."""
    p = c.firms.functions.prices.parameters
    c.firms.functions.prices.parameters = {**p, "price_setting_noise_std": 0.05}


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


def pre_md16_government_consumption(c: CountryConfiguration) -> None:
    """The default before MD16 (2026-10-22): the government plans an AR(1) on log levels of PPI-deflated spending."""
    government_consumption_plan(c, growth_rates=False, deflator="ppi")


# 3. Alternatives explored --------------------------------------------------------------------------------------------

# Growth and firm behaviour (G)


def growth_expectations(c: CountryConfiguration) -> None:
    """Paper: Q_f = (1 + gamma_s) (1 + phi^Q_F gamma_f) Q_f(t-1), with phi^Q_F = 0 (default since MD15)."""
    c.firms.functions.demand_estimator.parameters = {
        "firm_growth_adjustment_speed": 0.0,
        "sectoral_growth_adjustment_speed": 1.0,
    }


def spare_capacity(c: CountryConfiguration, rate: float = OMEGA) -> None:
    """Paper: omega^K = omega^M = 0.85 (default since MD15). Changes initial stocks (see module docstring)."""
    c.firms.parameters.capital_inputs_utilisation_rate = rate
    c.firms.parameters.intermediate_inputs_utilisation_rate = rate


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


def paper_target_production(
    c: CountryConfiguration, chi_h: float = CHI_H, chi_m: float = CHI_M, chi_k: float = CHI_K
) -> None:
    """Paper (`eq:firm_target_production`, G4): target production capped by labour, intermediate inputs and capital
    with weights chi (posterior 0.53, 0.03, 0.18), in place of the code's caps on purchases and hiring."""
    c.firms.functions.target_production.name = "PaperTargetProductionSetter"
    c.firms.functions.target_production.parameters = {
        **c.firms.functions.target_production.parameters,
        "target_production_considers_labour_inputs": chi_h,
        "target_production_considers_intermediate_inputs": chi_m,
        "target_production_considers_capital_inputs": chi_k,
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


def stock_top_up(c: CountryConfiguration) -> None:
    """Paper: phi^K = phi^M = 1. Explodes as implemented (G2)."""
    k = c.firms.functions.target_capital_inputs.parameters
    c.firms.functions.target_capital_inputs.parameters = {**k, "target_capital_inputs_fraction": PHI_STOCK}
    m = c.firms.functions.target_intermediate_inputs.parameters
    c.firms.functions.target_intermediate_inputs.parameters = {**m, "target_intermediate_inputs_fraction": PHI_STOCK}


def investment_engine(
    c: CountryConfiguration,
    adjustment_speed: float = 0.25,
    demand_smoothing: float = 1.0,
    credit_gap_fraction: float = 0.0,
) -> None:
    """Flexible-accelerator investment (MD10; default since MD15 with 0.10 and 0.10): capital purchases are
    replacement plus a fraction of the gap to desired capital, planned on expected demand rather than capped by
    current capacity."""
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


def labour_productivity_growth(c: CountryConfiguration, rate: float = 0.0025) -> None:
    """Labour-augmenting technical progress (G14, MD12): output per worker grows at `rate` per quarter in every
    industry, and real wages per worker grow with it. 0.0025 is about 1% a year, France's output per person employed
    in the 2000s-2010s (to verify against OECD data: the bundled sample has no employment series)."""
    c.firms.functions.productivity_growth.name = "LabourAugmentingGrowth"
    c.firms.functions.productivity_growth.parameters = {"labour_productivity_growth": rate}


def growth_forecast_data_only(c: CountryConfiguration) -> None:
    """Firms' expected growth is the AR(1) forecast from pre-simulation data only, h quarters ahead (G16): it does
    not feed on the growth the simulation produces. No lookahead: only data before the start is used."""
    c.economy.functions.growth.name = "DataOnlyGrowthForecastingAutoReg"
    c.economy.functions.growth.parameters = {"lags": 1}


def growth_forecast_slack_aware(c: CountryConfiguration, sensitivity: float = 0.2) -> None:
    """Expected growth falls when unemployment is below its initial level (G16, MD13): AR(1) forecast minus
    `sensitivity` times the gap. 0.2 = Okun coefficient 2 times a 10% quarterly closing of the output gap."""
    c.economy.functions.growth.name = "SlackAwareGrowthForecastingAutoReg"
    c.economy.functions.growth.parameters = {"lags": 1, "slack_sensitivity": sensitivity}


def no_growth(c: CountryConfiguration) -> None:
    """No source of growth: no productivity growth and a constant zero growth forecast. The initial state should then
    be (close to) a fixed point."""
    c.firms.functions.productivity_growth.name = "NoOpTFPGrowth"
    c.firms.functions.productivity_growth.parameters = {}
    c.economy.functions.growth.name = "GrowthForecastingConstant"
    c.economy.functions.growth.parameters = {"value": 0.0, "lags": 1}


def work_effort_cap(c: CountryConfiguration, cap: float = 1.1) -> None:
    """Most extra output per worker from effort and overtime (G12; default allows +50%)."""
    p = c.firms.functions.labour_productivity.parameters
    c.firms.functions.labour_productivity.parameters = {**p, "max_increase_in_work_effort": cap}


# Prices, wages and expectations (P)


def no_price_noise(c: CountryConfiguration) -> None:
    """Paper: eq. firm_prices has no noise term."""
    p = c.firms.functions.prices.parameters
    c.firms.functions.prices.parameters = {**p, "price_setting_noise_std": 0.0}


def no_forecast_noise(c: CountryConfiguration) -> None:
    """Drop the random draw added to the AR(1) growth and inflation forecasts (P3; default since MD15)."""
    c.assume_zero_noise = True


def price_brakes(c: CountryConfiguration, cost_pass_through: float = 0.5, demand_pull: float = 0.0) -> None:
    """Prices follow costs and demand, not only the inflation forecast (P5, MD14): a share `cost_pass_through` of
    unit-cost growth replaces the same share of expected inflation (weights sum to one, so steady inflation is
    unchanged), and firms with excess demand raise prices by `demand_pull` times it."""
    p = c.firms.functions.prices.parameters
    c.firms.functions.prices.parameters = {
        **p,
        "price_setting_speed_gf": 1.0 - cost_pass_through,
        "price_setting_speed_cp": cost_pass_through,
        "price_setting_speed_dp": demand_pull,
    }


def lagged_wage_indexation(c: CountryConfiguration, speed: float = 0.25) -> None:
    """Nominal wages catch up with prices gradually (G17, MD14): each quarter they close `speed` of the gap between
    their price index and the latest CPI (1: last quarter's CPI in full). 0.25 is about one wage round a year."""
    p = c.firms.functions.wage_setter.parameters
    c.firms.functions.wage_setter.parameters = {**p, "cpi_indexation_speed": speed}


def wage_phillips_curve(c: CountryConfiguration, sensitivity: float = 0.1) -> None:
    """Nominal wages grow faster when unemployment is below its initial level (P2): each quarter by `sensitivity`
    times the gap. 0.1 a quarter is about 0.4 points of annual wage growth per point of unemployment."""
    p = c.firms.functions.wage_setter.parameters
    c.firms.functions.wage_setter.parameters = {**p, "unemployment_gap_sensitivity": sensitivity}


def wage_brake(c: CountryConfiguration, tightness_scale: float = 0.5) -> None:
    """Existing employees' wages rise with their firm's recent hiring shortfalls (G8), as offered wages already do."""
    p = c.firms.functions.wage_setter.parameters
    c.firms.functions.wage_setter.parameters = {**p, "labour_market_tightness_markup_scale": tightness_scale}


def taylor_rule(c: CountryConfiguration) -> None:
    """Paper: the policy rate follows a Taylor rule estimated by OLS (`eq:cb_policy_rate`; P4)."""
    c.central_bank.functions.policy_rate.name = "PolednaPolicyRate"


# Labour market (MD11)


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
    The default (MD15) calibrates mu to the initial unemployment rate in the clearer itself.
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


def separation_rate(c: CountryConfiguration, rate: float) -> None:
    """Share of employees separating into unemployment each quarter (MD11, default 0.03); the matching efficiency is
    recalibrated so the initial unemployment rate stays a steady state."""
    p = c.labour_market.functions.clearing.parameters
    c.labour_market.functions.clearing.parameters = {
        **p,
        "random_firing_probability": rate,
        "matching_efficiency": None,
    }


# Households, government and finance (F, S)


def no_consumption_floor(c: CountryConfiguration) -> None:
    """Drop the consumption floor of (1 - saving rate) x benefits (S26, MD14): it counts every adult as receiving
    unemployment benefit, exceeds the income of 40% of households, and was not in the initial state, so consumption
    jumped 7% in the first quarter."""
    p = c.households.functions.consumption.parameters
    c.households.functions.consumption.parameters = {**p, "minimum_consumption_fraction": 0.0}


def firm_shares(c: CountryConfiguration) -> None:
    """Households' other financial assets are shares in firms paying dividends (MD6)."""
    c.households.functions.financial_assets.name = "FirmSharesFinancialAssets"


def government_consumption_plan(c: CountryConfiguration, growth_rates: bool = True, deflator: str = "cpi") -> None:
    """The government plans real consumption from an AR(1) fitted on its past growth rates (`growth_rates`) rather
    than on log levels, which mean-revert so planned growth fades; history deflated by `deflator` ("cpi" or "ppi").
    Default since MD16: growth rates, CPI."""
    c.government_entities.functions.consumption.name = (
        "AutoregressiveGrowthGovernmentConsumptionSetter"
        if growth_rates
        else "AutoregressiveGovernmentConsumptionSetter"
    )
    c.government_entities.functions.consumption.parameters = {"consistency": 1.0, "deflator": deflator}


def paper_bank_limits(c: CountryConfiguration) -> None:
    """Paper appendix bank parameters (G9)."""
    b = c.banks.parameters
    b.firm_loans_debt_to_equity_ratio = 1.0
    b.firm_loans_return_on_equity_ratio = 0.15
    b.firm_loans_return_on_assets_ratio = 0.05
    b.household_consumption_loans_loan_to_income_ratio = 0.36


# Rest of the world (M15)


def row_no_forecast_noise(r: RestOfTheWorldConfiguration) -> None:
    """The rest of the world's forecasts without a random draw, like the country's since MD15 (P3)."""
    r.assume_zero_noise = True
