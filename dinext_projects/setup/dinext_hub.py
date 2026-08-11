# Copyright (c) 2026, Dinext and contributors
# For license information, please see license.txt

"""Register this app's default Dinext Hub cards."""

from __future__ import annotations

import frappe

APP_NAME = 'dinext_projects'

HUB_ITEMS = (
	{
		"section": 'My Work',
		"element_type": 'Workspace',
		"target": 'Мои задачи',
		"label": 'My Tasks',
		"description": 'Personal dashboard for your Issues and Tasks: assigned, overdue, and paused items, milestone quick lists, and shortcuts to create new requests.',
		"icon": 'assign',
	},
	{
		"section": 'Project Management',
		"element_type": 'Workspace',
		"target": 'Мои проекты',
		"label": 'My Projects',
		"description": 'Portfolio overview, project directories, status breakdowns, workload and budget reports, and cost-center allocation links.',
		"icon": 'project',
	},
	{
		"section": 'Project Management',
		"element_type": 'DocType',
		"target": 'Project Portfolio',
		"label": 'Project Portfolio',
		"description": 'Groups related projects into portfolios for portfolio-level tracking and scoring.',
		"icon": 'organization',
	},
)


def register_dinext_hub_items() -> None:
	if "dinext_common" not in frappe.get_installed_apps():
		return

	try:
		from dinext_common.setup.hub_catalog import register_hub_items
	except ImportError:
		return

	register_hub_items(HUB_ITEMS, source_app=APP_NAME)
