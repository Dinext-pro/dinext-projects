import frappe
from frappe.model import delete_fields


def execute():
	"""Remove checkbox DocFields re-owned by other apps without dropping DB columns.

	`virtual_worker` -> dinext_projects_pl
	`allow_approval` -> dinext_timesheets
	`pt_allow_pss` -> dinext_project_tasks_gantt
	`notifications_on_limits` -> project_workload_assignment
	"""
	fields = [
		"virtual_worker",
		"allow_approval",
		"pt_allow_pss",
		"notifications_on_limits",
	]
	delete_fields({"Project Team Details": fields}, delete=0)
	frappe.clear_cache(doctype="Project Team Details")
