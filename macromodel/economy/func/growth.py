"""Economic growth forecasting module.

This module provides various approaches for forecasting economic growth rates
using different statistical and econometric methods. It implements several
forecasting strategies:

1. Constant Growth:
   - Fixed growth rate predictions
   - Useful for steady-state analysis

2. OLS-based Growth:
   - Linear regression approach
   - Captures basic growth dynamics

3. Autoregressive Growth:
   - Both implemented and manual AR models
   - Accounts for growth persistence
   - Supports different lag structures

4. Exogenous Growth:
   - Externally provided growth paths
   - Useful for scenario analysis

Each forecasting method can incorporate noise and supports different
forecast horizons for flexible economic modeling.
"""

from abc import ABC

import numpy as np

from macromodel.forecaster.forecaster import (
    ConstantForecaster,
    ImplementedAutoregForecaster,
    ManualAutoregForecaster,
    OLSForecaster,
)


class GrowthForecasting(ABC):
    """Abstract base class for economic growth forecasting.

    Provides a common interface for different growth forecasting approaches.
    Supports various forecast horizons and noise control in predictions.

    Attributes:
        forecaster: Underlying forecasting model implementation
    """

    def __init__(self, *args, **kwargs):
        """Initialize forecasting instance.

        Args:
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments
        """
        self.forecaster = None

    def forecast_growth(
        self,
        historic_growth: np.ndarray,
        exogenous_growth: np.ndarray,
        current_time: int,
        t: int = 1,
        assume_zero_noise: bool = False,
        **kwargs,
    ) -> float:
        """Generate growth forecasts based on historical data.

        Args:
            historic_growth (np.ndarray): Past growth rates: the data window, then the simulated quarters
            exogenous_growth (np.ndarray): External growth projections
            current_time (int): Current time period
            t (int, optional): Forecast horizon. Defaults to 1.
            assume_zero_noise (bool, optional): Suppress random variation. Defaults to False.
            **kwargs: Extra information some rules use (`data_growth`, `unemployment_rate`,
                `initial_unemployment_rate`)

        Returns:
            float: Forecasted growth rate
        """
        return self.forecaster.forecast(historic_growth, t, assume_zero_noise=assume_zero_noise)


class GrowthForecastingConstant(GrowthForecasting):
    """Constant growth forecasting implementation.

    Predicts a fixed growth rate regardless of history.
    Useful for steady-state and baseline analysis.

    Attributes:
        forecaster (ConstantForecaster): Fixed-value forecasting model
    """

    def __init__(self, value: float, *args, **kwargs):
        """Initialize constant forecaster.

        Args:
            value (float): Fixed growth rate to predict
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments
        """
        super().__init__()
        self.forecaster = ConstantForecaster(value=value)


class GrowthForecastingOLS(GrowthForecasting):
    """OLS-based growth forecasting implementation.

    Uses linear regression to predict growth rates.
    Captures basic linear relationships in growth dynamics.

    Attributes:
        forecaster (OLSForecaster): Linear regression forecasting model
    """

    def __init__(self):
        """Initialize OLS forecaster."""
        super().__init__()
        self.forecaster = OLSForecaster()


class GrowthImplementedForecastingAutoReg(GrowthForecasting):
    """Implemented autoregressive growth forecasting.

    Uses a pre-implemented AR model for growth prediction.
    Accounts for growth persistence through lag structure.

    Attributes:
        forecaster (ImplementedAutoregForecaster): AR model implementation
    """

    def __init__(self, lags: int, *args, **kwargs):
        """Initialize implemented AR forecaster.

        Args:
            lags (int): Number of autoregressive lags
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments
        """
        super().__init__()
        self.forecaster = ImplementedAutoregForecaster(lags)


