import numpy as np

from macromodel.economy.func.inflation import InflationForecastingConstant


def test_bounds_clip_the_forecast():
    """Regression: the upper bound was applied with np.maximum, so it raised every forecast to the cap."""
    forecaster = InflationForecastingConstant(value=0.01)
    history = np.zeros(10)

    assert forecaster.forecast_inflation(history, np.zeros(1), 0, max_inflation=0.05) == np.float64(0.01)
    assert forecaster.forecast_inflation(history, np.zeros(1), 0, max_inflation=0.005) == np.float64(0.005)
    assert forecaster.forecast_inflation(history, np.zeros(1), 0, min_inflation=0.02) == np.float64(0.02)
