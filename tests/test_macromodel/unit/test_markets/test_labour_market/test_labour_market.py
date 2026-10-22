from types import SimpleNamespace

import numpy as np

from macromodel.agents.individuals.individual_properties import ActivityStatus
from macromodel.markets.labour_market.func.clearing import (
    PolednaLabourMarketClearer,
    SearchFrictionsLabourMarketClearer,
    firing,
)


class _DummyTS:
    def __init__(self, values):
        self._values = values

    def current(self, name):
        return self._values[name]


CLEARER_PARAMETERS = dict(
    hiring_speed=1.0,
    firing_speed=1.0,
    random_firing_probability=0.0,
    sorted_firing=False,
    optimised_hiring=True,
    allow_switching_industries=True,
    consider_reservation_wages=False,
    firing_cost_fraction=0.0,
    hiring_cost_fraction=0.0,
    individuals_quitting=False,
    individuals_quitting_temperature=0.0,
    compare_with_normalised_inputs=False,
    round_target_employment=False,
)


def _one_firm_market(n_employed: int, n_unemployed: int, desired_labour: float):
    """One firm with unit productivity, n_employed workers and n_unemployed job seekers."""
    n = n_employed + n_unemployed
    firms = SimpleNamespace(
        ts=_DummyTS(
            {
                "labour_inputs": np.array([float(n_employed)]),
                "desired_labour_inputs": np.array([desired_labour]),
                "n_firms": 1,
            }
        ),
        states={
            "Employments": [list(range(n_employed))],
            "Industry": np.array([0]),
            "Labour Productivity by Industry": np.array([1.0]),
        },
    )
    households = SimpleNamespace(ts=_DummyTS({"wealth": np.ones(n)}))
    individuals = SimpleNamespace(
        ts=_DummyTS(
            {
                "labour_inputs": np.ones(n),
                "employee_income": np.ones(n),
                "reservation_wages": np.zeros(n),
            }
        ),
        states={
            "Activity Status": np.array(
                [ActivityStatus.EMPLOYED] * n_employed + [ActivityStatus.UNEMPLOYED] * n_unemployed, dtype=object
            ),
            "Employment Industry": np.zeros(n, dtype=int),
            "Corresponding Firm ID": np.array([0] * n_employed + [-1] * n_unemployed),
            "Corresponding Household ID": np.arange(n),
            "Offered Wage of Accepted Job": np.zeros(n),
        },
    )
    return firms, households, individuals