class GrowthManualForecastingAutoReg(GrowthForecasting):
    """Manual autoregressive growth forecasting.

    Uses a manually implemented AR(1) model for growth prediction.
    Provides direct control over the autoregressive process.

    Attributes:
        forecaster (ManualAutoregForecaster): Manual AR model implementation
    """

    def __init__(self, lags: int, *args, **kwargs):
        """Initialize manual AR forecaster.

        Args:
            lags (int): Must be 1 (AR(1) only)
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments

        Raises:
            AssertionError: If lags != 1
        """
        assert lags == 1
        super().__init__()
        self.forecaster = ManualAutoregForecaster()


class DataOnlyGrowthForecastingAutoReg(GrowthManualForecastingAutoReg):
    """AR(1) growth forecast from the pre-simulation data only (G16).

    Firms' expected growth is the AR(1) forecast made at the start, h quarters ahead in quarter h: it uses only data
    available at the forecast origin and does not feed on the growth the simulation produces.
    """

    def forecast_growth(
        self,
        historic_growth: np.ndarray,
        exogenous_growth: np.ndarray,
        current_time: int,
        t: int = 1,
        assume_zero_noise: bool = False,
        data_growth: np.ndarray = None,
        **kwargs,
    ) -> np.ndarray:
        horizon = len(historic_growth) - len(data_growth) + 1
        return self.forecaster.forecast(data_growth, horizon, assume_zero_noise=assume_zero_noise)[-1:]


class SlackAwareGrowthForecastingAutoReg(GrowthManualForecastingAutoReg):
    """AR(1) growth forecast, lowered when unemployment is below its initial level (G16).

    Expected growth = AR(1) forecast - slack_sensitivity * (initial unemployment rate - current unemployment rate).
    By Okun's law output is about twice as far above potential as unemployment is below its normal rate; firms that
    expect a fraction of that gap to close each quarter expect slower growth when the labour market is tight, and
    faster growth when it is slack.
    """

    def __init__(self, lags: int, slack_sensitivity: float = 0.2, *args, **kwargs):
        """Initialize the slack-aware AR(1) forecaster.

        Args:
            lags (int): Must be 1 (AR(1) only)
            slack_sensitivity (float): Fall in expected quarterly growth per unit of unemployment below its initial
                level
        """
        super().__init__(lags)
        self.slack_sensitivity = slack_sensitivity

    def forecast_growth(
        self,
        historic_growth: np.ndarray,
        exogenous_growth: np.ndarray,
        current_time: int,
        t: int = 1,
        assume_zero_noise: bool = False,
        unemployment_rate: float = None,
        initial_unemployment_rate: float = None,
        **kwargs,
    ) -> np.ndarray:
        forecast = self.forecaster.forecast(historic_growth, t, assume_zero_noise=assume_zero_noise)
        return forecast - self.slack_sensitivity * (initial_unemployment_rate - unemployment_rate)


class ExogenousGrowthForecasting(GrowthForecasting):
    """Exogenous growth forecasting implementation.

    Uses externally provided growth paths for predictions.
    Useful for scenario analysis and policy simulations.

    Note:
        Currently requires transformation of exogenous growth values.
        TODO: Remove the outer exp(x) - 1 transform when using this class.
    """

    def __init__(self, lags: int):
        """Initialize exogenous growth forecaster.

        Args:
            lags (int): Number of lags (currently unused)
        """
        super().__init__()
        self.forecaster = None

    def forecast_growth(
        self,
        historic_growth: np.ndarray,
        exogenous_growth: np.ndarray,
        current_time: int,
        t: int = 1,
        assume_zero_noise: bool = False,
        **kwargs,
    ) -> float | np.ndarray:
        """Generate growth forecasts from exogenous data.

        Args:
            historic_growth (np.ndarray): Past growth rates (unused)
            exogenous_growth (np.ndarray): External growth projections
            current_time (int): Current time period
            t (int, optional): Forecast horizon. Defaults to 1.
            assume_zero_noise (bool, optional): Suppress random variation. Defaults to False.

        Returns:
            float | np.ndarray: Forecasted growth rate(s)

        Raises:
            AssertionError: Always raises error due to pending transformation fix
        """
        assert 0  # TODO: remove the outer exp(x) - 1 transform when using this
        return np.array([exogenous_growth[current_time]])
