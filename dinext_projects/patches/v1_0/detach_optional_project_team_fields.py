import frappe
from frappe.model import delete_fields


def execute():
	"""Remove optional cross-app DocFields without dropping DB columns.

	`pt_worker`, `pt_cost_level`, and `pt_category` are re-owned as Custom Fields
	by dinext_timesheets / dinext_projects_pl using the same fieldnames.
	"""
	fields = ["pt_worker", "pt_cost_level", "pt_category"]
	delete_fields({"Project Team Details": fields}, delete=0)
	frappe.clear_cache(doctype="Project Team Details")