class TestLabourMarket:
    def test_firing_counts_only_workers_fired(self):
        # Firm 0 wants two more workers, firm 1 one fewer: one layoff, not 1 - 2 = -1
        _, num_fired = firing(
            individuals_corresponding_firm=np.array([0, 1, 1, -1]),
            prev_individuals_productivity=np.ones(4),
            desired_labour_inputs=np.array([3.0, 1.0]),
            prev_labour_inputs=np.array([1.0, 2.0]),
            current_individual_wages=np.ones(4),
            firm_industries=np.array([0, 0]),
            average_industry_productivity=np.array([1.0]),
            firing_speed=1.0,
            firing_cost_fraction=0.0,
        )
        assert num_fired == 1

    def test_matching_function_is_capped_by_unemployed_and_vacancies(self):
        clearer = SearchFrictionsLabourMarketClearer(
            matching_efficiency=0.5, matching_elasticity=0.5, **CLEARER_PARAMETERS
        )
        assert clearer.matches(16.0, 4.0) == 0.5 * np.sqrt(16.0 * 4.0)
        assert clearer.matches(0.0, 4.0) == 0.0
        assert clearer.matches(4.0, 0.0) == 0.0
        clearer.matching_efficiency = 100.0
        assert clearer.matches(16.0, 4.0) == 4.0
        assert clearer.matches(3.0, 4.0) == 3.0

    def test_search_frictions_hires_no_more_than_matches(self):
        for efficiency, expected_hires in [(0.0, 0), (100.0, 8)]:
            clearer = SearchFrictionsLabourMarketClearer(
                matching_efficiency=efficiency, matching_elasticity=0.5, **CLEARER_PARAMETERS
            )
            firms, households, individuals = _one_firm_market(n_employed=2, n_unemployed=20, desired_labour=10.0)

            _, num_hired, *_ = clearer.clear(firms=firms, households=households, individuals=individuals)

            assert num_hired == expected_hires
            assert len(firms.states["Employments"][0]) == 2 + expected_hires
            assert np.sum(individuals.states["Activity Status"] == ActivityStatus.EMPLOYED) == 2 + expected_hires

    def test_search_frictions_replace_separated_workers_within_the_quarter(self):
        np.random.seed(0)
        clearer = SearchFrictionsLabourMarketClearer(
            matching_efficiency=100.0,
            matching_elasticity=0.5,
            **{**CLEARER_PARAMETERS, "random_firing_probability": 0.5},
        )
        firms, households, individuals = _one_firm_market(n_employed=40, n_unemployed=10, desired_labour=40.0)

        _, num_hired, num_separated, *_ = clearer.clear(firms=firms, households=households, individuals=individuals)

        assert num_separated > 0
        assert num_hired == num_separated
        assert len(firms.states["Employments"][0]) == 40

    def test_uncalibrated_matching_makes_initial_unemployment_a_steady_state(self):
        """With matching_efficiency=None the first clearing calibrates it so that, in expectation, hires replace
        separations at the initial unemployment rate."""
        clearer = SearchFrictionsLabourMarketClearer(
            matching_efficiency=None,
            matching_elasticity=0.5,
            **{**CLEARER_PARAMETERS, "random_firing_probability": 0.05},
        )
        firms, households, individuals = _one_firm_market(n_employed=90, n_unemployed=10, desired_labour=90.0)

        clearer.clear(firms=firms, households=households, individuals=individuals)

        u, s = 0.1, 0.05
        assert np.isclose(clearer.matching_efficiency, (s * (1 - u) / (u + s * (1 - u))) ** 0.5)
        # In the steady state the market fills every vacancy: M(U + sE, sE) = sE
        seekers, vacancies = 100 * u + s * 90, s * 90
        assert np.isclose(clearer.matches(seekers, vacancies), vacancies)
        assert SearchFrictionsLabourMarketClearer.steady_state_matching_efficiency(0.1, 0.0, 0.5) == 1.0

    def test_employee_lists_follow_layoffs_and_hires(self):
        """Regression: laid-off workers stayed on their old firm's list (and on two lists once rehired)."""
        clearer = SearchFrictionsLabourMarketClearer(
            matching_efficiency=100.0, matching_elasticity=0.5, **CLEARER_PARAMETERS
        )
        firms, households, individuals = _one_firm_market(n_employed=6, n_unemployed=4, desired_labour=3.0)

        clearer.clear(firms=firms, households=households, individuals=individuals)

        corresponding_firm = individuals.states["Corresponding Firm ID"]
        assert sorted(firms.states["Employments"][0]) == list(np.flatnonzero(corresponding_firm == 0))
        assert len(firms.states["Employments"][0]) == 3

    def test_poledna_clear_marks_unassigned_active_individuals_as_unemployed(self):
        clearer = PolednaLabourMarketClearer(
            hiring_speed=0.0,
            firing_speed=0.0,
            random_firing_probability=0.0,
            sorted_firing=False,
            optimised_hiring=True,
            allow_switching_industries=True,
            consider_reservation_wages=False,
            firing_cost_fraction=0.0,
            hiring_cost_fraction=0.0,
            individuals_quitting=False,
            individuals_quitting_temperature=0.0,
            compare_with_normalised_inputs=False,
            round_target_employment=False,
        )

        firms = SimpleNamespace(
            ts=_DummyTS(
                {
                    "labour_inputs": np.array([1.0]),
                    "desired_labour_inputs": np.array([1.0]),
                    "n_firms": 1,
                }
            ),
            states={
                "Employments": [[0]],
                "Industry": np.array([0]),
                "Labour Productivity by Industry": np.array([1.0]),
            },
        )
        households = SimpleNamespace(ts=_DummyTS({"wealth": np.array([0.0, 0.0])}))
        individuals = SimpleNamespace(
            ts=_DummyTS(
                {
                    "labour_inputs": np.array([1.0, 0.0]),
                    "employee_income": np.array([1.0, 0.0]),
                    "reservation_wages": np.array([0.0, 0.0]),
                }
            ),
            states={
                "Activity Status": np.array([ActivityStatus.EMPLOYED, ActivityStatus.EMPLOYED], dtype=object),
                "Employment Industry": np.array([0, 0]),
                "Corresponding Firm ID": np.array([0, -1]),
                "Corresponding Household ID": np.array([0, 1]),
                "Offered Wage of Accepted Job": np.zeros(2),
            },
        )

        clearer.clear(firms=firms, households=households, individuals=individuals)

        assert individuals.states["Activity Status"][0] == ActivityStatus.EMPLOYED
        assert individuals.states["Activity Status"][1] == ActivityStatus.UNEMPLOYED
