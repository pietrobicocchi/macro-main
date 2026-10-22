import numpy as np

from macromodel.economy.func.house_price_index import HPIForecastingConstant
from macromodel.economy.func.inflation import InflationForecastingConstant


def test_bounds_clip_the_forecast():
    """Regression: the upper bound was applied with np.maximum, so it raised every forecast to the cap."""
    forecaster = InflationForecastingConstant(value=0.01)
    history = np.zeros(10)

    assert forecaster.forecast_inflation(history, np.zeros(1), 0, max_inflation=0.05) == np.float64(0.01)
    assert forecaster.forecast_inflation(history, np.zeros(1), 0, max_inflation=0.005) == np.float64(0.005)
    assert forecaster.forecast_inflation(history, np.zeros(1), 0, min_inflation=0.02) == np.float64(0.02)


def test_hpi_bounds_clip_the_forecast():
    """Regression (P8): the upper bound was applied with np.maximum. The economy passes max_hpi_growth=0.2, so every
    house price forecast was log growth 0.2 (22% a quarter) and every household chose to buy."""
    forecaster = HPIForecastingConstant(value=0.01)
    history = np.zeros(10)

    assert forecaster.forecast_hpi_growth(history, min_hpi_growth=-0.2, max_hpi_growth=0.2) == np.float64(0.01)
    assert forecaster.forecast_hpi_growth(history, max_hpi_growth=0.005) == np.float64(0.005)
