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


def spare_capacity(c: CountryConfiguration) -> None:
    """Paper: omega^K = omega^M = 0.85. Changes initial stocks (see module docstring)."""
    c.firms.parameters.capital_inputs_utilisation_rate = OMEGA
    c.firms.parameters.intermediate_inputs_utilisation_rate = OMEGA


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
