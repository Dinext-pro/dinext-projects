# Copyright (c) 2026, Dinext and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from dinext_projects.dinext_projects.doctype.project_contact_list.project_contact_list import (
	_validate_score,
)


class TestProjectContactList(FrappeTestCase):
	def test_empty_scores_are_allowed(self):
		_validate_score(None, "influence")
		_validate_score("", "interest")

	def test_bounds_are_allowed(self):
		_validate_score(1, "influence")
		_validate_score(10, "interest")
		_validate_score("8", "influence")

	def test_out_of_range_and_fractions_are_rejected(self):
		for fieldname, value in (
			("influence", 0),
			("influence", 11),
			("interest", -1),
			("interest", 1.5),
			("influence", "1.5"),
			("interest", True),
		):
			with self.assertRaises(frappe.ValidationError):
				_validate_score(value, fieldname)

	def test_row_validate_rejects_eleven(self):
		row = frappe.get_doc(
			{
				"doctype": "Project Contact List",
				"contact": "Stakeholder Matrix Contact",
				"influence": 11,
				"interest": 3,
			}
		)
		with self.assertRaises(frappe.ValidationError):
			row.validate()
