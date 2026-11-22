"""Maintain Issue groups from ToDo assignments."""

import json
from hashlib import sha256

import frappe
from frappe.core.doctype.server_script.server_script_utils import get_server_script_map

LEGACY_SCRIPT = "IssueAssignUserGroup"
# Common's shipped script body, with line endings normalized for database imports.
LEGACY_SCRIPT_SHA256 = "dfc3ba2783feb29361fb36480a260e1b1ad6ce7cb9c10c5bb44d745cfdd8960e"


def sync_issue_user_groups(doc, method=None):
	if doc.reference_type != "Issue" or not doc.reference_name:
		return
	if doc.status not in ("Open", "Closed", "Cancelled"):
		return
	if frappe.flags.in_install or frappe.flags.in_migrate:
		return
	if LEGACY_SCRIPT in get_server_script_map().get("ToDo", {}).get("After Save", ()):
		return

	issue = frappe.get_doc("Issue", doc.reference_name, for_update=True)
	rows = issue.get("custom_z_user_group") or []
	if doc.status == "Open":
		existing_groups = {row.user_group for row in rows}
		additions = [group for group in _groups_for_users([doc.allocated_to]) if group not in existing_groups]
		if additions:
			for group in additions:
				issue.append("custom_z_user_group", {"user_group": group})
			issue.custom_is_new = 0
			issue.save()
	elif rows:
		# ToDo.on_update has already locked the open assignments and written this list.
		assigned_users = json.loads(issue.get("_assign") or "[]")
		active_groups = set(_groups_for_users(assigned_users))
		inactive_rows = [row for row in rows if row.user_group not in active_groups]
		if not inactive_rows:
			return
		inactive_groups = set(
			frappe.get_all(
				"User Group",
				filters={"name": ("in", [row.user_group for row in inactive_rows])},
				pluck="name",
			)
		)
		removals = [row for row in inactive_rows if row.user_group in inactive_groups]
		if removals:
			for row in removals:
				issue.remove(row)
			issue.save()


def _groups_for_users(users):
	users = list(dict.fromkeys(user for user in users if user))
	if not users:
		return ()
	groups = frappe.get_all(
		"User Group Member",
		filters={
			"parenttype": "User Group",
			"parentfield": "user_group_members",
			"user": ("in", users),
		},
		pluck="parent",
		order_by="parent asc",
	)
	return tuple(dict.fromkeys(groups))


def retire_legacy_issue_assignment():
	"""Disable the verified Common fixture and preserve site-authored variants."""
	script = frappe.db.get_value(
		"Server Script",
		{
			"name": LEGACY_SCRIPT,
			"module": "Dinext Common",
			"script_type": "DocType Event",
			"reference_doctype": "ToDo",
			"doctype_event": "After Save",
			"disabled": 0,
		},
		"script",
		for_update=True,
	)
	if not script:
		return
	digest = sha256(script.replace("\r\n", "\n").strip().encode()).hexdigest()
	if digest != LEGACY_SCRIPT_SHA256:
		return
	frappe.db.set_value("Server Script", LEGACY_SCRIPT, "disabled", 1, update_modified=False)
	frappe.cache.delete_value("server_script_map")
	frappe.db.after_commit.add(lambda: frappe.cache.delete_value("server_script_map"))
