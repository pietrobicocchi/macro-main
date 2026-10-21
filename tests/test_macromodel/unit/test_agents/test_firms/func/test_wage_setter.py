import numpy as np

from macromodel.agents.firms.func.wage_setter import WorkEffortFirmWageSetter


class TestFirmWageSetter:
    def test__set_wages(self):
        WorkEffortFirmWageSetter(
            labour_market_tightness_markup_scale=0.1,
            markup_time_span=12,
            max_increase_in_work_effort=1.5,
        ).set_employee_income(
            corresponding_firm=np.array([0, 1]),
            current_individual_labour_inputs=np.array([1.0, 2.0]),
            current_individual_stating_new_job=np.array([True, False]),
            current_employee_income=np.array([10.0, 20.0]),
            current_individual_offered_wage=np.array([2.0, 3.0]),
            current_target_production=np.array([2.0, 3.0]),
            current_limiting_capital_inputs=np.array([2.0, 3.0]),
            current_limiting_intermediate_inputs=np.array([2.0, 3.0]),
            labour_inputs_from_employees=np.array([2.0, 3.0]),
            industry_labour_productivity_by_firm=np.array([2.0, 3.0]),
            estimated_ppi_inflation=1.0,
            employee_social_insurance_tax=0.1,
            employer_social_insurance_tax=0.1,
            income_taxes=0.3,
            initial_wage_per_capita=np.array([2.0, 3.0]),
            current_wage_per_capita=np.array([2.0, 3.0]),
            current_labour_productivity_factor=np.ones(2),
            prev_labour_productivity_factor=np.ones(2),
            current_wage_tightness_markup=np.zeros(2),
        )


class TestWagePriceIndex:
    @staticmethod
    def _setter(speed: float) -> WorkEffortFirmWageSetter:
        return WorkEffortFirmWageSetter(
            labour_market_tightness_markup_scale=0.0,
            markup_time_span=4,
            max_increase_in_work_effort=1.5,
            cpi_indexation_speed=speed,
        )

    def test_full_indexation_follows_the_latest_cpi(self):
        assert self._setter(1.0).wage_price_index(np.array([1.0, 1.02, 1.05])) == 1.05

    def test_partial_indexation_closes_part_of_the_gap_each_quarter(self):
        # 1.0 -> 1.0 + 0.5 * (1.02 - 1.0) = 1.01 -> 1.01 + 0.5 * (1.05 - 1.01) = 1.03
        assert np.isclose(self._setter(0.5).wage_price_index(np.array([1.0, 1.02, 1.05])), 1.03)

    def test_stable_prices_leave_the_index_at_the_cpi(self):
        assert np.isclose(self._setter(0.25).wage_price_index(np.full(8, 1.1)), 1.1)
