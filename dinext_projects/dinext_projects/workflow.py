from contextlib import contextmanager
import frappe
from frappe import local
from dinext_projects.dinext_projects.permissions import set_user_light

@frappe.whitelist()
def get_transitions(
	doc, user = None, workflow = None, raise_exception: bool = False
) -> list[dict]:
    from frappe.model.workflow import get_transitions as og_get_transitions
    cur_user = frappe.session.user

    if not user or user == frappe.session.user:
        return og_get_transitions(
            doc=doc,
            workflow = workflow,
            raise_exception=raise_exception
        )
    else:
        with set_user_light(user):
            return og_get_transitions(
                doc=doc,
                workflow=workflow,
                raise_exception=raise_exception
            )
