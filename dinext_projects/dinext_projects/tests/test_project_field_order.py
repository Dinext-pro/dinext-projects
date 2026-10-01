# Copyright (c) Dinext. License: GNU GPL v3. See license.txt

import json
import os

import frappe
from frappe.tests.utils import FrappeTestCase

FIELD_ORDER_PROPERTY_SETTER = "Project-main-field_order"


def _load_fixture(app, filename):
	path = frappe.get_app_path(app, "fixtures", filename)
	if not os.path.exists(path):
		return []
	with open(path, encoding="utf-8") as f:
		return json.load(f)


def _shipped_field_order():
	for row in _load_fixture("dinext_projects", "property_setter.json"):
		if row.get("name") == FIELD_ORDER_PROPERTY_SETTER:
			return row
	return None


class TestProjectFieldOrder(FrappeTestCase):
	def test_field_order_is_shipped_with_dinext_projects(self):
		row = _shipped_field_order()

		self.assertIsNotNone(row, f"{FIELD_ORDER_PROPERTY_SETTER} is missing from dinext_projects fixtures")
		self.assertEqual(row["doc_type"], "Project")
		self.assertEqual(row["property"], "field_order")
		self.assertTrue(json.loads(row["value"]))

	def test_field_order_covers_project_custom_fields_of_installed_apps(self):
		row = _shipped_field_order()
		self.assertIsNotNone(row)
		field_order = set(json.loads(row["value"]))

		missing = {
			f"{app}:{field['fieldname']}"
			for app in frappe.get_installed_apps()
			for field in _load_fixture(app, "custom_field.json")
			if field.get("dt") == "Project" and field["fieldname"] not in field_order
		}

		self.assertFalse(
			missing,
			f"Project custom fields absent from {FIELD_ORDER_PROPERTY_SETTER}: {sorted(missing)}",
		)
