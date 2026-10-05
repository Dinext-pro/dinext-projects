# Copyright (c) 2026, Dinext and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

SCORE_FIELDS = ("influence", "interest")


class ProjectContactList(Document):
	def validate(self):
		for fieldname in SCORE_FIELDS:
			_validate_score(self.get(fieldname), fieldname)


def _validate_score(value, fieldname):
	if value in (None, ""):
		return
	label = _(frappe.unscrub(fieldname))
	if isinstance(value, bool) or _is_fraction(value):
		_reject(label)
	try:
		number = int(value)
	except (TypeError, ValueError):
		_reject(label)
	if isinstance(value, str) and value.strip() != str(number):
		_reject(label)
	if number < 1 or number > 10:
		_reject(label)


def _is_fraction(value):
	return isinstance(value, float) and not value.is_integer()


def _reject(label):
	frappe.throw(
		_("{0} must be an integer from 1 to 10").format(label),
		title=_("Invalid Score"),
	)
