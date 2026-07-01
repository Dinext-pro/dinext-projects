# Copyright (c) 2026, Dinext
"""Регрессия Server Script Work Efforts + dual-mode (SS vs Python) после миграции ISS-2025-01239."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import frappe
from frappe.tests.utils import FrappeTestCase

from .data_setup import (
	DEPENDENCY_PROJECT,
	DEPENDENCY_VIEW_OPTIONS,
	TC03_FORECAST_PLAN,
	prepare_case_save_forecast_as_plan,
	reset_owned_data,
	get_plan_hours,
	dependency_project_available,
)

from dinext_projects.dinext_projects.work_efforts.consolidated_data import (
	run_get_work_efforts_consolidated_data,
)
from dinext_projects.dinext_projects.work_efforts.timesheet_limits import (
	run_calculate_timesheet_limits,
)
from dinext_projects.dinext_projects.work_efforts.save_forecast_as_plan import (
	run_save_forecast_as_plan,
)


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

VOLATILE_ROLE_PREFIXES = ("fact_utps_",)
ROUND_DIGITS = 2


def call_python_api(func_name: str, **params: Any) -> Any:
	"""Вызывает Python-функцию из work_efforts модуля напрямую, без HTTP-слоя."""
	prev_fd = getattr(frappe.local, "form_dict", None)
	frappe.local.form_dict = frappe._dict(params)
	try:
		if func_name == "get_work_efforts_consolidated_data":
			return run_get_work_efforts_consolidated_data(frappe.form_dict)
		elif func_name == "calculate_timesheet_limits":
			return run_calculate_timesheet_limits(frappe.form_dict)
		elif func_name == "save_forecast_as_plan":
			return run_save_forecast_as_plan(frappe.form_dict)
		raise ValueError(f"Unknown func_name: {func_name}")
	finally:
		frappe.local.form_dict = prev_fd


def call_server_script_api(api_method: str, **params: Any):
	"""Эквивалент Desk `frappe.call({method, args})` для Server Script API."""
	from frappe.handler import execute_cmd

	prev_fd = getattr(frappe.local, "form_dict", None)
	frappe.local.form_dict = frappe._dict(params)
	try:
		result = execute_cmd(api_method)
		if result is not None:
			return result
		return frappe.response.get("message")
	finally:
		frappe.local.form_dict = prev_fd


def _round_num(value: Any) -> Any:
	if isinstance(value, bool) or value is None:
		return value
	if isinstance(value, int):
		return value
	if isinstance(value, float):
		return round(value, ROUND_DIGITS)
	if isinstance(value, str):
		try:
			return round(float(value.replace(",", ".")), ROUND_DIGITS)
		except ValueError:
			return value
	return value


def _normalize_role_entry(entry: dict) -> dict:
	out: dict[str, Any] = {}
	for key in sorted(entry.keys()):
		if any(key.startswith(prefix) for prefix in VOLATILE_ROLE_PREFIXES):
			continue
		val = entry[key]
		if key.startswith(("plan_", "forecast_", "fact_")):
			out[key] = _round_num(val)
		else:
			out[key] = val
	return out


def _normalize_task_row(row: dict) -> dict:
	role_data = [_normalize_role_entry(r) for r in row.get("role_data") or []]
	role_data.sort(key=lambda r: (r.get("role") or "", json.dumps(r, sort_keys=True)))
	return {
		"value": row.get("value"),
		"subject": row.get("subject"),
		"indent": int(row.get("indent") or 0),
		"expandable": int(row.get("expandable") or 0),
		"parent_task": row.get("parent_task"),
		"type": row.get("type"),
		"status": row.get("status"),
		"role_data": role_data,
	}


def normalize_consolidated_golden(raw: list | None, *, project: str, view_options: str) -> dict:
	tasks = [_normalize_task_row(row) for row in raw or []]
	tasks.sort(key=lambda r: (r.get("indent", 0), r.get("value") or ""))
	return {
		"project": project,
		"view_options": view_options,
		"task_count": len(tasks),
		"tasks": tasks,
	}


def normalize_limits_golden(raw: list | None) -> list[dict]:
	results: list[dict] = []
	for row in raw or []:
		hours_data = row.get("hours_data") or {}
		norm_hours = {k: _round_num(v) for k, v in sorted(hours_data.items()) if k != "users"}
		item = {
			"project": row.get("project"),
			"position": row.get("position"),
			"document_name": row.get("document_name"),
			"role": row.get("role"),
			"planned_hours": _round_num(row.get("planned_hours")),
			"total_hours": _round_num(row.get("total_hours")),
			"completion_percentage": int(row.get("completion_percentage") or 0),
			"status": row.get("status"),
			"limit": _round_num(row.get("limit")),
			"used_parent_for_plan": bool(row.get("used_parent_for_plan")),
			"used_children_for_actual": bool(row.get("used_children_for_actual")),
			"child_tasks_count": int(row.get("child_tasks_count") or 0),
			"plan_required": bool(row.get("plan_required")),
			"hours_data": norm_hours,
		}
		results.append(item)
	results.sort(key=lambda r: (r.get("document_name") or "", r.get("role") or ""))
	return results


class TestWEServerScriptMigrationBaseline(FrappeTestCase):
	def tearDown(self):
		reset_owned_data()
		super().tearDown()

	def test_tc01_get_work_efforts_consolidated_data_golden(self):
		"""TC-01: get_work_efforts_consolidated_data — нормализованный ответ vs golden fixture."""
		if not dependency_project_available():
			self.skipTest(f"Dependency project {DEPENDENCY_PROJECT} отсутствует на сайте")

		fixture_path = FIXTURES_DIR / "tc01_consolidated_golden.json"
		if not fixture_path.exists():
			self.skipTest(f"Golden fixture missing: {fixture_path.name} — запустите capture_golden.py")

		with open(fixture_path, encoding="utf-8") as f:
			golden = json.load(f)
		golden.pop("_comment", None)

		frappe.set_user("Administrator")
		raw = call_server_script_api(
			"get_work_efforts_consolidated_data",
			project=DEPENDENCY_PROJECT,
			view_options=DEPENDENCY_VIEW_OPTIONS,
		)
		actual = normalize_consolidated_golden(
			raw,
			project=DEPENDENCY_PROJECT,
			view_options=DEPENDENCY_VIEW_OPTIONS,
		)

		self.assertEqual(actual["project"], golden["project"])
		self.assertEqual(actual["view_options"], golden["view_options"])
		self.assertEqual(actual["task_count"], golden["task_count"])
		self.assertEqual(actual["tasks"], golden["tasks"])

	def test_tc02_calculate_timesheet_limits_golden(self):
		"""TC-02: calculate_timesheet_limits — минимальный positions payload vs golden."""
		fixture_path = FIXTURES_DIR / "tc02_limits_golden.json"
		if not fixture_path.exists():
			self.skipTest(f"Golden fixture missing: {fixture_path.name} — запустите capture_golden.py")

		with open(fixture_path, encoding="utf-8") as f:
			golden = json.load(f)
		golden.pop("_comment", None)

		frappe.set_user("Administrator")
		raw = call_server_script_api(
			"calculate_timesheet_limits",
			positions=json.dumps(golden["positions_payload"]),
			timesheet_name=golden.get("timesheet_name") or "",
		)
		actual = normalize_limits_golden(raw)
		self.assertEqual(actual, golden["results"])

	def test_tc03_save_forecast_as_plan_updates_owned_pwe(self):
		"""TC-03: save_forecast_as_plan — запись plan в owned PWE из forecast."""
		if not frappe.db.exists("DocType", "Project Work Efforts"):
			self.skipTest("DocType Project Work Efforts не установлен")

		ctx = prepare_case_save_forecast_as_plan()
		project = str(ctx["project"])
		task = str(ctx["task"])
		pwe = str(ctx["pwe"])
		fy = str(ctx["fiscal_year"])
		year = int(ctx["year"])
		month = int(ctx["month"])
		role = str(ctx["role"])

		self.assertEqual(get_plan_hours(pwe, fy, month), float(ctx["initial_plan"]))

		payload = [
			{
				"task": task,
				"role": role,
				"year": year,
				"month": month,
				"plan_value": TC03_FORECAST_PLAN,
			}
		]
		frappe.set_user("Administrator")
		call_server_script_api(
			"save_forecast_as_plan",
			project=project,
			data=json.dumps(payload),
		)

		updated = get_plan_hours(pwe, fy, month)
		self.assertAlmostEqual(updated, TC03_FORECAST_PLAN, places=ROUND_DIGITS)


	def test_tc01_python_path_consolidated_data(self):
		"""TC-01 Python: get_work_efforts_consolidated_data — Python-путь vs golden fixture."""
		if not dependency_project_available():
			self.skipTest(f"Dependency project {DEPENDENCY_PROJECT} отсутствует на сайте")

		fixture_path = FIXTURES_DIR / "tc01_consolidated_golden.json"
		if not fixture_path.exists():
			self.skipTest(f"Golden fixture missing: {fixture_path.name}")

		with open(fixture_path, encoding="utf-8") as f:
			golden = json.load(f)
		golden.pop("_comment", None)

		frappe.set_user("Administrator")
		raw = call_python_api(
			"get_work_efforts_consolidated_data",
			project=DEPENDENCY_PROJECT,
			view_options=DEPENDENCY_VIEW_OPTIONS,
		)
		actual = normalize_consolidated_golden(
			raw,
			project=DEPENDENCY_PROJECT,
			view_options=DEPENDENCY_VIEW_OPTIONS,
		)

		self.assertEqual(actual["project"], golden["project"])
		self.assertEqual(actual["view_options"], golden["view_options"])
		self.assertEqual(actual["task_count"], golden["task_count"])
		self.assertEqual(actual["tasks"], golden["tasks"])

	def test_tc01_dual_mode_consolidated_data(self):
		"""TC-01 dual-mode: Python-путь vs SS-путь дают одинаковый нормализованный вывод."""
		if not dependency_project_available():
			self.skipTest(f"Dependency project {DEPENDENCY_PROJECT} отсутствует на сайте")

		frappe.set_user("Administrator")
		kwargs = dict(project=DEPENDENCY_PROJECT, view_options=DEPENDENCY_VIEW_OPTIONS)

		raw_ss = call_server_script_api("get_work_efforts_consolidated_data", **kwargs)
		raw_py = call_python_api("get_work_efforts_consolidated_data", **kwargs)

		norm_ss = normalize_consolidated_golden(raw_ss, project=DEPENDENCY_PROJECT, view_options=DEPENDENCY_VIEW_OPTIONS)
		norm_py = normalize_consolidated_golden(raw_py, project=DEPENDENCY_PROJECT, view_options=DEPENDENCY_VIEW_OPTIONS)

		self.assertEqual(norm_py["task_count"], norm_ss["task_count"])
		self.assertEqual(norm_py["tasks"], norm_ss["tasks"])

	def test_tc02_python_path_timesheet_limits(self):
		"""TC-02 Python: calculate_timesheet_limits — Python-путь vs golden fixture."""
		fixture_path = FIXTURES_DIR / "tc02_limits_golden.json"
		if not fixture_path.exists():
			self.skipTest(f"Golden fixture missing: {fixture_path.name}")

		with open(fixture_path, encoding="utf-8") as f:
			golden = json.load(f)
		golden.pop("_comment", None)

		frappe.set_user("Administrator")
		raw = call_python_api(
			"calculate_timesheet_limits",
			positions=json.dumps(golden["positions_payload"]),
			timesheet_name=golden.get("timesheet_name") or "",
		)
		actual = normalize_limits_golden(raw)
		self.assertEqual(actual, golden["results"])

	def test_tc02_dual_mode_timesheet_limits(self):
		"""TC-02 dual-mode: Python-путь vs SS-путь дают одинаковый нормализованный вывод."""
		fixture_path = FIXTURES_DIR / "tc02_limits_golden.json"
		if not fixture_path.exists():
			self.skipTest(f"Golden fixture missing: {fixture_path.name}")

		with open(fixture_path, encoding="utf-8") as f:
			golden = json.load(f)
		golden.pop("_comment", None)

		frappe.set_user("Administrator")
		kwargs = dict(
			positions=json.dumps(golden["positions_payload"]),
			timesheet_name=golden.get("timesheet_name") or "",
		)

		raw_ss = call_server_script_api("calculate_timesheet_limits", **kwargs)
		raw_py = call_python_api("calculate_timesheet_limits", **kwargs)

		norm_ss = normalize_limits_golden(raw_ss)
		norm_py = normalize_limits_golden(raw_py)

		self.assertEqual(norm_py, norm_ss)

	def test_tc03_python_path_save_forecast_as_plan(self):
		"""TC-03 Python: save_forecast_as_plan — Python-путь записывает pwea_plan."""
		if not frappe.db.exists("DocType", "Project Work Efforts"):
			self.skipTest("DocType Project Work Efforts не установлен")

		ctx = prepare_case_save_forecast_as_plan()
		project = str(ctx["project"])
		task = str(ctx["task"])
		pwe = str(ctx["pwe"])
		fy = str(ctx["fiscal_year"])
		year = int(ctx["year"])
		month = int(ctx["month"])
		role = str(ctx["role"])

		self.assertEqual(get_plan_hours(pwe, fy, month), float(ctx["initial_plan"]))

		payload = [
			{
				"task": task,
				"role": role,
				"year": year,
				"month": month,
				"plan_value": TC03_FORECAST_PLAN,
			}
		]
		frappe.set_user("Administrator")
		call_python_api(
			"save_forecast_as_plan",
			project=project,
			data=json.dumps(payload),
		)

		updated = get_plan_hours(pwe, fy, month)
		self.assertAlmostEqual(updated, TC03_FORECAST_PLAN, places=ROUND_DIGITS)


def reset():
	reset_owned_data()
