"""Dev-server fixtures for the stakeholder matrix Cypress scenario."""

from __future__ import annotations

import frappe
from frappe.tests.ui_test_helpers import whitelist_for_tests
from frappe.utils.password import update_password

PASSWORD = "Cypress-Stakeholder-2026!"
USER = "cy.stakeholder@example.com"
PROJECT_ID = "CY-STAKEHOLDER"
PROJECT_NAME = "Cypress Stakeholder Project"
CONTACT_FIRST_NAME = "Cypress Stakeholder"


def _company() -> str:
	company = frappe.db.get_value("Company", {}, "name")
	if not company:
		frappe.throw("Cypress stakeholder matrix needs a Company")
	return company


def _required_link(doctype: str) -> str:
	name = frappe.db.get_value(doctype, {}, "name")
	if not name:
		frappe.throw(f"Cypress stakeholder matrix needs a {doctype}")
	return name


def _ensure_user() -> None:
	if frappe.db.exists("User", USER):
		frappe.db.set_value("User", USER, "language", "ru")
		user = frappe.get_doc("User", USER)
	else:
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": USER,
				"first_name": "Administrator",
				"last_name": "",
				"language": "ru",
				"send_welcome_email": 0,
				"user_type": "System User",
			}
		)
		user.insert(ignore_permissions=True)
	for role in ("System Manager", "Dinext_Project_Manager", "Dinext_Projects_Admin"):
		if role not in set(frappe.get_roles(USER)):
			user.add_roles(role)
	update_password(USER, PASSWORD)


def _ensure_contact() -> str:
	existing = frappe.db.get_value("Contact", {"first_name": CONTACT_FIRST_NAME}, "name")
	if existing:
		return existing
	contact = frappe.get_doc(
		{
			"doctype": "Contact",
			"first_name": CONTACT_FIRST_NAME,
		}
	)
	contact.insert(ignore_permissions=True)
	return contact.name


def _delete_projects() -> None:
	names = set(frappe.get_all("Project", filters={"project_name": PROJECT_NAME}, pluck="name"))
	if frappe.db.exists("Project", PROJECT_ID):
		names.add(PROJECT_ID)
	for name in names:
		frappe.delete_doc("Project", name, force=True, ignore_permissions=True)


@whitelist_for_tests
def seed_stakeholder_matrix() -> dict:
	"""Create a Russian user, a contact, and a project row without scores."""
	_ensure_user()
	_delete_projects()
	contact = _ensure_contact()
	project = frappe.get_doc(
		{
			"doctype": "Project",
			"name": PROJECT_ID,
			"project_name": PROJECT_NAME,
			"company": _company(),
			"project_type": "Внутренний",
			"custom_payment_scheme": _required_link("Project Payment Scheme"),
			"custom_contact_list": [
				{
					"contact": contact,
				}
			],
		}
	)
	project.insert(ignore_permissions=True)
	frappe.db.commit()
	return {
		"user": USER,
		"password": PASSWORD,
		"project": project.name,
		"contact": contact,
	}


@whitelist_for_tests
def cleanup_stakeholder_matrix() -> dict:
	"""Delete the Cypress project, contact, and user."""
	_delete_projects()
	for name in frappe.get_all("Contact", filters={"first_name": CONTACT_FIRST_NAME}, pluck="name"):
		frappe.delete_doc("Contact", name, force=True, ignore_permissions=True)
	if frappe.db.exists("User", USER):
		frappe.delete_doc("User", USER, force=True, ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True}
