import json
from unittest.mock import patch

import frappe

from dinext_common.tests.hub_test_utils import HubRegistrationTestCase
from dinext_common.tests.test_hub_catalog_defaults import REFERENCE
from dinext_common.setup.hub_catalog import register_hub_doctype_items
from dinext_projects.setup.dinext_hub import register_dinext_hub_items


class TestInitialHubContribution(HubRegistrationTestCase):
	def test_projects_registers_four_approved_document_lists_and_dimensions(self):
		register_dinext_hub_items()
		register_dinext_hub_items()
		self.settings.reload()
		self.assertEqual(len(self.settings.doctype_items), 4)
		for actual, expected in zip(self.settings.doctype_items, REFERENCE["doctype_items"]):
			for field, value in expected.items():
				if field in ("attention_filter", "list_filter"):
					self.assertEqual(json.loads(actual.get(field) or "[]"), json.loads(value or "[]"))
				else:
					self.assertEqual(actual.get(field), value, field)
		self.assertEqual(
			[(r.section, r.list_limit, r.card_columns) for r in self.settings.sections],
			[("My Work", 5, 3), ("Project Management", 8, 4)],
		)

	def test_existing_kanban_fallback_is_reused_and_edited_flags_survive_replay(self):
		fallback = {**REFERENCE["doctype_items"][1], "show_liked": 0}
		fallback.pop("source_app")
		register_hub_doctype_items([fallback], source_app="dinext_kanban")
		row = self.settings.doctype_items[0]
		row.show_assigned = 0
		row.list_filter = ""
		self.settings.save(ignore_permissions=True)
		for _ in range(2):
			register_dinext_hub_items()
		self.settings.reload()
		tasks = [r for r in self.settings.doctype_items if r.document_type == "Task"]
		self.assertEqual(len(tasks), 1)
		self.assertEqual(tasks[0].source_app, "dinext_projects")
		self.assertTrue(tasks[0].show_liked)
		self.assertFalse(tasks[0].show_assigned)
		self.assertFalse(tasks[0].list_filter)
