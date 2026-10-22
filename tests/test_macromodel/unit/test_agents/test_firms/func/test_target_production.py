import numpy as np

from macromodel.agents.firms.func.target_production import PaperTargetProductionSetter

BASE = dict(
    existing_inventory_fraction=0.0,
    target_inventory_to_production_fraction=0.0,
    financial_constrains_fraction=0.0,
    maximum_debt_to_equity_ratio=2.0,
    intermediate_inputs_target_considers_labour_inputs=0.0,
    intermediate_inputs_target_considers_intermediate_inputs=0.0,
    intermediate_inputs_target_considers_capital_inputs=0.0,
    capital_inputs_target_considers_labour_inputs=0.0,
    capital_inputs_target_considers_intermediate_inputs=0.0,
    capital_inputs_target_considers_capital_inputs=0.0,
)


def _target(setter, labour, intermediate, capital):
    zeros = np.zeros(1)
    return setter.compute_target_production(
        current_estimated_demand=np.array([10.0]),
        initial_inventory=zeros,
        previous_inventory=zeros,
        previous_production=np.array([10.0]),
        current_target_production=np.array([10.0]),
        current_limiting_intermediate_inputs=np.array([intermediate]),
        current_limiting_capital_inputs=np.array([capital]),
        current_firm_equity=np.ones(1),
        current_firm_debt=zeros,
        previous_loans_applied_for=zeros,
        current_firm_deposits=zeros,
        interest_on_overdraft_rates=zeros,
        interest_paid_on_loans=zeros,
        current_limiting_labour_inputs=np.array([labour]),
    )[0]


def test_paper_target_production_caps_by_each_input():
    """eq:firm_target_production: min over inputs of Q + chi (limit - Q); chi = 0 ignores the input."""
    setter = PaperTargetProductionSetter(
        target_production_considers_labour_inputs=0.5,
        target_production_considers_intermediate_inputs=0.0,
        target_production_considers_capital_inputs=1.0,
        **BASE,
    )
    assert np.isclose(_target(setter, labour=8.0, intermediate=1.0, capital=12.0), 9.0)  # labour: 10 + 0.5 (8 - 10)
    assert np.isclose(_target(setter, labour=20.0, intermediate=1.0, capital=9.5), 9.5)  # capital fully binding


def test_paper_target_production_without_chi_is_the_default_target():
    setter = PaperTargetProductionSetter(**BASE)
    assert np.isclose(_target(setter, labour=1.0, intermediate=1.0, capital=1.0), 10.0)
