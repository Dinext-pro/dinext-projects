from datetime import date
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import frappe

from dinext_projects import hooks
from dinext_projects.application_for_leave import rebuild_user_projects, validate_approval_projects


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


class TestLeaveProjects(TestCase):
	def test_registers_only_project_operations_for_leave(self):
		self.assertNotIn("Application For Leave", hooks.doc_events)
		self.assertNotIn("Application For Leave", hooks.doctype_js)
		self.assertEqual(
			hooks.application_for_leave_project_handlers,
			{
				"rebuild": "dinext_projects.application_for_leave.rebuild_user_projects",
				"validate_approval": "dinext_projects.application_for_leave.validate_approval_projects",
			},
		)

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
			rebuild_user_projects(doc, date(2026, 1, 5), date(2026, 1, 8))

		self.assertEqual(doc.set_calls, [("user_projects", [])])
		self.assertEqual(
			[row.project for row in doc.user_projects],
			["PROJ-1", "PROJ-2"],
		)

	def test_approval_requires_an_open_snapshotted_project(self):
		doc = LeaveDocument(status="Pending Approval", user_projects=[frappe._dict(project="PROJ-1")])

		def get_value(doctype, filters, field, *, for_update):
			self.assertEqual((doctype, field, for_update), ("Project", "name", True))
			self.assertEqual(filters, {"name": ("in", ["PROJ-1"]), "status": "Open"})
			return open_project

		with (
			patch.object(frappe, "db", SimpleNamespace(get_value=get_value)),
			patch.object(frappe, "flags", frappe._dict(mute_messages=True)),
			patch("frappe.translate.get_all_translations", return_value={}),
		):
			open_project = None
			with self.assertRaisesRegex(frappe.ValidationError, "All projects for this leave application"):
				validate_approval_projects(doc)
			open_project = "PROJ-1"
			validate_approval_projects(doc)
