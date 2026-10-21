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
# Money not accounted for by the flows that have no counterpart by design (S9, S10, S13 in PROJECT.md).
# A small transient remains in the first quarters (S23); tighten as it is fixed.
UNEXPLAINED_MONEY_TOLERANCE = 0.04


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


def test_money_is_conserved_apart_from_unbacked_flows(audited_run):
    """Regression: wiped overdrafts, unpaid house sellers, free write-offs, unpaid VAT, untaxed gross wages,
    double-inflated wage bills and unpaid unemployment benefits created or destroyed up to 160% of GDP."""
    _, report = audited_run
    unexplained = report[report["check"] == "money.unexplained"]
    assert unexplained["share_of_gdp"].abs().max() < UNEXPLAINED_MONEY_TOLERANCE


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


def test_insolvent_firms_debt_records_match_the_credit_market(datawrapper):
    """Regression (S28): a firm's written-off loans stayed in its own debt records until the next quarter."""
    from macromodel.accounting import residuals, snapshot

    configuration = SimulationConfiguration(country_configurations={"FRA": CountryConfiguration()}, t_max=1, seed=0)
    simulation = Simulation.from_datawrapper(datawrapper=datawrapper, simulation_configuration=configuration)
    simulation.run()
    country = simulation.countries["FRA"]
    firms = country.firms
    borrower = int(np.argmax(firms.ts.current("debt")))
    assert firms.ts.current("debt")[borrower] > 0.0

    insolvent = np.zeros_like(firms.states["is_insolvent"])
    insolvent[borrower] = True
    firms.functions["demography"].handle_firm_insolvency = lambda **_: insolvent
    firms.handle_insolvency(credit_market=country.credit_market)

    assert firms.ts.current("debt")[borrower] == 0.0
    assert abs(residuals(snapshot(country), None)["loans.firms.borrowers"]) < 1e-6


def test_firm_shares_mode_conserves_money(datawrapper):
    """With other financial assets as shares in firms, dividends and share purchases have counterparts: the only
    flow left without one is interest on government debt, and nothing else is unexplained."""
    country_configuration = CountryConfiguration()
    country_configuration.households.functions.financial_assets.name = "FirmSharesFinancialAssets"
    configuration = SimulationConfiguration(country_configurations={"FRA": country_configuration}, t_max=3, seed=0)
    simulation = Simulation.from_datawrapper(datawrapper=datawrapper, simulation_configuration=configuration)
    monitor = AccountingMonitor()
    monitor.record(simulation, t=-1)
    simulation.posthooks.append(monitor)
    simulation.run()
    report = monitor.report()

    ledgers = report[report["check"].isin(LEDGER_CHECKS)]
    assert ledgers["share_of_gdp"].abs().max() < 1e-9
    unexplained = report[report["check"] == "money.unexplained"]
    assert unexplained["share_of_gdp"].abs().max() < UNEXPLAINED_MONEY_TOLERANCE


def test_households_default_only_when_unable_to_pay():
    """Regression: any overdraft plus negative net wealth used to write off a household's whole debt."""
    from types import SimpleNamespace

    from macromodel.agents.households.func.insolvency import UnableToPayHouseholdInsolvencyHandler

    current = {
        "net_wealth": np.array([-10.0, -10.0, 5.0, -10.0]),
        "wealth_deposits": np.array([-1.0, -50.0, -50.0, 3.0]),
        "income": np.array([20.0, 20.0, 20.0, 20.0]),
    }
    households = SimpleNamespace(ts=SimpleNamespace(current=lambda key: current[key]))
    handler = UnableToPayHouseholdInsolvencyHandler(overdraft_limit_in_quarters_of_income=1.0)
    # only the underwater household whose overdraft exceeds a quarter's income defaults
    np.testing.assert_array_equal(handler.find_insolvent(households), [1])


def test_money_identity_counts_central_bank_interest_on_reserves():
    """Regression (S29): the interest the central bank pays on positive reserves is money it creates, not a leak."""
    from collections import defaultdict

    from macromodel.accounting import residuals

    def books(reserves: float, rate: float) -> dict[str, float]:
        # every other stock and flow is zero
        return defaultdict(
            float, {"bank_reserves": reserves, "bank_positive_reserves": max(reserves, 0.0), "policy_rate": rate}
        )

    previous, current = books(100.0, 0.02), books(102.0, 0.02)
    out = {k: v for k, v in residuals(current, previous).items() if k.startswith("money")}
    assert np.isclose(out["money"], 0.0) and np.isclose(out["money.unexplained"], 0.0)
