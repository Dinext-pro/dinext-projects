# Copyright (c) 2026, Dinext and contributors
# See license.txt
"""ISS-2026-03288 live-site scenario. Port of ISS-2025-02606 after SS → app hooks."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

from .data_setup import (
    EARLY_START_FACT_ROWS,
    INSIDE_PLAN_FACT_ROWS,
    LATE_END_FACT_ROWS,
    REGULAR_TASK_EXP_END,
    REGULAR_TASK_EXP_START,
    SAME_RANGE_FACT_ROWS,
    SECOND_AGGREGATE_FACT_ROWS,
    WIDE_FACT_ROWS,
    build_regular_task_scenario,
    change_position_status,
    reset_scenario,
)


class TestIss202603288UtpActDates(FrappeTestCase):
    @classmethod
    def tearDownClass(cls):
        reset_scenario()
        super().tearDownClass()

    def setUp(self):
        reset_scenario()

    def test_approved_utp_within_plan_keeps_expected_dates_unchanged(self):
        bundle = build_regular_task_scenario(primary_rows=INSIDE_PLAN_FACT_ROWS)

        change_position_status(bundle["wide_position"], "Согласовано")

        task = frappe.get_doc("Task", bundle["task"])

        self.assertEqual(getdate(INSIDE_PLAN_FACT_ROWS[0][0]), task.act_start_date)
        self.assertEqual(getdate(INSIDE_PLAN_FACT_ROWS[1][0]), task.act_end_date)
        self.assertEqual(getdate(REGULAR_TASK_EXP_START), task.exp_start_date)
        self.assertEqual(getdate(REGULAR_TASK_EXP_END), task.exp_end_date)

    def test_return_from_approved_to_editing_keeps_existing_fact(self):
        bundle = build_regular_task_scenario(primary_rows=INSIDE_PLAN_FACT_ROWS)

        change_position_status(bundle["wide_position"], "Согласовано")
        change_position_status(bundle["wide_position"], "Редактирование")

        task = frappe.get_doc("Task", bundle["task"])

        self.assertEqual(getdate(INSIDE_PLAN_FACT_ROWS[0][0]), task.act_start_date)
        self.assertEqual(getdate(INSIDE_PLAN_FACT_ROWS[1][0]), task.act_end_date)
        self.assertEqual("Open", task.status)

    def test_reapproving_same_position_restores_same_fact_range(self):
        bundle = build_regular_task_scenario(primary_rows=INSIDE_PLAN_FACT_ROWS)

        change_position_status(bundle["wide_position"], "Согласовано")
        change_position_status(bundle["wide_position"], "Редактирование")
        change_position_status(bundle["wide_position"], "Согласовано")

        task = frappe.get_doc("Task", bundle["task"])

        self.assertEqual(getdate(INSIDE_PLAN_FACT_ROWS[0][0]), task.act_start_date)
        self.assertEqual(getdate(INSIDE_PLAN_FACT_ROWS[1][0]), task.act_end_date)

    def test_early_fact_moves_only_expected_start_date(self):
        bundle = build_regular_task_scenario(primary_rows=EARLY_START_FACT_ROWS)

        change_position_status(bundle["wide_position"], "Согласовано")

        task = frappe.get_doc("Task", bundle["task"])

        self.assertEqual(getdate(EARLY_START_FACT_ROWS[0][0]), task.act_start_date)
        self.assertEqual(getdate(EARLY_START_FACT_ROWS[1][0]), task.act_end_date)
        self.assertEqual(getdate(EARLY_START_FACT_ROWS[0][0]), task.exp_start_date)
        self.assertEqual(getdate(REGULAR_TASK_EXP_END), task.exp_end_date)

    def test_late_fact_moves_only_expected_end_date(self):
        bundle = build_regular_task_scenario(primary_rows=LATE_END_FACT_ROWS)

        change_position_status(bundle["wide_position"], "Согласовано")

        task = frappe.get_doc("Task", bundle["task"])

        self.assertEqual(getdate(LATE_END_FACT_ROWS[0][0]), task.act_start_date)
        self.assertEqual(getdate(LATE_END_FACT_ROWS[1][0]), task.act_end_date)
        self.assertEqual(getdate(REGULAR_TASK_EXP_START), task.exp_start_date)
        self.assertEqual(getdate(LATE_END_FACT_ROWS[1][0]), task.exp_end_date)

    def test_two_approved_positions_aggregate_min_and_max_fact_dates(self):
        bundle = build_regular_task_scenario(
            primary_rows=LATE_END_FACT_ROWS,
            second_position_rows=SECOND_AGGREGATE_FACT_ROWS,
            second_position_key="aggregate_position",
        )

        change_position_status(bundle["wide_position"], "Согласовано")
        change_position_status(bundle["aggregate_position"], "Согласовано")

        task = frappe.get_doc("Task", bundle["task"])

        self.assertEqual(getdate(SECOND_AGGREGATE_FACT_ROWS[0][0]), task.act_start_date)
        self.assertEqual(getdate(LATE_END_FACT_ROWS[1][0]), task.act_end_date)

    def test_recalculation_does_not_shrink_or_clear_existing_fact(self):
        bundle = build_regular_task_scenario(include_narrow_position=True)

        change_position_status(bundle["wide_position"], "Согласовано")
        change_position_status(bundle["narrow_position"], "Согласовано")
        change_position_status(bundle["wide_position"], "Редактирование")

        task = frappe.get_doc("Task", bundle["task"])
        expected_start = getdate(WIDE_FACT_ROWS[0][0])
        expected_end = getdate(WIDE_FACT_ROWS[1][0])

        self.assertEqual(expected_start, task.act_start_date)
        self.assertEqual(expected_end, task.act_end_date)

        change_position_status(bundle["narrow_position"], "Редактирование")

        task.reload()
        self.assertEqual(expected_start, task.act_start_date)
        self.assertEqual(expected_end, task.act_end_date)

    def test_removing_last_approved_position_after_series_keeps_fact(self):
        bundle = build_regular_task_scenario(include_narrow_position=True)

        change_position_status(bundle["wide_position"], "Согласовано")
        change_position_status(bundle["narrow_position"], "Согласовано")
        change_position_status(bundle["wide_position"], "Редактирование")
        change_position_status(bundle["narrow_position"], "Редактирование")

        task = frappe.get_doc("Task", bundle["task"])

        self.assertEqual(getdate(WIDE_FACT_ROWS[0][0]), task.act_start_date)
        self.assertEqual(getdate(WIDE_FACT_ROWS[1][0]), task.act_end_date)

    def test_non_shrinking_remaining_period_keeps_full_fact_range(self):
        bundle = build_regular_task_scenario(
            primary_rows=WIDE_FACT_ROWS,
            second_position_rows=SAME_RANGE_FACT_ROWS,
            second_position_key="same_range_position",
        )

        change_position_status(bundle["wide_position"], "Согласовано")
        change_position_status(bundle["same_range_position"], "Согласовано")
        change_position_status(bundle["wide_position"], "Редактирование")

        task = frappe.get_doc("Task", bundle["task"])

        self.assertEqual(getdate(WIDE_FACT_ROWS[0][0]), task.act_start_date)
        self.assertEqual(getdate(WIDE_FACT_ROWS[1][0]), task.act_end_date)
