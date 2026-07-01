// we-table.js — entry point for Work Efforts table module
// ISS-2025-01239
//
// Load order (via hooks.py doctype_js):
//   we-namespace.js       → frappe.provide("dinext_projects.work_efforts")
//   we-calc.js            → makeAggregator, calc_we_column_total_optimized, clearTaskIndexCacheFor
//   we-checks.js          → load_all_assignments_if_needed, buildWorkloadPeriodsMap, hasWorkloadInPeriod,
//                            isPeriodInTaskDates, get_task_assignments, clear_assignments_cache,
//                            check_plan_load_for_percentage_assignments, perform_overload_check
//   we-styles.js          → applyWorkEffortsStyles
//   we-chart.js           → render_work_efforts_chart
//   we-table/controls.js  → get_project_roles, get_display_periods, addViewOptionsControl, render_legend
//   we-table/data-load.js → load_work_efforts_data, rollup_fact_data
//   we-table/columns.js   → get_columns_definition
//   we-table/cell-edit.js → updateForecastValue, save_forecast_as_plan
//   we-table/limits.js    → recalculatePeriodLimits, setCellStyles
//   we-table/render.js    → render_work_efforts_table, updateTable, frappe.ui.form.on("Project")
//   we-table.js           ← this file

dinext_projects.work_efforts.ready = true;
