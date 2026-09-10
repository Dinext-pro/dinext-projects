from __future__ import annotations

import json
from datetime import date
from unittest import TestCase
from unittest.mock import patch

import frappe

from dinext_projects.application_for_leave import (
	AFL_REJECTION_ACTION,
	AFL_REJECTION_STATE,
	calculate_total_hours,
	configure_application_for_leave,
	rebuild_user_projects,
	validate_application_for_leave,
)


class LeaveDocument(frappe._dict):
	def __init__(self, **values):
		super().__init__(values)
		self.clear_calls = 0

	def clear(self, fieldname: str) -> None:
		self.clear_calls += 1
		self[fieldname] = []

	def append(self, fieldname: str, value: dict) -> None:
		self.setdefault(fieldname, []).append(frappe._dict(value))


class TestApplicationForLeave(TestCase):
	def test_dates_are_required_and_ordered(self):
		for values in (
			{"alfrom_date": None, "alto_date": "2026-01-05"},
			{"alfrom_date": "2026-01-05", "alto_date": None},
			{"alfrom_date": "2026-01-06", "alto_date": "2026-01-05"},
		):
			with self.subTest(values=values), self.assertRaises(frappe.ValidationError):
				validate_application_for_leave(LeaveDocument(**values))

	def test_calculates_hours_with_holidays_overrides_and_boundary_clamps(self):
		doc = LeaveDocument(
			alfrom_date="2026-01-05",
			alto_date="2026-01-08",
			alworker="WRKR-1",
			lauser=None,
			alfrom_hours=10,
			alto_hours=3,
		)
		worker = frappe._dict(
			name="WRKR-1",
			wuser="worker@example.com",
			wholiday_list="RU Holidays",
			wtimesheet_template="RU Template",
		)
		holiday_list = frappe._dict(
			name="RU Holidays",
			from_date=date(2026, 1, 1),
			to_date=date(2026, 12, 31),
			holidays=[frappe._dict(holiday_date=date(2026, 1, 6))],
		)
		template = frappe._dict(
			name="RU Template",
			hours_on_date=8,
			tt_working_hours_on_date="RU Short Days",
		)
		hours_on_date = frappe._dict(
			name="RU Short Days",
			hod_from_date=date(2026, 1, 1),
			hod_to_date=date(2026, 12, 31),
			hod_working_hours_table=[
				frappe._dict(wht_date=date(2026, 1, 7), wht_hours=6),
			],
		)
		documents = {
			("Worker", "WRKR-1"): worker,
			("Holiday List", "RU Holidays"): holiday_list,
			("Timesheet Template", "RU Template"): template,
			("Working Hours On Date", "RU Short Days"): hours_on_date,
		}

		with patch(
			"dinext_projects.application_for_leave.frappe.get_doc",
			side_effect=lambda doctype, name: documents[(doctype, name)],
		):
			calculate_total_hours(doc)

		self.assertEqual(doc.lauser, "worker@example.com")
		self.assertEqual(doc.alfrom_hours, 8)
		self.assertEqual(doc.alto_hours, 3)
		self.assertEqual(doc.al_total_hours, 17)

	def test_one_day_leave_uses_only_first_day_clamp(self):
		doc = LeaveDocument(
			alfrom_date="2026-01-05",
			alto_date="2026-01-05",
			alworker="WRKR-1",
			lauser="worker@example.com",
			alfrom_hours=5,
			alto_hours=1,
		)
		documents = {
			("Worker", "WRKR-1"): frappe._dict(
				wuser="worker@example.com",
				wholiday_list="RU Holidays",
				wtimesheet_template="RU Template",
			),
			("Holiday List", "RU Holidays"): frappe._dict(
				name="RU Holidays",
				from_date=date(2026, 1, 1),
				to_date=date(2026, 12, 31),
				holidays=[],
			),
			("Timesheet Template", "RU Template"): frappe._dict(
				hours_on_date=8,
				tt_working_hours_on_date="RU Short Days",
			),
			("Working Hours On Date", "RU Short Days"): frappe._dict(
				name="RU Short Days",
				hod_from_date=date(2026, 1, 1),
				hod_to_date=date(2026, 12, 31),
				hod_working_hours_table=[],
			),
		}

		with patch(
			"dinext_projects.application_for_leave.frappe.get_doc",
			side_effect=lambda doctype, name: documents[(doctype, name)],
		):
			calculate_total_hours(doc)

		self.assertEqual(doc.alfrom_hours, 5)
		self.assertEqual(doc.alto_hours, 1)
		self.assertEqual(doc.al_total_hours, 5)

	def test_requires_holiday_and_working_hours_coverage(self):
		doc = LeaveDocument(
			alfrom_date="2026-01-05",
			alto_date="2026-01-08",
			alworker="WRKR-1",
			lauser="worker@example.com",
		)
		worker = frappe._dict(
			name="WRKR-1",
			wuser="worker@example.com",
			wholiday_list="RU Holidays",
			wtimesheet_template="RU Template",
		)
		template = frappe._dict(
			name="RU Template",
			hours_on_date=8,
			tt_working_hours_on_date="RU Short Days",
		)

		for invalid_document in (
			frappe._dict(
				name="RU Holidays",
				from_date=date(2026, 1, 6),
				to_date=date(2026, 12, 31),
				holidays=[],
			),
			frappe._dict(
				name="RU Short Days",
				hod_from_date=date(2026, 1, 6),
				hod_to_date=date(2026, 12, 31),
				hod_working_hours_table=[],
			),
		):
			with self.subTest(name=invalid_document.name):
				documents = {
					("Worker", "WRKR-1"): worker,
					("Holiday List", "RU Holidays"): (
						invalid_document
						if invalid_document.name == "RU Holidays"
						else frappe._dict(
							name="RU Holidays",
							from_date=date(2026, 1, 1),
							to_date=date(2026, 12, 31),
							holidays=[],
						)
					),
					("Timesheet Template", "RU Template"): template,
					("Working Hours On Date", "RU Short Days"): invalid_document,
				}
				with (
					patch(
						"dinext_projects.application_for_leave.frappe.get_doc",
						side_effect=lambda doctype, name: documents[(doctype, name)],
					),
					self.assertRaises(frappe.ValidationError),
				):
					calculate_total_hours(doc)

	def test_rebuilds_projects_once_in_deterministic_order(self):
		doc = LeaveDocument(
			status="На согласовании",
			lauser="worker@example.com",
			alfrom_date="2026-01-05",
			alto_date="2026-01-08",
			user_projects=[frappe._dict(project="OLD")],
		)

		def get_all(doctype, *, filters=None, fields=None, pluck=None, **kwargs):
			if doctype == "User Group Member":
				return ["Team A"]
			if doctype == "Project Team Details":
				if filters["pt_participant_type"] == "User":
					return [
						frappe._dict(
							parent="PROJ-2",
							pt_valid_from=date(2026, 1, 1),
							pt_valid_for=date(2026, 1, 31),
						),
						frappe._dict(
							parent="PROJ-3",
							pt_valid_from=date(2026, 1, 1),
							pt_valid_for=None,
						),
					]
				return [
					frappe._dict(parent="PROJ-1", pt_valid_from=None, pt_valid_for=None),
					frappe._dict(parent="PROJ-2", pt_valid_from=None, pt_valid_for=None),
				]
			if doctype == "Project":
				return [
					frappe._dict(
						name="PROJ-2",
						expected_start_date=date(2025, 1, 1),
						expected_end_date=date(2027, 1, 1),
					),
					frappe._dict(
						name="PROJ-1",
						expected_start_date=date(2025, 1, 1),
						expected_end_date=date(2027, 1, 1),
					),
					frappe._dict(
						name="PROJ-3",
						expected_start_date=date(2025, 1, 1),
						expected_end_date=date(2027, 1, 1),
					),
				]
			raise AssertionError(f"Unexpected DocType: {doctype}")

		with patch(
			"dinext_projects.application_for_leave.frappe.get_all",
			side_effect=get_all,
		):
			rebuild_user_projects(doc)

		self.assertEqual(doc.clear_calls, 1)
		self.assertEqual(
			[row.project for row in doc.user_projects],
			["PROJ-1", "PROJ-2"],
		)

	def test_cutover_sets_rejection_contract_and_disables_only_afl_duplicates(self):
		workflow = frappe._dict(
			transitions=[
				frappe._dict(
					state="На согласовании",
					action=AFL_REJECTION_ACTION,
					custom_comment_is_required=0,
				),
				frappe._dict(
					state="На согласовании",
					action="Согласовано",
					custom_comment_is_required=0,
				),
			],
			states=[
				frappe._dict(
					state=AFL_REJECTION_STATE,
					next_action_email_template=None,
				),
			],
		)
		workflow.save = lambda **kwargs: workflow.update(save_count=workflow.get("save_count", 0) + 1)

		with (
			patch(
				"dinext_projects.application_for_leave.frappe.db.exists",
				return_value=True,
			),
			patch(
				"dinext_projects.application_for_leave.frappe.get_doc",
				return_value=workflow,
			),
			patch(
				"dinext_projects.application_for_leave.frappe.db.set_value"
			) as set_value,
			patch(
				"dinext_projects.application_for_leave.frappe.delete_doc"
			) as delete_doc,
			patch(
				"dinext_projects.application_for_leave.frappe.clear_cache"
			) as clear_cache,
		):
			configure_application_for_leave()

		self.assertEqual(workflow.transitions[0].custom_comment_is_required, 1)
		self.assertEqual(workflow.transitions[1].custom_comment_is_required, 0)
		self.assertEqual(
			workflow.states[0].next_action_email_template,
			"Dinext Workflow Correction",
		)
		self.assertEqual(workflow.save_count, 1)
		disabled_names = {
			call.args[1]
			for call in set_value.call_args_list
			if call.args[0] == "Server Script"
		}
		self.assertEqual(disabled_names, {"AFL_Calculate_Hours", "AFL_Projects"})
		delete_doc.assert_called_once_with(
			"Client Script",
			"AFL_Approval_V3",
			force=True,
			ignore_permissions=True,
			ignore_missing=True,
		)
		clear_cache.assert_called_once_with()

	def test_hook_owns_afl_validation(self):
		from dinext_projects import hooks

		self.assertEqual(
			hooks.doc_events["Application For Leave"]["validate"],
			"dinext_projects.application_for_leave.validate_application_for_leave",
		)
		self.assertEqual(
			hooks.doctype_js["Application For Leave"],
			"public/js/application_for_leave_approvals.js",
		)

	def test_afl_client_adapter_replaces_legacy_script(self):
		from pathlib import Path

		app_path = Path(__file__).resolve().parents[1]
		script = (app_path / "public/js/application_for_leave_approvals.js").read_text()
		self.assertIn("dinext_common.workflow_approval.api.get_pending_approvers", script)
		self.assertIn("End date cannot be earlier than start date", script)
		self.assertNotIn("frappe.msgprint = function", script)
		self.assertNotIn("wt_docname", script)
		fixtures = json.loads((app_path / "fixtures" / "client_script.json").read_text())
		names = {row["name"] for row in fixtures}
		self.assertNotIn("AFL_Approval_V3", names)
		self.assertNotIn("Workflow_Task_Route", names)
		server = json.loads((app_path / "fixtures" / "server_script.json").read_text())
		self.assertNotIn("Workflow Task Assign", {row["name"] for row in server})
