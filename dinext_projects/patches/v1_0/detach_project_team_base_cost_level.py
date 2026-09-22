import frappe
from frappe.model import delete_fields


def execute():
	"""Remove PL-owned virtual DocField without DDL.

	`base_cost_level` is re-owned as a Custom Field by dinext_projects_pl.
	"""
	delete_fields({"Project Team Details": ["base_cost_level"]}, delete=0)
	frappe.clear_cache(doctype="Project Team Details")
