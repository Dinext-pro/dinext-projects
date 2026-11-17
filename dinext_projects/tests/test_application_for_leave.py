from __future__ import annotations

import json
from datetime import date
from unittest import TestCase
from unittest.mock import patch

import frappe
from frappe.core.doctype.server_script import server_script_utils

from dinext_projects.application_for_leave import (
	AFL_REJECTION_ACTION,
	AFL_REJECTION_STATE,
	calculate_total_hours,
	rebuild_user_projects,
	validate_application_for_leave,
	validate_leave_overlap,
	validate_workflow_vote,
)


class LeaveDocument(frappe._dict):
	def __init__(self, **values):
		super().__init__(values)
		self.set_calls = []

	def set(self, fieldname: str, value) -> None:
		recorded = list(value) if isinstance(value, list) else value
		self.set_calls.append((fieldname, recorded))
		self[fieldname] = value

	def append(self, fieldname: str, value: dict) -> None:
		self.setdefault(fieldname, []).append(frappe._dict(value))

	def is_new(self) -> bool:
		return bool(self.get("__islocal"))


class TestApplicationForLeave(TestCase):
	def setUp(self):
		legacy_scripts = patch.object(server_script_utils, "get_server_script_map", return_value={})
		self.legacy_scripts = legacy_scripts.start()
		self.addCleanup(legacy_scripts.stop)
		get_value = patch.object(frappe.db, "get_value", return_value=None)
		get_value.start()
		self.addCleanup(get_value.stop)

	def test_dates_are_required_and_ordered(self):
		for values in (
			{"alfrom_date": None, "alto_date": "2026-01-05"},
			{"alfrom_date": "2026-01-05", "alto_date": None},
			{"alfrom_date": "2026-01-06", "alto_date": "2026-01-05"},
		):
			with self.subTest(values=values), self.assertRaises(frappe.ValidationError):
				validate_application_for_leave(LeaveDocument(**values))

	def test_requires_the_workers_user_before_calculating_hours_or_projects(self):
		for worker_user in (None, "worker@example.com"):
			with self.subTest(worker_user=worker_user):
				doc = LeaveDocument(
					alfrom_date="2026-01-05",
					alto_date="2026-01-06",
					alworker="WRKR-1",
					lauser="other@example.com",
					status="Pending Approval",
					user_projects=[frappe._dict(project="BEFORE")],
				)
				worker = frappe._dict(wuser=worker_user, wholiday_list="RU Holidays")

				def get_doc(doctype, name, **kwargs):
					self.assertEqual((doctype, name), ("Worker", "WRKR-1"))
					return worker

				with (
					patch("dinext_projects.application_for_leave.frappe.get_doc", side_effect=get_doc),
					self.assertRaises(frappe.ValidationError),
				):
					validate_application_for_leave(doc)

				self.assertIsNone(doc.al_total_hours)
				self.assertEqual(doc.user_projects, [{"project": "BEFORE"}])

	def test_legacy_before_save_scripts_keep_ownership_until_cutover(self):
		self.legacy_scripts.return_value = {
			"Application For Leave": {"Before Save": ["AFL_Calculate_Hours", "AFL_Projects"]},
		}
		doc = LeaveDocument(
			doctype="Application For Leave",
			alfrom_date="2026-01-05",
			alto_date="2026-01-06",
			alworker="WRKR-1",
			status="Pending Approval",
			al_total_hours=7,
			user_projects=[frappe._dict(project="BEFORE")],
		)
		worker = frappe._dict(wuser="worker@example.com")
		with patch("dinext_projects.application_for_leave.frappe.get_doc", return_value=worker):
			validate_application_for_leave(doc)

		self.assertEqual(doc.lauser, "worker@example.com")
		self.assertEqual(doc.al_total_hours, 7)
		self.assertEqual(doc.user_projects, [{"project": "BEFORE"}])

	def test_rejects_negative_hours_before_legacy_or_native_calculation(self):
		for scripts in ([], ["AFL_Calculate_Hours"]):
			self.legacy_scripts.return_value = {"Application For Leave": {"Before Save": scripts}}
			for field in ("alfrom_hours", "alto_hours"):
				doc = LeaveDocument(
					alfrom_date="2026-01-05",
					alto_date="2026-01-06",
					alworker="WRKR-1",
					alfrom_hours=5,
					alto_hours=3,
				)
				doc[field] = -1
				worker = frappe._dict(wuser="worker@example.com")
				with (
					self.subTest(scripts=scripts, field=field),
					patch("dinext_projects.application_for_leave.frappe.get_doc", return_value=worker),
					self.assertRaisesRegex(frappe.ValidationError, "Leave hours cannot be negative"),
				):
					validate_application_for_leave(doc)

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
			side_effect=lambda doctype, name, **kwargs: documents[(doctype, name)],
		):
			calculate_total_hours(doc)

		self.assertEqual(doc.lauser, "worker@example.com")
		self.assertEqual(doc.alfrom_hours, 8)
		self.assertEqual(doc.alto_hours, 3)
		self.assertEqual(doc.al_total_hours, 17)

		for holidays, expected in (
			((date(2026, 1, 5), date(2026, 1, 6)), (0, 3, 9)),
			((date(2026, 1, 6), date(2026, 1, 8)), (8, 0, 14)),
			((date(2026, 1, 5), date(2026, 1, 8)), (0, 0, 14)),
		):
			with self.subTest(holidays=holidays):
				doc.alfrom_hours = 10
				doc.alto_hours = 3
				holiday_list.holidays = [frappe._dict(holiday_date=day) for day in holidays]
				with patch(
					"dinext_projects.application_for_leave.frappe.get_doc",
					side_effect=lambda doctype, name, **kwargs: documents[(doctype, name)],
				):
					calculate_total_hours(doc)

				self.assertEqual((doc.alfrom_hours, doc.alto_hours, doc.al_total_hours), expected)

	def test_overlapping_applications_include_boundary_dates_and_exclude_only_self_and_cancelled(self):
		doc = LeaveDocument(
			name="current",
			alworker="WRKR-1",
			alfrom_date="2026-01-05",
			alto_date="2026-01-06",
		)
		worker = frappe._dict(wuser="worker@example.com")
		for stored, new, blocked in (
			({"alfrom_date": date(2026, 1, 6)}, False, True),
			({"alto_date": date(2026, 1, 5), "status": "Rejected"}, False, True),
			({"alfrom_date": date(2026, 1, 7)}, False, False),
			({"docstatus": 2}, False, False),
			({"alworker": "WRKR-2"}, False, False),
			({"name": "current"}, False, False),
			({"name": "current"}, True, True),
		):
			row = {
				"name": "other",
				"alworker": "WRKR-1",
				"alfrom_date": date(2026, 1, 5),
				"alto_date": date(2026, 1, 6),
				"docstatus": 0,
				**stored,
			}
			doc["__islocal"] = new

			def get_value(doctype, filters, fieldname, *, for_update=False):
				self.assertTrue(for_update)
				self.assertEqual(doctype, "Application For Leave")
				operators = {"<=": lambda a, b: a <= b, ">=": lambda a, b: a >= b, "!=": lambda a, b: a != b}
				for field, expected in filters.items():
					value = row[field]
					if isinstance(expected, tuple):
						operator, argument = expected
						matches = operators[operator](value, argument)
					else:
						matches = value == expected
					if not matches:
						return None
				return row[fieldname]

			with (
				self.subTest(stored=stored, new=new),
				patch("dinext_projects.application_for_leave.frappe.get_doc", return_value=worker),
				patch.object(frappe.db, "get_value", side_effect=get_value),
			):
				if blocked:
					with self.assertRaisesRegex(frappe.ValidationError, "already has a leave application"):
						validate_leave_overlap(doc)
				else:
					validate_leave_overlap(doc)

	def test_approval_waits_if_all_snapshotted_projects_are_closed(self):
		from dinext_common.workflow_approval.engine import WorkflowDomainRollbackError

		doc = LeaveDocument(status="Pending Approval", user_projects=[frappe._dict(project="PROJ-1")])
		with self.assertRaisesRegex(WorkflowDomainRollbackError, "All projects for this leave application"):
			validate_workflow_vote(doc, "Approved")
		with patch.object(frappe.db, "get_value", return_value="PROJ-1"):
			validate_workflow_vote(doc, "Approved")

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
			side_effect=lambda doctype, name, **kwargs: documents[(doctype, name)],
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
						side_effect=lambda doctype, name, **kwargs: documents[(doctype, name)],
					),
					self.assertRaises(frappe.ValidationError),
				):
					calculate_total_hours(doc)

	def test_rebuilds_projects_once_in_deterministic_order(self):
		doc = LeaveDocument(
			status="Pending Approval",
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

		self.assertEqual(doc.set_calls, [("user_projects", [])])
		self.assertEqual(
			[row.project for row in doc.user_projects],
			["PROJ-1", "PROJ-2"],
		)

	def test_ordinary_migration_configures_rejection_without_changing_scripts(self):
		from dinext_projects.install import after_migrate

		workflow = frappe._dict(
			transitions=[
				frappe._dict(
					state="Pending Approval",
					action=AFL_REJECTION_ACTION,
					custom_comment_is_required=0,
				),
				frappe._dict(
					state="Pending Approval",
					action="Approve",
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
			patch("dinext_projects.setup.dinext_hub.register_dinext_hub_items"),
		):
			after_migrate()

		self.assertEqual(workflow.transitions[0].custom_comment_is_required, 1)
		self.assertEqual(workflow.transitions[1].custom_comment_is_required, 0)
		self.assertEqual(
			workflow.states[0].next_action_email_template,
			"Dinext Workflow Correction",
		)
		self.assertEqual(workflow.save_count, 1)
		set_value.assert_not_called()
		delete_doc.assert_not_called()
		clear_cache.assert_called_once_with()

	def test_hook_owns_afl_validation(self):
		from dinext_projects import hooks

		self.assertEqual(
			hooks.doc_events["Application For Leave"]["validate"],
			"dinext_projects.application_for_leave.validate_application_for_leave",
		)
		self.assertEqual(
			hooks.doc_events["Application For Leave"]["before_validate"],
			"dinext_projects.application_for_leave.validate_leave_overlap",
		)
		self.assertEqual(
			hooks.doctype_js["Application For Leave"],
			"public/js/application_for_leave_approvals.js",
		)

	def test_afl_client_adapter_replaces_legacy_script(self):
		from pathlib import Path

		app_path = Path(__file__).resolve().parents[1]
		script = (app_path / "public/js/application_for_leave_approvals.js").read_text()
		self.assertIn("End date cannot be earlier than start date", script)
		self.assertNotIn("frappe.msgprint = function", script)
		self.assertNotIn("wt_docname", script)
		fixtures = json.loads((app_path / "fixtures" / "client_script.json").read_text())
		names = {row["name"] for row in fixtures}
		self.assertNotIn("AFL_Approval_V3", names)
		self.assertNotIn("Workflow_Task_Route", names)
		server = json.loads((app_path / "fixtures" / "server_script.json").read_text())
		self.assertNotIn("Workflow Task Assign", {row["name"] for row in server})
