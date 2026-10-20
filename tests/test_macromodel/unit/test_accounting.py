import numpy as np
import pytest

from macromodel.accounting import AccountingMonitor
from macromodel.agents.households.func.wealth import DefaultWealthSetter
from macromodel.configurations import CountryConfiguration, SimulationConfiguration
from macromodel.simulation import Simulation

LEDGER_CHECKS = [
    "loans.firms.borrowers",
    "loans.firms.banks",
    "loans.consumption.borrowers",
    "loans.consumption.banks",
    "loans.mortgages.borrowers",
    "loans.total.banks",
    "deposits.firms",
    "deposits.households",
    "bank_equity",
    "government_debt",
]
# Money is not yet exactly conserved: financial-asset income and purchases have no counterpart, and goods-market
# and wage payments still differ by a few percent of GDP (issues S9-S12 in PROJECT.md). Tighten as they are fixed.
MONEY_TOLERANCE = 0.05


@pytest.fixture(scope="module", name="audited_run")
def audited_run(datawrapper):
    configuration = SimulationConfiguration(country_configurations={"FRA": CountryConfiguration()}, t_max=4, seed=0)
    simulation = Simulation.from_datawrapper(datawrapper=datawrapper, simulation_configuration=configuration)
    monitor = AccountingMonitor()
    monitor.record(simulation, t=-1)
    simulation.posthooks.append(monitor)
    simulation.run()
    return simulation, monitor.report()


def test_ledgers_agree_every_quarter(audited_run):
    """Regression: loans and deposits recorded by borrowers, banks and the credit market agree, from t=0 on."""
    _, report = audited_run
    ledgers = report[report["check"].isin(LEDGER_CHECKS)]
    worst = ledgers.loc[ledgers["share_of_gdp"].abs().idxmax()]
    assert abs(worst["share_of_gdp"]) < 1e-9, (
        f"{worst['check']} off by {worst['share_of_gdp']:.2%} of GDP at t={worst['t']}"
    )


def test_money_is_roughly_conserved(audited_run):
    """Regression: wiped overdrafts, unpaid house sellers and free write-offs created or destroyed up to 160% of GDP."""
    _, report = audited_run
    money = report[report["check"] == "money"]
    assert money["share_of_gdp"].abs().max() < MONEY_TOLERANCE


def test_dissaving_does_not_wipe_overdrafts():
    """Regression: dissaving from an overdrawn account subtracted the (negative) balance, wiping the overdraft."""
    setter = DefaultWealthSetter(other_real_assets_depreciation_rate=0.0)
    used_deposits, used_other = setter.use_up_wealth(
        used_up_wealth=np.array([10.0, 10.0]),
        current_wealth_in_deposits=np.array([-50.0, 4.0]),
        current_wealth_in_other_financial_assets=np.array([0.0, 3.0]),
    )
    np.testing.assert_allclose(used_other, [0.0, 3.0])
    np.testing.assert_allclose(used_deposits, [10.0, 7.0])  # the rest is paid from deposits, even into overdraft


def test_written_off_loans_are_bank_losses(audited_run):
    """Regression: writing off a borrower's loans must be recorded as a loss of the lending bank."""
    simulation, _ = audited_run
    credit_market = simulation.countries["FRA"].credit_market
    credit_market.take_loan_losses()
    borrowers = np.arange(5)
    expected = (
        credit_market.states["cons_loans"][0][:, borrowers] + credit_market.states["mort_loans"][0][:, borrowers]
    ).sum(axis=1)
    credit_market.remove_loans_to_households(borrowers)
    np.testing.assert_allclose(credit_market.take_loan_losses(), expected)
    np.testing.assert_allclose(credit_market.take_loan_losses(), 0.0)
