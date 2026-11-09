"""Working-date and Worker group-manager extensions without Timesheets imports."""

from datetime import date, datetime, timedelta

import frappe
from frappe import _
from frappe.utils import getdate


def advance_working_days(start, amount, calendar_from, calendar_to, holidays):
    from dinext_common.workflow_approval.deadlines.policy import positive_amount, resolve_local
    remaining = positive_amount(amount, integer=True)
    if not calendar_from <= start.date() <= calendar_to:
        raise ValueError(_("Worker calendar does not cover the deadline start"))
    result = start
    while remaining:
        result += timedelta(days=1)
        if result.date() > calendar_to:
            raise ValueError(_("Worker calendar does not cover the deadline"))
        if result.date() not in holidays:
            remaining -= 1
    return resolve_local(result).astimezone(start.tzinfo)


def manager_on_date(rows, fallback, on_date):
    applicable = [row for row in rows if row.get("date") and getdate(row["date"]) <= on_date]
    latest = max(applicable, key=lambda row:(getdate(row["date"]), int(row.get("idx") or 0)), default=None)
    return latest.get("teamlead") if latest else fallback


def _worker(user):
    name = frappe.db.get_value("Worker", {"wuser":user}, "name")
    if not name:
        raise ValueError(_("Worker is missing for user {0}").format(user))
    return frappe.get_doc("Worker", name)


def working_days(context):
    worker = _worker(context["approver"])
    if not worker.wholiday_list:
        raise ValueError(_("Worker holiday calendar is missing"))
    calendar = frappe.get_doc("Holiday List", worker.wholiday_list)
    return advance_working_days(context["start"],context["amount"],getdate(calendar.from_date),
        getdate(calendar.to_date),{getdate(row.holiday_date) for row in calendar.holidays})


def group_manager(context):
    worker = _worker(context["approver"])
    if not worker.wuser_group:
        return []
    group = frappe.get_doc("User Group",worker.wuser_group)
    manager = manager_on_date([row.as_dict() for row in group.get("custom_table") or []],
        group.get("custom_teamlead"),getdate(context["on_date"]))
    return [manager] if manager else []


def working_day_slot(context):
    """Latest scheduled slot on the recipient's working-date cadence."""
    from dinext_common.workflow_approval.deadlines.policy import positive_amount
    from dinext_common.workflow_approval.notifications import _daily_slot_utc, get_timezone
    worker = _worker(context["recipient"])
    if not worker.wholiday_list:
        raise ValueError(_("Worker holiday calendar is missing"))
    calendar = frappe.get_doc("Holiday List",worker.wholiday_list)
    zone = get_timezone(context["timezone_name"])
    anchor = context["anchor"].astimezone(zone)
    now = context["now"].astimezone(zone)
    first,last=getdate(calendar.from_date),getdate(calendar.to_date)
    if not first <= anchor.date() <= now.date() <= last:
        raise ValueError(_("Worker calendar does not cover the notification schedule"))
    holidays={getdate(row.holiday_date) for row in calendar.holidays}
    interval=positive_amount(context["interval"],integer=True)
    day=anchor.date();index=0;latest=None
    while day <= now.date():
        if day not in holidays:
            if index % interval == 0:
                for at in context["send_times"]:
                    slot=_daily_slot_utc(day,at,zone)
                    if max(context["created_at"],context["anchor"]) <= slot <= context["now"]:
                        latest=max(latest,slot) if latest else slot
            index+=1
        day+=timedelta(days=1)
    return latest


def get_extensions(doctype):
    supported = {"Project", "Task", "Application for Leave", "User Timesheet", "User Timesheet Position",
        "Goal", "Project Stage", "Project Gate Checkpoint", "Project Scorecard"}
    if doctype not in supported or not frappe.db.exists("DocType","Worker"):
        return {}
    return {
        "deadline_intervals":{"Working Days":{"label":"Working Days", "integer":True,"calculate":working_days}},
        "sending_intervals":{"Working Days":{"label":"Working Days", "integer":True,"latest_slot":working_day_slot}},
        "recipients":{"Worker Group Manager":{"label":"Worker Group Manager","resolve":group_manager}},
    }
