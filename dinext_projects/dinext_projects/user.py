import frappe

@frappe.whitelist()
def get_users_with_role(role: str) -> list[str]:

    if not frappe.db.exists("Role", role):
        return []

    query = """
        SELECT DISTINCT user.name
        FROM `tabHas Role` hr
        INNER JOIN `tabUser` user ON hr.parent = user.name
        WHERE hr.role = %(role)s
          AND user.name != 'Administrator'
          AND user.enabled = 1
    """
    result = frappe.db.sql(query, {"role": role}, as_dict=False)

    return [row[0] for row in result]
