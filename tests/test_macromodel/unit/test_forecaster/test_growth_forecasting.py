import numpy as np

from macromodel.economy.func.growth import (
    DataOnlyGrowthForecastingAutoReg,
    GrowthManualForecastingAutoReg,
    SlackAwareGrowthForecastingAutoReg,
)

DATA = 0.005 + 0.002 * np.sin(np.arange(40))


def _forecast(rule, historic_growth, **kwargs) -> float:
    return rule.forecast_growth(
        historic_growth=historic_growth,
        exogenous_growth=np.zeros(1),
        current_time=0,
        assume_zero_noise=True,
        data_growth=DATA,
        **kwargs,
    )[0]


class TestDataOnlyGrowthForecasting:
    def test_ignores_simulated_growth(self):
        """A simulated boom must not move the forecast: it depends only on the data and the horizon."""
        rule = DataOnlyGrowthForecastingAutoReg(lags=1)
        boom = _forecast(rule, np.concatenate([DATA, [0.03, 0.03, 0.03]]))
        bust = _forecast(rule, np.concatenate([DATA, [-0.03, -0.03, -0.03]]))
        assert boom == bust

    def test_first_quarter_matches_the_default_forecast(self):
        default = GrowthManualForecastingAutoReg(lags=1)
        expected = default.forecast_growth(DATA, np.zeros(1), 0, assume_zero_noise=True)[0]
        assert np.isclose(_forecast(DataOnlyGrowthForecastingAutoReg(lags=1), DATA), expected)

    def test_horizon_grows_with_simulated_quarters(self):
        rule = DataOnlyGrowthForecastingAutoReg(lags=1)
        expected = rule.forecaster.forecast(DATA, 4, assume_zero_noise=True)[-1]
        assert np.isclose(_forecast(rule, np.concatenate([DATA, np.zeros(3)])), expected)


class TestSlackAwareGrowthForecasting:
    def test_tight_labour_market_lowers_expected_growth(self):
        default = GrowthManualForecastingAutoReg(lags=1).forecast_growth(DATA, np.zeros(1), 0, assume_zero_noise=True)
        rule = SlackAwareGrowthForecastingAutoReg(lags=1, slack_sensitivity=0.2)
        tight = _forecast(rule, DATA, unemployment_rate=0.05, initial_unemployment_rate=0.10)
        normal = _forecast(rule, DATA, unemployment_rate=0.10, initial_unemployment_rate=0.10)
        assert np.isclose(normal, default[0])
        assert np.isclose(tight, default[0] - 0.2 * 0.05)
