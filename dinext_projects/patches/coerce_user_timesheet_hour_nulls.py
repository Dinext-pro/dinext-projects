import frappe


HOUR_FIELDS = (
	"total_hours_worked",
	"total_hours_schedule",
	"total_hours_to_work",
	"total_hours_utilized",
	"total_hours_leave",
	"total_hours_util_leave",
)


def execute():
	"""Coerce NULL/empty hour columns before Float schema sync.

	Legacy sites may still store these as varchar with NULL values.
	MariaDB then fails ALTER ... decimal NOT NULL with Data truncated.
	"""
	if not frappe.db.table_exists("User Timesheet"):
		return

	table_columns = set(frappe.db.get_table_columns("User Timesheet") or [])
	fields = [field for field in HOUR_FIELDS if field in table_columns]
	if not fields:
		return

	set_clause = ", ".join(
		f"`{field}` = IFNULL(NULLIF(`{field}`, ''), '0')" for field in fields
	)
	where_clause = " OR ".join(
		f"`{field}` IS NULL OR `{field}` = ''" for field in fields
	)

	frappe.db.sql(
		f"UPDATE `tabUser Timesheet` SET {set_clause} WHERE {where_clause}"
	)
