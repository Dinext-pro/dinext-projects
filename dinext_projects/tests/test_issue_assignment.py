import hashlib
import unittest
from unittest.mock import Mock, patch

import frappe


class TestIssueAssignment(unittest.TestCase):
	def setUp(self):
		from dinext_projects import issue_assignment

		self.rule = issue_assignment
		self.issue = Mock(custom_is_new=1)
		self.groups = []
		self.issue_fields = {"custom_z_user_group": self.groups, "_assign": ""}
		self.issue.get.side_effect = self.issue_fields.get
		self.issue.append.side_effect = lambda field, row: self.groups.append(frappe._dict(row))
		self.issue.remove.side_effect = self.groups.remove
		self.todo = frappe._dict(
			reference_type="Issue", reference_name="ISSUE-1", allocated_to="assignee@example.test", status="Open"
		)
		self.backend = Mock(
			get_doc=Mock(return_value=self.issue), flags=frappe._dict(in_install=False, in_migrate=False)
		)
		self.backend.get_all.return_value = []
		self.server_scripts = {}
		for substitution in (
			patch.object(issue_assignment, "frappe", self.backend),
			patch.object(issue_assignment, "get_server_script_map", return_value=self.server_scripts),
		):
			substitution.start()
			self.addCleanup(substitution.stop)

	def test_open_adds_group_once_and_saves_with_normal_permissions(self):
		self.backend.get_all.return_value = ["Ops", "Ops"]
		self.rule.sync_issue_user_groups(self.todo)
		self.rule.sync_issue_user_groups(self.todo)
		self.assertEqual(self.groups, [{"user_group": "Ops"}])
		self.assertEqual(self.issue.custom_is_new, 0)
		self.issue.save.assert_called_once_with()
		self.backend.get_all.assert_called_with(
			"User Group Member",
			filters={
				"parenttype": "User Group",
				"parentfield": "user_group_members",
				"user": ("in", ["assignee@example.test"]),
			},
			pluck="parent",
			order_by="parent asc",
		)

	def test_no_change_keeps_new_flag(self):
		self.groups.append(frappe._dict(user_group="Ops"))
		self.backend.get_all.return_value = ["Ops"]
		self.rule.sync_issue_user_groups(self.todo)
		self.assertEqual(self.issue.custom_is_new, 1)
		self.issue.save.assert_not_called()

	def test_close_leaves_group_for_another_open_assignment(self):
		self.todo.status = "Closed"
		self.groups.append(frappe._dict(user_group="Ops"))
		self.issue_fields["_assign"] = '["other@example.test"]'
		self.backend.get_all.return_value = ["Ops"]
		self.rule.sync_issue_user_groups(self.todo)
		self.assertEqual(self.groups, [{"user_group": "Ops"}])
		self.issue.save.assert_not_called()
		self.backend.db.get_values.assert_not_called()

	def test_cancel_removes_inactive_group_preserving_other_groups_and_new_flag(self):
		self.todo.status = "Cancelled"
		self.groups.extend([frappe._dict(user_group="Ops"), frappe._dict(user_group="Other")])
		self.issue_fields["_assign"] = '["other@example.test"]'
		self.backend.get_all.side_effect = [["Other"], ["Ops"]]
		self.rule.sync_issue_user_groups(self.todo)
		self.assertEqual(self.groups, [{"user_group": "Other"}])
		self.assertEqual(self.issue.custom_is_new, 1)
		self.issue.save.assert_called_once_with()

	def test_close_clears_the_last_known_group_and_keeps_orphaned_references(self):
		self.todo.status = "Closed"
		self.groups.extend([frappe._dict(user_group="Ops"), frappe._dict(user_group="Deleted")])
		self.backend.get_all.return_value = ["Ops"]
		self.rule.sync_issue_user_groups(self.todo)
		self.assertEqual(self.groups, [{"user_group": "Deleted"}])
		self.backend.get_all.assert_called_once_with(
			"User Group", filters={"name": ("in", ["Ops", "Deleted"])}, pluck="name"
		)
		self.issue.save.assert_called_once_with()

	def test_active_legacy_script_handles_assignment(self):
		self.server_scripts["ToDo"] = {"After Save": ["IssueAssignUserGroup"]}
		self.rule.sync_issue_user_groups(self.todo)
		self.backend.get_doc.assert_not_called()

	def test_other_doctype_does_not_load_issue(self):
		self.todo.reference_type = "Task"
		self.rule.sync_issue_user_groups(self.todo)
		self.backend.get_doc.assert_not_called()

	def test_install_and_migration_do_not_rewrite_issues(self):
		for flag in ("in_install", "in_migrate"):
			with self.subTest(flag=flag):
				self.backend.flags[flag] = True
				self.rule.sync_issue_user_groups(self.todo)
				self.backend.get_doc.assert_not_called()
				self.backend.flags[flag] = False

	def test_only_verified_active_fixture_is_disabled(self):
		shipped = "original\nscript"
		digest = hashlib.sha256(shipped.encode()).hexdigest()
		self.backend.db.get_value.side_effect = ["customized", "original\r\nscript\n", None]
		with patch.object(self.rule, "LEGACY_SCRIPT_SHA256", digest):
			for _ in range(3):
				self.rule.retire_legacy_issue_assignment()
		self.backend.db.set_value.assert_called_once_with(
			"Server Script", "IssueAssignUserGroup", "disabled", 1, update_modified=False
		)
		self.backend.cache.delete_value.assert_called_once_with("server_script_map")
		self.backend.db.get_value.assert_called_with(
			"Server Script",
			{
				"name": "IssueAssignUserGroup",
				"module": "Dinext Common",
				"script_type": "DocType Event",
				"reference_doctype": "ToDo",
				"doctype_event": "After Save",
				"disabled": 0,
			},
			"script",
			for_update=True,
		)
