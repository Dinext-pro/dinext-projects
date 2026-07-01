# Copyright (c) 2026, Dinext
"""Whitelisted API для Work Efforts: consolidated data, timesheet limits, save forecast as plan.

ISS-2025-01239: миграция Server Scripts в Python-модули dinext_projects.

Три точки входа (whitelist → api_method Server Script → модуль ядра):
- get_work_efforts_consolidated_data → consolidated_data.run_get_work_efforts_consolidated_data
- calculate_timesheet_limits         → timesheet_limits.run_calculate_timesheet_limits
- save_forecast_as_plan              → save_forecast_as_plan.run_save_forecast_as_plan

Имена методов совпадают с api_method соответствующих Server Scripts для обратной совместимости.
"""

import frappe

from dinext_projects.dinext_projects.work_efforts.consolidated_data import (
    run_get_work_efforts_consolidated_data,
)
from dinext_projects.dinext_projects.work_efforts.timesheet_limits import (
    run_calculate_timesheet_limits,
)
from dinext_projects.dinext_projects.work_efforts.save_forecast_as_plan import (
    run_save_forecast_as_plan,
)


@frappe.whitelist()
def get_work_efforts_consolidated_data():
    """Consolidated Work Efforts data for a project. API method: get_work_efforts_consolidated_data."""
    return run_get_work_efforts_consolidated_data(frappe.form_dict)


@frappe.whitelist()
def calculate_timesheet_limits():
    """Calculate plan/fact limits for timesheet positions. API method: calculate_timesheet_limits."""
    return run_calculate_timesheet_limits(frappe.form_dict)


@frappe.whitelist()
def save_forecast_as_plan():
    """Save forecast values as plan in Project Work Efforts. API method: save_forecast_as_plan."""
    return run_save_forecast_as_plan(frappe.form_dict)
