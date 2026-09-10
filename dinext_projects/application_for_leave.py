from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

AFL_WORKFLOW = "AFL Workflow"
AFL_PENDING_STATE = "На согласовании"
AFL_REJECTION_ACTION = "Не согласовано"
AFL_REJECTION_STATE = "Отклонено"
AFL_CORRECTION_TEMPLATE = "Dinext Workflow Correction"

_AFL_SERVER_SCRIPTS = ("AFL_Calculate_Hours", "AFL_Projects")
_AFL_CLIENT_SCRIPT = "AFL_Approval_V3"


def validate_application_for_leave(
	doc: Document,
	method: str | None = None,
) -> None:
	"""Validate AFL business data before generic workflow snapshot hooks run."""
	del method
	calculate_total_hours(doc)
	rebuild_user_projects(doc)


def calculate_total_hours(doc: Document) -> None:
	start_date, end_date = _leave_dates(doc)

	worker_name = doc.get("alworker")
	if not worker_name:
		frappe.throw(_("Worker is required."))

	worker = frappe.get_doc("Worker", worker_name)
	if not doc.get("lauser"):
		doc.lauser = worker.get("wuser")
	if not doc.get("lauser"):
		frappe.throw(_("Worker {0} has no user.").format(frappe.bold(worker_name)))

	holiday_list_name = worker.get("wholiday_list")
	if not holiday_list_name:
		frappe.throw(
			_("Worker {0} has no Holiday List.").format(frappe.bold(worker_name))
		)
	holiday_list = frappe.get_doc("Holiday List", holiday_list_name)
	_validate_coverage(
		holiday_list,
		start_date,
		end_date,
		from_field="from_date",
		to_field="to_date",
		label=_("Holiday List"),
	)

	template_name = worker.get("wtimesheet_template")
	if not template_name:
		frappe.throw(
			_("Worker {0} has no Timesheet Template.").format(
				frappe.bold(worker_name)
			)
		)
	template = frappe.get_doc("Timesheet Template", template_name)

	working_hours_name = template.get("tt_working_hours_on_date")
	if not working_hours_name:
		frappe.throw(
			_("Timesheet Template {0} has no Working Hours On Date.").format(
				frappe.bold(template_name)
			)
		)
	working_hours = frappe.get_doc("Working Hours On Date", working_hours_name)
	_validate_coverage(
		working_hours,
		start_date,
		end_date,
		from_field="hod_from_date",
		to_field="hod_to_date",
		label=_("Working Hours On Date"),
	)

	holiday_dates = {
		getdate(row.holiday_date)
		for row in holiday_list.get("holidays", [])
		if row.get("holiday_date")
	}
	hours_by_date = {
		getdate(row.wht_date): flt(row.wht_hours)
		for row in working_hours.get("hod_working_hours_table", [])
		if row.get("wht_date")
	}
	default_hours = flt(template.get("hours_on_date")) or 8

	total_hours = 0.0
	for working_date in _dates_between(start_date, end_date):
		if working_date in holiday_dates:
			continue

		day_hours = hours_by_date.get(working_date, default_hours)
		if working_date == start_date:
			day_hours = min(flt(doc.get("alfrom_hours")), day_hours)
			doc.alfrom_hours = day_hours
		elif working_date == end_date:
			day_hours = min(flt(doc.get("alto_hours")), day_hours)
			doc.alto_hours = day_hours
		total_hours += day_hours

	doc.al_total_hours = total_hours


def rebuild_user_projects(doc: Document) -> None:
	"""Rebuild AFL project rows from active, overlapping team memberships."""
	if doc.get("status") != AFL_PENDING_STATE:
		return

	start_date, end_date = _leave_dates(doc)
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
	projects_by_name: dict[str, Any] = {}
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

	doc.clear("user_projects")
	for project_name in sorted(project_names):
		doc.append("user_projects", {"project": project_name})


def configure_application_for_leave() -> None:
	"""Make the typed AFL owner authoritative after fixtures are synchronized."""
	workflow_changed = False
	if frappe.db.exists("Workflow", AFL_WORKFLOW):
		workflow = frappe.get_doc("Workflow", AFL_WORKFLOW)
		for transition in workflow.transitions:
			if (
				transition.state == AFL_PENDING_STATE
				and transition.action == AFL_REJECTION_ACTION
				and not transition.custom_comment_is_required
			):
				transition.custom_comment_is_required = 1
				workflow_changed = True

		for state in workflow.states:
			if (
				state.state == AFL_REJECTION_STATE
				and state.next_action_email_template != AFL_CORRECTION_TEMPLATE
			):
				state.next_action_email_template = AFL_CORRECTION_TEMPLATE
				workflow_changed = True

		if workflow_changed:
			workflow.save(ignore_permissions=True)

	for script_name in _AFL_SERVER_SCRIPTS:
		if frappe.db.exists("Server Script", script_name):
			frappe.db.set_value(
				"Server Script",
				script_name,
				"disabled",
				1,
				update_modified=False,
			)

	frappe.delete_doc(
		"Client Script",
		_AFL_CLIENT_SCRIPT,
		force=True,
		ignore_permissions=True,
		ignore_missing=True,
	)
	frappe.clear_cache()


def _leave_dates(doc: Document) -> tuple[date, date]:
	if not doc.get("alfrom_date") or not doc.get("alto_date"):
		frappe.throw(_("Start and end dates are required."))

	start_date = getdate(doc.alfrom_date)
	end_date = getdate(doc.alto_date)
	if start_date > end_date:
		frappe.throw(_("Start date cannot be after end date."))
	return start_date, end_date


def _validate_coverage(
	coverage_doc: Document,
	start_date: date,
	end_date: date,
	*,
	from_field: str,
	to_field: str,
	label: str,
) -> None:
	coverage_start = coverage_doc.get(from_field)
	coverage_end = coverage_doc.get(to_field)
	if (
		not coverage_start
		or not coverage_end
		or getdate(coverage_start) > start_date
		or getdate(coverage_end) < end_date
	):
		frappe.throw(
			_("{0} {1} does not cover the leave period.").format(
				label,
				frappe.bold(coverage_doc.name),
			)
		)


def _dates_between(start_date: date, end_date: date):
	current_date = start_date
	while current_date <= end_date:
		yield current_date
		current_date += timedelta(days=1)


def _ranges_overlap(
	start_date: date,
	end_date: date,
	range_start: date,
	range_end: date,
) -> bool:
	return start_date <= range_end and end_date >= range_start
