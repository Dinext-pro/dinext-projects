# Copyright (c) 2026, Dinext
"""Детерминированные данные для регрессии Server Script Work Efforts (migration baseline)."""

from __future__ import annotations

import frappe

PREFIX = "WE-SS-MIG-BASE"
ROLE_NAME = f"{PREFIX} Role"
BUSINESS_USER = "Administrator"
TASK_TYPE = "Stage"

# Read-only dependency: реальный проект с PWE на dev-site (не owned data).
DEPENDENCY_PROJECT = "TEST-V15.106.0 (HEAD)"
DEPENDENCY_VIEW_OPTIONS = "Прогноз и факт"

# Owned TC-03: фиксированный период и значения plan/forecast.
TC03_FISCAL_YEAR = 2026
TC03_MONTH = 8
TC03_INITIAL_PLAN = 12.0
TC03_FORECAST_PLAN = 48.5


def owned_entities() -> dict[str, list[str]]:
	return {
		"Project": [f"project_name like {PREFIX}%"],
		"Task": [f"subject like {PREFIX}%"],
		"Project Work Efforts": ["pwe_task in owned tasks"],
		"Project Role": [ROLE_NAME],
	}


def _default_company() -> str | None:
	row = frappe.db.sql("select name from `tabCompany` limit 1", as_dict=True)
	return row[0].name if row else None


def _default_project_type_name() -> str | None:
	for cand in ("Внутренний", "Internal", "Коммерческий", "External"):
		if frappe.db.exists("Project Type", cand):
			return cand
	row = frappe.db.sql("select name from `tabProject Type` limit 1", as_dict=True)
	return row[0].name if row else None


def _default_project_payment_scheme_name() -> str | None:
	for cand in ("Неоплачиваемый", "Время и затраты (T&M)", "Фикс. стоимость"):
		if frappe.db.exists("Project Payment Scheme", cand):
			return cand
	row = frappe.db.sql("select name from `tabProject Payment Scheme` limit 1", as_dict=True)
	return row[0].name if row else None


def _pick_fiscal_year(year: int) -> str | None:
	rows = frappe.db.sql(
		"""
		select name from `tabFiscal Year`
		where year_start_date <= %(end)s and year_end_date >= %(start)s
		limit 1
		""",
		{"start": f"{year}-01-01", "end": f"{year}-12-31"},
	)
	if not rows:
		return None
	return rows[0][0]


def reset_owned_data() -> None:
	task_names = frappe.get_all(
		"Task",
		filters={"subject": ["like", f"{PREFIX}%"]},
		pluck="name",
		order_by="lft desc",
		ignore_permissions=True,
	)
	if task_names:
		for pwe in frappe.get_all(
			"Project Work Efforts",
			filters={"pwe_task": ["in", task_names]},
			pluck="name",
			ignore_permissions=True,
		):
			frappe.delete_doc("Project Work Efforts", pwe, force=True, ignore_permissions=True)

	for task_name in task_names:
		frappe.delete_doc("Task", task_name, force=True, ignore_permissions=True)

	for proj in frappe.get_all(
		"Project",
		filters={"project_name": ["like", f"{PREFIX}%"]},
		pluck="name",
		ignore_permissions=True,
	):
		frappe.delete_doc("Project", proj, force=True, ignore_permissions=True)

	if frappe.db.exists("Project Role", ROLE_NAME):
		frappe.delete_doc("Project Role", ROLE_NAME, force=True, ignore_permissions=True)


def ensure_project_role() -> str:
	if not frappe.db.exists("Project Role", ROLE_NAME):
		frappe.get_doc(
			{
				"doctype": "Project Role",
				"role_name": ROLE_NAME,
				"enabled": 1,
			}
		).insert(ignore_permissions=True)
	return ROLE_NAME


def prepare_case_save_forecast_as_plan() -> dict[str, str | float | int]:
	"""Owned Project/Task/PWE для TC-03: save_forecast_as_plan меняет pwea_plan."""
	reset_owned_data()
	if not frappe.db.exists("DocType", "Project Work Efforts"):
		frappe.throw("DocType Project Work Efforts не установлен")

	company = _default_company()
	if not company:
		frappe.throw("Нет Company в базе")
	pt = _default_project_type_name()
	pps = _default_project_payment_scheme_name()
	if not pt or not pps:
		frappe.throw("Нет Project Type или Project Payment Scheme")

	fy = _pick_fiscal_year(TC03_FISCAL_YEAR)
	if not fy:
		frappe.throw(f"Нет Fiscal Year на {TC03_FISCAL_YEAR}")

	ensure_project_role()
	project = frappe.get_doc(
		{
			"doctype": "Project",
			"name": f"{PREFIX}-PRJ",
			"project_name": f"{PREFIX} Project",
			"project_type": pt,
			"custom_payment_scheme": pps,
			"company": company,
			"status": "Open",
		}
	).insert(ignore_permissions=True)

	task = frappe.get_doc(
		{
			"doctype": "Task",
			"subject": f"{PREFIX} Forecast Task",
			"status": "Open",
			"type": TASK_TYPE,
			"project": project.name,
			"is_group": 0,
		}
	).insert(ignore_permissions=True)

	pwe = frappe.get_doc(
		{
			"doctype": "Project Work Efforts",
			"pwe_project": project.name,
			"pwe_task": task.name,
			"pwe_project_role": ROLE_NAME,
			"pwe_amount": [
				{
					"pwea_year": fy,
					"pwea_month": TC03_MONTH,
					"pwea_plan": TC03_INITIAL_PLAN,
					"pwea_expected": TC03_FORECAST_PLAN,
				}
			],
		}
	).insert(ignore_permissions=True)

	return {
		"company": company,
		"project": project.name,
		"task": task.name,
		"pwe": pwe.name,
		"fiscal_year": fy,
		"year": TC03_FISCAL_YEAR,
		"month": TC03_MONTH,
		"initial_plan": TC03_INITIAL_PLAN,
		"forecast_plan": TC03_FORECAST_PLAN,
		"role": ROLE_NAME,
	}


def get_plan_hours(pwe_name: str, fiscal_year: str, month: int) -> float:
	doc = frappe.get_doc("Project Work Efforts", pwe_name)
	for row in doc.pwe_amount:
		if str(row.pwea_year) == str(fiscal_year) and int(row.pwea_month) == int(month):
			return float(row.pwea_plan or 0)
	return 0.0


def dependency_project_available() -> bool:
	return bool(frappe.db.exists("Project", DEPENDENCY_PROJECT))


def reset():
	reset_owned_data()
