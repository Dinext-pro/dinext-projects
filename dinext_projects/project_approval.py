from __future__ import annotations

import frappe
from frappe.model.document import Document

PROJECT_WORKFLOW = "Project Approval"
PROJECT_DRAFT_STATE = "Черновик"


def sync_draft_activation(doc: Document, method: str | None = None) -> None:
	"""Apply the draft state value after Frappe restores protected form fields."""
	if doc.get("workflow_state") != PROJECT_DRAFT_STATE or doc.get("is_active") != "Yes":
		return

	from dinext_common.workflow_approval.scenarios import service

	if service.is_ready():
		context = service.workflow_context(doc)
		if not context or context[0] != PROJECT_WORKFLOW:
			return
		workflow = context[1]
	else:
		from frappe.model.workflow import get_workflow_name

		if get_workflow_name(doc.doctype) != PROJECT_WORKFLOW:
			return
		workflow = frappe.get_cached_doc("Workflow", PROJECT_WORKFLOW)

	draft = next((row for row in workflow.states if row.state == PROJECT_DRAFT_STATE), None)
	if draft and draft.update_field == "is_active" and draft.update_value == "No":
		doc.is_active = draft.update_value
