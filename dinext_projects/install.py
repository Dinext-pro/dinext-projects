# Copyright (c) Dinext. License: GNU GPL v3. See license.txt

"""App install hooks.

Runs before sync_fixtures for this app (see frappe.installer.install_app): standard ERPNext
rows are removed here; the next step may re-import the same names from dinext_projects/fixtures/.
"""

import frappe
from frappe import _

# ERPNext install_fixtures.py (setup wizard)
_STANDARD_PROJECT_TYPES = ("Internal", "External", "Other")
_STANDARD_ISSUE_PRIORITY_MSGIDS = ("Low", "Medium", "High")


def after_install():
	clear_standard_project_type_and_issue_priority()
	from dinext_projects.setup.dinext_hub import register_dinext_hub_items

	register_dinext_hub_items()


def after_migrate():
	from dinext_projects.setup.dinext_hub import register_dinext_hub_items

	register_dinext_hub_items()


def clear_standard_project_type_and_issue_priority():
	# ERPNext ProjectType.on_trash blocks "External"; skip trash hooks during cleanup.
	for name in _STANDARD_PROJECT_TYPES:
		frappe.delete_doc(
			"Project Type",
			name,
			force=True,
			ignore_permissions=True,
			ignore_missing=True,
			ignore_on_trash=True,
		)

	for name in _issue_priority_erpnext_names():
		frappe.delete_doc(
			"Issue Priority",
			name,
			force=True,
			ignore_permissions=True,
			ignore_missing=True,
			ignore_on_trash=True,
		)


def _issue_priority_erpnext_names():
	"""Names created by ERPNext from _('Low'|'Medium'|'High') depend on active language."""
	names = set(_STANDARD_ISSUE_PRIORITY_MSGIDS)
	prev_lang = getattr(frappe.local, "lang", None) or "en"
	try:
		langs = set(frappe.get_all("Language", pluck="name") or [])
		langs.add("en")
		for lang in langs:
			frappe.local.lang = lang
			for msgid in _STANDARD_ISSUE_PRIORITY_MSGIDS:
				names.add(_(msgid))
	finally:
		frappe.local.lang = prev_lang
	return names
