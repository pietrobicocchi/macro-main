"""Bank demography and insolvency management.

This module implements strategies for managing bank demographics and
handling bank insolvency cases through:
- Solvency ratio monitoring
- Insolvency detection
- Equity injection calculation
- Bank restructuring

The strategies consider:
- Bank equity levels
- Loan portfolios
- Deposit bases
- Solvency thresholds
"""

from abc import ABC, abstractmethod
from typing import Tuple

import numpy as np


class BankDemography(ABC):
    """Abstract base class for bank demography management.

    This class defines strategies for handling bank demographics and
    insolvency through:
    - Solvency monitoring
    - Insolvency detection
    - Capital adequacy assessment
    - Restructuring decisions

    The strategies consider:
    - Equity to asset ratios
    - Minimum capital requirements
    - System-wide stability
    - Resolution mechanisms

    Attributes:
        solvency_ratio (float): Minimum required equity to assets ratio
    """

    def __init__(self, solvency_ratio: float):
        """Initialize bank demography manager.

        Args:
            solvency_ratio (float): Minimum required equity to assets ratio
        """
        self.solvency_ratio = solvency_ratio

    @abstractmethod
    def handle_bank_insolvency(
        self,
        current_bank_equity: np.ndarray,
        current_bank_loans: np.ndarray,
        current_bank_deposits: np.ndarray,
        is_insolvent: np.ndarray,
    ) -> Tuple[float, np.ndarray]:
        """Handle insolvent banks.

        Args:
            current_bank_equity (np.ndarray): Current equity by bank
            current_bank_loans (np.ndarray): Current loans by bank
            current_bank_deposits (np.ndarray): Current deposits by bank
            is_insolvent (np.ndarray): Current insolvency status by bank

        Returns:
            Tuple[float, np.ndarray]: (Total equity injection, equity of each bank after any injection)
        """
        pass


class NoBankDemography(BankDemography):
    """No-intervention bank demography strategy.

    This class implements a passive approach that:
    - Does not actively monitor solvency
    - Does not intervene in bank failures
    - Only tracks average equity levels
    - Maintains system as is
    """

    def handle_bank_insolvency(
        self,
        current_bank_equity: np.ndarray,
        current_bank_loans: np.ndarray,
        current_bank_deposits: np.ndarray,
        is_insolvent: np.ndarray,
    ) -> Tuple[float, np.ndarray]:
        """Handle insolvency with no intervention.

        Returns system average equity without any intervention.

        Args:
            [same as parent class]

        Returns:
            Tuple[float, np.ndarray]: (0.0 for no injection, unchanged equity)
        """
        return 0.0, current_bank_equity.copy()


class DefaultBankDemography(BankDemography):
    """Default bank demography strategy.

    This class implements active bank monitoring and resolution:
    - Tracks equity to asset ratios
    - Identifies insolvent banks
    - Calculates needed equity injections
    - Manages bank restructuring

    The approach:
    - Uses solvency ratio threshold
    - Marks insolvent institutions
    - Computes recapitalization needs
    - Maintains system stability
    """

    def handle_bank_insolvency(
        self,
        current_bank_equity: np.ndarray,
        current_bank_loans: np.ndarray,
        current_bank_deposits: np.ndarray,
        is_insolvent: np.ndarray,
    ) -> Tuple[float, np.ndarray]:
        """Handle insolvent banks actively.

        Identifies insolvent banks and calculates needed equity
        injections based on:
        - Current equity levels
        - Total assets (loans + deposits)
        - Solvency ratio requirement
        - System-wide average equity

        Args:
            [same as parent class]

        Returns:
            Tuple[float, np.ndarray]: (Total equity injection, equity of each bank after the injection: insolvent
                banks are topped up to the average equity of solvent banks)
        """
        insolvent_banks = (
            np.divide(
                current_bank_equity,
                current_bank_loans + current_bank_deposits,
                out=np.zeros(current_bank_equity.shape),
                where=current_bank_loans + current_bank_deposits != 0.0,
            )
            < self.solvency_ratio
        )
        is_insolvent[insolvent_banks] = True

        # Compute average equity of non-insolvent banks
        if np.sum(~insolvent_banks) > 0:
            average_equity = float(np.mean(current_bank_equity[~insolvent_banks]))
        else:
            average_equity = float(np.mean(current_bank_equity))
        target_equity = current_bank_equity.copy()
        target_equity[insolvent_banks] = np.maximum(current_bank_equity[insolvent_banks], average_equity)
        return float((target_equity - current_bank_equity).sum()), target_equity


class MinimumCapitalBankDemography(DefaultBankDemography):
    """Recapitalise failing banks to the minimum capital ratio.

    A bank is insolvent when equity / (customer deposits + equity) falls below the solvency ratio (as in
    DefaultBankDemography). The government then injects exactly the equity that restores that ratio. Unlike topping
    up to the average of the healthy banks, this also works when there is a single bank.
    """

    def handle_bank_insolvency(
        self,
        current_bank_equity: np.ndarray,
        current_bank_loans: np.ndarray,
        current_bank_deposits: np.ndarray,
        is_insolvent: np.ndarray,
    ) -> Tuple[float, np.ndarray]:
        """Find insolvent banks and the injection that restores the solvency ratio.

        Args:
            current_bank_equity (np.ndarray): Current equity by bank
            current_bank_loans (np.ndarray): Current loans by bank
            current_bank_deposits (np.ndarray): Current reserve position by bank (deposits + equity - loans)
            is_insolvent (np.ndarray): Insolvency status by bank, updated in place

        Returns:
            Tuple[float, np.ndarray]: (Total equity injection, equity of each bank after the injection)
        """
        funding = current_bank_loans + current_bank_deposits  # customer deposits + equity
        insolvent_banks = (
            np.divide(current_bank_equity, funding, out=np.zeros(current_bank_equity.shape), where=funding != 0.0)
            < self.solvency_ratio
        )
        is_insolvent[insolvent_banks] = True

        # Equity E* with E* / (D + E*) = solvency ratio, where D are customer deposits
        customer_deposits = funding - current_bank_equity
        required_equity = self.solvency_ratio * customer_deposits / (1.0 - self.solvency_ratio)
        target_equity = current_bank_equity.copy()
        target_equity[insolvent_banks] = np.maximum(current_bank_equity, required_equity)[insolvent_banks]
        return float((target_equity - current_bank_equity).sum()), target_equity
