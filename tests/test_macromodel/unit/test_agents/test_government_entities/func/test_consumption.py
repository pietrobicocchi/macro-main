import numpy as np
import pytest

from macromodel.agents.government_entities.func.consumption import AutoregressiveGrowthGovernmentConsumptionSetter
from macromodel.forecaster.forecaster import ManualAutoregForecaster


def _planned_total(setter, history: np.ndarray, current_time: int) -> float:
    return setter.compute_target_consumption(
        previous_desired_government_consumption=np.ones(2),
        model=None,
        historic_total_consumption=history,
        initial_good_prices=np.ones(2),
        current_good_prices=np.ones(2),
        expected_growth=0.0,
        expected_inflation=0.0,
        current_time=current_time,
        exogenous_total_consumption=None,
        forecasting_window=60,
        assume_zero_noise=True,
    ).sum()


@pytest.fixture
def history() -> np.ndarray:
    growth = 0.004 + 0.002 * np.sin(np.arange(40))
    return 100.0 * np.cumprod(1.0 + growth)


def test_growth_plan_compounds_the_ar1_growth_forecast(history):
    """Regression: the planned growth rates were exponentiated as if they were log growth."""
    setter = AutoregressiveGrowthGovernmentConsumptionSetter(consistency=1.0, deflator="cpi")
    growth = history[1:] / history[:-1] - 1.0
    planned_growth = ManualAutoregForecaster().forecast(growth, t=2, assume_zero_noise=True)

    assert np.isclose(_planned_total(setter, history, 1), history[-1] * (1 + planned_growth[0]))
    assert np.isclose(_planned_total(setter, history, 2), history[-1] * np.prod(1 + planned_growth))


def test_growth_plan_is_made_again_when_it_runs_out(history):
    """Regression: the plan covered 20 quarters and longer runs failed with an IndexError."""
    setter = AutoregressiveGrowthGovernmentConsumptionSetter(consistency=1.0)
    for t in range(1, setter.buffer + 1):
        _planned_total(setter, history, t)
    longer_history = np.append(history, history[-1] * 1.01)

    planned = _planned_total(setter, longer_history, setter.buffer + 1)

    growth = longer_history[1:] / longer_history[:-1] - 1.0
    next_growth = ManualAutoregForecaster().forecast(growth, t=1, assume_zero_noise=True)[0]
    assert np.isclose(planned, longer_history[-1] * (1 + next_growth))
    assert setter.deflator == "ppi"
