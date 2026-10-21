"""Household insolvency management implementation.

This module implements household insolvency handling through:
- Default detection and processing
- Debt restructuring mechanisms
- Asset liquidation procedures
- Bank interaction management

The implementation handles:
- Insolvency identification
- Credit market impacts
- Non-performing loan tracking
- Default rate calculations
"""

from abc import ABC, abstractmethod
from typing import Tuple

import numpy as np

from macromodel.agents.banks.banks import Banks
from macromodel.agents.households.households import Households
from macromodel.markets.credit_market.credit_market import CreditMarket


class HouseholdInsolvencyHandler(ABC):
    """Abstract base class for household insolvency management.

    Defines interface for handling household defaults through:
    - Insolvency detection
    - Default processing
    - Credit market updates
    - Bank interactions
    """

    @abstractmethod
    def handle_insolvency(
        self,
        households: Households,
        banks: Banks,
        credit_market: CreditMarket,
    ) -> Tuple[float, float, float]:
        """Process household insolvency cases.

        Args:
            households (Households): Household sector agent
            banks (Banks): Banking sector agent
            credit_market (CreditMarket): Credit market interface

        Returns:
            Tuple[float, float, float]: Default rate, NPL ratios for consumption
                loans and mortgages
        """
        pass


class DefaultHouseholdInsolvencyHandler(HouseholdInsolvencyHandler):
    """Default implementation of household insolvency management.

    Implements insolvency handling through:
    - Net wealth and deposit checks
    - Loan removal processing
    - NPL ratio calculations
    """

    def find_insolvent(self, households: Households) -> np.ndarray:
        """Households in negative net wealth with any overdraft."""
        return np.where(
            np.logical_and(
                households.ts.current("net_wealth") < 0,
                households.ts.current("wealth_deposits") < 0,
            )
        )[0]

    def handle_insolvency(
        self,
        households: Households,
        banks: Banks,
        credit_market: CreditMarket,
    ) -> Tuple[float, float, float]:
        """Process household defaults using default behavior.

        Handles insolvency through:
        - Identifying insolvent households
        - Processing loan removals
        - Calculating default metrics

        Args:
            households (Households): Household sector agent
            banks (Banks): Banking sector agent
            credit_market (CreditMarket): Credit market interface

        Returns:
            Tuple[float, float, float]: Default rate, NPL ratios for consumption
                loans and mortgages
        """
        insolvent_households = self.find_insolvent(households)
        bad_hh_cons_loans, bad_mortgages = credit_market.remove_loans_to_households(insolvent_households)

        # The written-off loans are gone from the households' own books too
        for key in ["consumption_loan_debt", "mortgage_debt", "debt"]:
            cleared = households.ts.current(key).copy()
            cleared[insolvent_households] = 0.0
            households.ts.override_current(key, cleared)

        # Calculate NPL ratios
        total_cons_loans = credit_market.ts.current("total_outstanding_loans_granted_households_consumption")[0]
        if total_cons_loans == 0.0:
            npl_hh_cons_loans = 0.0
        else:
            npl_hh_cons_loans = bad_hh_cons_loans / total_cons_loans
        if credit_market.ts.current("total_outstanding_loans_granted_mortgages")[0] == 0.0:
            npl_mortgages = 0.0
        else:
            npl_mortgages = bad_mortgages / credit_market.ts.current("total_outstanding_loans_granted_mortgages")[0]

        return (
            len(insolvent_households) / households.ts.current("n_households"),
            npl_hh_cons_loans,
            npl_mortgages,
        )


class UnableToPayHouseholdInsolvencyHandler(DefaultHouseholdInsolvencyHandler):
    """Households default when they cannot pay, not at the first overdraft.

    A household defaults when it is underwater (negative net wealth) and its overdraft exceeds
    `overdraft_limit_in_quarters_of_income` quarters of its income, i.e. it has run out of room to keep paying.
    Underwater households that still meet their payments keep their loans, as with negative equity in practice.
    """

    def __init__(self, overdraft_limit_in_quarters_of_income: float = 1.0):
        self.overdraft_limit_in_quarters_of_income = overdraft_limit_in_quarters_of_income

    def find_insolvent(self, households: Households) -> np.ndarray:
        """Underwater households whose overdraft exceeds the limit relative to income."""
        income = np.maximum(households.ts.current("income"), 0.0)
        overdraft = -np.minimum(households.ts.current("wealth_deposits"), 0.0)
        return np.where(
            np.logical_and(
                households.ts.current("net_wealth") < 0,
                overdraft > self.overdraft_limit_in_quarters_of_income * income,
            )
        )[0]
