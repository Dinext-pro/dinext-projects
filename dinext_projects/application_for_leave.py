"""Project membership and approvals for leave applications."""

from __future__ import annotations

from datetime import date

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


def rebuild_user_projects(doc: Document, start_date: date, end_date: date) -> None:
	"""Rebuild AFL project rows from active, overlapping team memberships."""
	if doc.get("status") != "Pending Approval":
		return

	user = doc.get("lauser")
	if not user:
		return

	team_fields = ["parent", "pt_valid_from", "pt_valid_for"]
	team_rows = frappe.get_all(
		"Project Team Details",
		filters={
			"pt_participant_type": "User",
			"pt_participant": user,
		},
		fields=team_fields,
	)

	user_groups = frappe.get_all(
		"User Group Member",
		filters={"user": user},
		pluck="parent",
	)
	if user_groups:
		team_rows.extend(
			frappe.get_all(
				"Project Team Details",
				filters={
					"pt_participant_type": "User Group",
					"pt_participant": ["in", user_groups],
				},
				fields=team_fields,
			)
		)

	candidate_names = sorted({row.parent for row in team_rows if row.get("parent")})
	projects_by_name: dict[str, frappe._dict] = {}
	if candidate_names:
		projects_by_name = {
			project.name: project
			for project in frappe.get_all(
				"Project",
				filters={"name": ["in", candidate_names], "status": "Open"},
				fields=["name", "expected_start_date", "expected_end_date"],
			)
		}

	project_names: set[str] = set()
	for row in team_rows:
		project = projects_by_name.get(row.parent)
		if not project:
			continue

		valid_from = row.get("pt_valid_from")
		valid_for = row.get("pt_valid_for")
		if valid_from and valid_for:
			if _ranges_overlap(
				start_date,
				end_date,
				getdate(valid_from),
				getdate(valid_for),
			):
				project_names.add(project.name)
			continue

		if valid_from or valid_for:
			continue

		expected_start = project.get("expected_start_date")
		expected_end = project.get("expected_end_date")
		if expected_start and expected_end and _ranges_overlap(
			start_date,
			end_date,
			getdate(expected_start),
			getdate(expected_end),
		):
			project_names.add(project.name)

	doc.set("user_projects", [])
	for project_name in sorted(project_names):
		doc.append("user_projects", {"project": project_name})


def validate_approval_projects(doc: Document) -> None:
	"""Lock an open project while the final leave vote is applied."""
	project_names = [row.project for row in doc.get("user_projects", []) if row.project]
	if project_names and not frappe.db.get_value(
		"Project", {"name": ("in", project_names), "status": "Open"}, "name", for_update=True,
	):
		frappe.throw(_("All projects for this leave application are closed. Reopen a project before approving."))


def _ranges_overlap(
	start_date: date,
	end_date: date,
	range_start: date,
	range_end: date,
) -> bool:
	return start_date <= range_end and end_date >= range_start
