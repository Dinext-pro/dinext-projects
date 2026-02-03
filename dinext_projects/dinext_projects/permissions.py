import logging
import os

def get_custom_logger(name="dinext_projects", log_file="has_permission.log", log_dir="/home/frappe/frappe-bench/logs", level=logging.INFO):
    os.makedirs(log_dir, exist_ok=True)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.hasHandlers():
        file_handler = logging.FileHandler(os.path.join(log_dir, log_file))
        file_handler.setLevel(level)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

    return logger



from contextlib import contextmanager
import frappe
from frappe import local

logger = get_custom_logger()
logger.info("dinext_projects.permissions loaded successfully")

@contextmanager
def set_user_light(user):
    original_state = {
        'user': local.session.user,
        'sid': local.session.sid,
        'cache': local.cache,
        'form_dict': local.form_dict,
        'jenv': local.jenv,
        'session_data': local.session.data,
        'role_permissions': local.role_permissions,
        'new_doc_templates': local.new_doc_templates,
        'user_perms': local.user_perms,
    }

    try:
        # аналогично frappe.set_user()
        local.session.user = user
        local.session.sid = user
        local.cache = {}
        local.form_dict = frappe._dict()
        local.jenv = None
        local.session.data = frappe._dict()
        local.role_permissions = {}
        local.new_doc_templates = {}
        local.user_perms = None

        yield

    finally:
        for key, value in original_state.items():
            setattr(local.session, key, value) if key in ['user', 'sid', 'data'] else setattr(local, key, value)

'''@frappe.whitelist()
def has_permission(
    doctype,
    ptype="read",
    doc=None,
    user=None,
    raise_exception=True,
    *,
    parent_doctype=None,
    debug=False,
) -> bool:
    #logger.info(
    #    f"has_permission called with arguments: doctype={doctype}, ptype={ptype}, doc={doc}, user={user}, raise_exception={raise_exception}, parent_doctype={parent_doctype}, debug={debug}")
    from frappe.permissions import has_permission as og_has_permission
    cur_user = frappe.session.user

    default_user = cur_user
    default_sid = cur_user
    default_cache = {}
    default_form_dict = _dict()
    default_jenv = None
    default_session_data = _dict()
    default_role_permissions = {}
    default_new_doc_templates = {}
    default_user_perms = None

    ls = local.session

    if user:

        default_user = ls.user
        default_sid = ls.sid
        default_cache = local.cache
        default_form_dict = local.form_dict
        default_jenv = local.jenv
        default_session_data = ls.data
        default_role_permissions = local.role_permissions
        default_new_doc_templates = local.new_doc_templates
        default_user_perms = local.user_perms
        frappe.set_user(user)
        logger.info(f"user set to: '{user}'")

    res = og_has_permission(doctype=doctype,
                            ptype=ptype,
                            doc=doc,
                            user=user,
                            raise_exception=raise_exception,
                            parent_doctype=parent_doctype,
                            debug=debug)
    #logger.info(f"Does user have {ptype} permission for {doc}? {res}")

    if user:
        frappe.set_user(cur_user)
        ls.user = local.session.user
        ls.sid = default_sid
        local.cache = default_cache
        local.form_dict = default_form_dict
        local.jenv = default_jenv
        ls.data = default_session_data
        local.role_permissions = default_role_permissions
        local.new_doc_templates = default_new_doc_templates
        local.user_perms = default_user_perms

        logger.info(f"user set back to: '{cur_user}'")

    return res
'''
@frappe.whitelist()
def has_permission(
    doctype,
    ptype="read",
    doc=None,
    user=None,
    raise_exception=True,
    *,
    parent_doctype=None,
    debug=False,
) -> bool:
    from frappe.permissions import has_permission as og_has_permission

    if not user or user == frappe.session.user:
        return og_has_permission(
            doctype=doctype,
            ptype=ptype,
            doc=doc,
            user=user,
            raise_exception=raise_exception,
            parent_doctype=parent_doctype,
            debug=debug
        )

    with set_user_light(user):
        return og_has_permission(
            doctype=doctype,
            ptype=ptype,
            doc=doc,
            user=user,
            raise_exception=raise_exception,
            parent_doctype=parent_doctype,
            debug=debug
        )

@frappe.whitelist()
def get_doc_permissions(doctype, doc, user=None, ptype=None, debug=False):

    #logger.info(f"get_doc_permissions called with arguments: doc={doc}, user={user}, ptype={ptype}, debug={debug}")
    meta = frappe.get_meta(doctype)
    #logger.info(f"pulled meta, got doc with get_doc('{meta.name}','{doc}'")
    doc = frappe.get_doc(meta.name, doc)

    cur_user = frappe.session.user
    if user:
        frappe.set_user(user)
        #logger.info(f"user set to: '{user}'")

    from frappe.permissions import get_doc_permissions as og_get_doc_permissions
    res = og_get_doc_permissions(doc=doc, user=user, ptype=ptype, debug=debug)
    #logger.info("Doc permissions: " + frappe.as_json(res))

    if user:
        frappe.set_user(cur_user)
        #logger.info(f"user set back to: '{cur_user}'")

    return res
#print("dinext_projects.permissions loaded successfully")