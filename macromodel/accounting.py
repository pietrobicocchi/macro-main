"""Accounting checks: does every debt have a creditor, and does money move only through recorded channels?

Loans are recorded in three ledgers (borrowers, banks, the credit market) and deposits in two (owners, banks);
the ledgers must agree. Banks' reserve position is the residual of their balance sheet,

    reserves = deposits from firms and households + equity - outstanding loans,

so the banking system's own books balance by construction. Money is conserved only if reserves change by what
enters or leaves the banking system: the government deficit (paid out as benefits and purchases, taken in as
taxes) plus net exports. Any other change in reserves is money created or destroyed without a counterpart.

Use as a post-step hook::

    monitor = AccountingMonitor()
    monitor.record(simulation, t=-1)  # the initial state
    simulation.posthooks.append(monitor)
    simulation.run()
    monitor.report()  # one row per check and period, residuals in LCU and as a share of quarterly GDP
"""

from typing import Any

import numpy as np
import pandas as pd

# check -> what it means when the residual is not zero
CHECKS = {
    "loans.firms.borrowers": "firms' recorded debt differs from the credit market's firm loans",
    "loans.firms.banks": "banks' recorded firm loans differ from the credit market's",
    "loans.consumption.borrowers": "households' consumption-loan debt differs from the credit market's",
    "loans.consumption.banks": "banks' recorded consumption loans differ from the credit market's",
    "loans.mortgages.borrowers": "households' mortgage debt differs from the credit market's",
    "loans.total.banks": "banks' total outstanding loans differ from the credit market's",
    "deposits.firms": "firms' deposits differ from banks' deposits from firms",
    "deposits.households": "households' deposits differ from banks' deposits from households",
    "money": "reserves changed by more or less than the government deficit plus net exports",
    "bank_equity": "bank equity changed by more or less than after-tax profits plus government injections",
    "government_debt": "government debt changed by more or less than the deficit",
    "gdp.trade_adjustment": "output GDP minus expenditure GDP before imports/exports are adjusted to close it",
}


def _total(ts: Any, key: str) -> float:
    return float(np.sum(ts.current(key)))


def snapshot(country: Any) -> dict[str, float]:
    """End-of-period stocks and flows of one country, in LCU."""
    firms, households, banks = country.firms.ts, country.households.ts, country.banks.ts
    government, economy = country.central_government.ts, country.economy.ts
    loans = {
        kind: float(country.credit_market.states[kind][0].sum())
        for kind in ["st_loans", "lt_loans", "cons_loans", "mort_loans"]
    }
    bank_profits = np.asarray(banks.current("profits"), dtype=float)
    return {
        "firm_debt": _total(firms, "debt"),
        "household_consumption_debt": _total(households, "consumption_loan_debt"),
        "household_mortgage_debt": _total(households, "mortgage_debt"),
        "bank_firm_loans": _total(banks, "total_short_term_loans_to_firms")
        + _total(banks, "total_long_term_loans_to_firms"),
        "bank_consumption_loans": _total(banks, "total_consumption_loans_to_households"),
        "bank_total_loans": _total(banks, "total_outstanding_loans"),
        "market_firm_loans": loans["st_loans"] + loans["lt_loans"],
        "market_consumption_loans": loans["cons_loans"],
        "market_mortgages": loans["mort_loans"],
        "firm_deposits": _total(firms, "deposits"),
        "household_deposits": _total(households, "wealth_deposits"),
        "bank_deposits_from_firms": _total(banks, "deposits_from_firms"),
        "bank_deposits_from_households": _total(banks, "deposits_from_households"),
        "bank_reserves": _total(banks, "deposits"),
        "bank_equity": _total(banks, "equity"),
        "bank_after_tax_profits": float(
            np.sum(bank_profits - country.central_government.states["Profit Tax"] * np.maximum(bank_profits, 0.0))
        ),
        "government_debt": _total(government, "debt"),
        "government_deficit": _total(government, "deficit"),
        "bank_equity_injection": _total(government, "bank_equity_injection"),
        "exports": _total(economy, "exports"),
        "imports": _total(economy, "imports"),
        "exports_adjusted": _total(economy, "total_exports"),
        "imports_adjusted": _total(economy, "total_imports"),
        "gdp": _total(economy, "gdp_output"),
    }


def residuals(current: dict[str, float], previous: dict[str, float] | None) -> dict[str, float]:
    """Residual of every check; zero means the books agree. Flow checks need the previous period."""
    c = current
    out = {
        "loans.firms.borrowers": c["firm_debt"] - c["market_firm_loans"],
        "loans.firms.banks": c["bank_firm_loans"] - c["market_firm_loans"],
        "loans.consumption.borrowers": c["household_consumption_debt"] - c["market_consumption_loans"],
        "loans.consumption.banks": c["bank_consumption_loans"] - c["market_consumption_loans"],
        "loans.mortgages.borrowers": c["household_mortgage_debt"] - c["market_mortgages"],
        "loans.total.banks": c["bank_total_loans"]
        - (c["market_firm_loans"] + c["market_consumption_loans"] + c["market_mortgages"]),
        "deposits.firms": c["firm_deposits"] - c["bank_deposits_from_firms"],
        "deposits.households": c["household_deposits"] - c["bank_deposits_from_households"],
        "gdp.trade_adjustment": (c["exports_adjusted"] - c["exports"]) - (c["imports_adjusted"] - c["imports"]),
    }
    if previous is not None:
        p = previous
        out["money"] = (c["bank_reserves"] - p["bank_reserves"]) - (
            c["government_deficit"] + c["exports"] - c["imports"]
        )
        out["bank_equity"] = (c["bank_equity"] - p["bank_equity"]) - (
            c["bank_after_tax_profits"] + c["bank_equity_injection"]
        )
        out["government_debt"] = (c["government_debt"] - p["government_debt"]) - c["government_deficit"]
    return out


class AccountingMonitor:
    """Records accounting residuals for every country after each period (a Simulation post-hook)."""

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []
        self._previous: dict[str, dict[str, float]] = {}

    def record(self, simulation: Any, t: int) -> None:
        for name, country in simulation.countries.items():
            current = snapshot(country)
            for check, value in residuals(current, self._previous.get(name)).items():
                self.rows.append(
                    {"country": name, "t": t + 1, "check": check, "residual": value, "gdp": current["gdp"]}
                )
            self._previous[name] = current

    def __call__(self, simulation: Any, t: int, year: int, month: int) -> None:
        self.record(simulation, t)

    def report(self) -> pd.DataFrame:
        """Residuals by check and period; `share_of_gdp` is the residual over that period's quarterly GDP."""
        df = pd.DataFrame(self.rows)
        df["share_of_gdp"] = df["residual"] / df["gdp"]
        return df.drop(columns="gdp")

    def failures(self, tolerance: float = 1e-6) -> pd.DataFrame:
        """Checks whose residual exceeds `tolerance` as a share of GDP, with the first period it happened."""
        df = self.report()
        bad = df[df["share_of_gdp"].abs() > tolerance]
        if bad.empty:
            return bad
        summary = bad.groupby(["country", "check"]).agg(
            first_t=("t", "min"),
            periods=("t", "size"),
            worst_share_of_gdp=("share_of_gdp", lambda s: s.loc[s.abs().idxmax()]),
        )
        summary["meaning"] = [CHECKS[check] for _, check in summary.index]
        return summary.reset_index()
