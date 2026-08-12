# Copyright (c) 2026, Dinext and contributors
# For license information, please see license.txt

"""Register this app's default Dinext Hub cards and DocType lists."""

from __future__ import annotations

import frappe

APP_NAME = "dinext_projects"

HUB_ITEMS = (
	{
		"section": "My Work",
		"element_type": "Workspace",
		"target": "Мои задачи",
		"label": "My Tasks",
		"description": (
			"Personal dashboard for your Issues and Tasks: assigned, overdue, and paused items, "
			"milestone quick lists, and shortcuts to create new requests."
		),
		"icon": "assign",
	},
	{
		"section": "Project Management",
		"element_type": "Workspace",
		"target": "Мои проекты",
		"label": "My Projects",
		"description": (
			"Portfolio overview, project directories, status breakdowns, workload and budget reports, "
			"and cost-center allocation links."
		),
		"icon": "project",
	},
	{
		"section": "Project Management",
		"element_type": "DocType",
		"target": "Project Portfolio",
		"label": "Project Portfolio",
		"description": "Groups related projects into portfolios for portfolio-level tracking and scoring.",
		"icon": "organization",
	},
)

HUB_SECTIONS = (
	{"section": "My Work", "list_limit": 5},
	{"section": "Project Management", "list_limit": 8},
)

HUB_DOCTYPE_ITEMS = (
	{
		"section": "My Work",
		"document_type": "Issue",
		"show_quick_create": 1,
		"show_recently_opened": 1,
		"show_assigned": 1,
		"show_liked": 1,
		"show_attention": 1,
		"attention_filter": [
			["Issue", "status", "in", ["Open", "Replied", "On Hold"], False],
			["Issue", "custom_is_overdue", "=", 1, False],
		],
	},
	{
		"section": "My Work",
		"document_type": "Task",
		"show_quick_create": 1,
		"show_recently_opened": 1,
		"show_assigned": 1,
		"show_liked": 1,
		"show_attention": 1,
		"attention_filter": [
			["Task", "status", "=", "Overdue", False],
			["Task", "type", "!=", "Issue", False],
		],
	},
	{
		"section": "Project Management",
		"document_type": "Project",
		"show_quick_create": 0,
		"show_recently_opened": 1,
		"show_assigned": 0,
		"show_liked": 0,
		"show_attention": 1,
		"attention_filter": [["Project", "workflow_state", "=", "На согласовании", False]],
	},
	{
		"section": "Project Management",
		"document_type": "Project Portfolio",
		"show_quick_create": 1,
		"show_recently_opened": 1,
		"show_assigned": 0,
		"show_liked": 0,
		"show_attention": 0,
		"attention_filter": [],
	},
)


def register_dinext_hub_items() -> None:
	if "dinext_common" not in frappe.get_installed_apps():
		return

	try:
		from dinext_common.setup.hub_catalog import (
			register_hub_doctype_items,
			register_hub_items,
			register_hub_sections,
		)
	except ImportError:
		return

	register_hub_items(HUB_ITEMS, source_app=APP_NAME)
	register_hub_sections(HUB_SECTIONS, source_app=APP_NAME)
	register_hub_doctype_items(HUB_DOCTYPE_ITEMS, source_app=APP_NAME)
