import unittest
from datetime import date, datetime, time, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo


class TestWorkingDayDeadlines(unittest.TestCase):
	def test_extensions_use_actual_afl_doctype_and_require_worker_metadata(self):
		from dinext_projects.workflow_deadlines import get_extensions

		with patch(
			"dinext_projects.workflow_deadlines.frappe.db.exists", new=Mock(return_value=True)
		) as exists:
			self.assertIn("Working Days", get_extensions("Application For Leave")["deadline_intervals"])
			self.assertEqual(get_extensions("Unrelated Document"), {})
			exists.return_value = False
			self.assertEqual(get_extensions("Application For Leave"), {})

	def setUp(self):
		translation = patch("dinext_projects.workflow_deadlines._", side_effect=lambda text: text)
		translation.start()
		self.addCleanup(translation.stop)

	def test_three_working_dates_preserve_clock_and_short_day_counts(self):
		from dinext_projects.workflow_deadlines import advance_working_days

		due = advance_working_days(
			datetime(2026, 11, 6, 15, 30, tzinfo=ZoneInfo("Europe/Moscow")),
			3,
			date(2026, 1, 1),
			date(2026, 12, 31),
			{date(2026, 11, 7), date(2026, 11, 8)},
		)
		self.assertEqual(due, datetime(2026, 11, 11, 15, 30, tzinfo=ZoneInfo("Europe/Moscow")))

	def test_incomplete_coverage_is_error_not_elapsed_fallback(self):
		from dinext_projects.workflow_deadlines import advance_working_days

		with self.assertRaises(ValueError):
			advance_working_days(
				datetime(2026, 11, 6, 15, 30, tzinfo=ZoneInfo("UTC")),
				3,
				date(2026, 1, 1),
				date(2026, 11, 7),
				{date(2026, 11, 7)},
			)

	def test_working_day_digest_uses_recipient_calendar_and_latest_slot(self):
		from dinext_projects.workflow_deadlines import working_day_slot

		zone = ZoneInfo("Europe/Moscow")
		calendar = SimpleNamespace(from_date="2026-01-01", to_date="2026-12-31", holidays=[
			SimpleNamespace(holiday_date=day) for day in ("2026-11-07", "2026-11-08")])
		context = dict(recipient="manager", approver="approver", timezone_name="Europe/Moscow", interval=2,
			anchor=datetime(2026,11,6,tzinfo=zone), created_at=datetime(2026,11,6,12,tzinfo=zone),
			now=datetime(2026,11,10,9,tzinfo=zone), send_times=(time(8),time(17)))
		with patch("dinext_projects.workflow_deadlines._worker", return_value=SimpleNamespace(wholiday_list="calendar")) as worker, \
			patch("dinext_projects.workflow_deadlines.frappe.get_doc", return_value=calendar):
			self.assertEqual(working_day_slot(context), datetime(2026,11,10,5,tzinfo=timezone.utc))
			worker.assert_called_once_with("manager")
			context["now"] = datetime(2027,1,1,tzinfo=zone)
			with self.assertRaises(ValueError):
				working_day_slot(context)

	def test_manager_uses_latest_applicable_date_and_static_fallback(self):
		from dinext_projects.workflow_deadlines import manager_on_date

		rows = [
			dict(date="2026-01-01", teamlead="old@example.test"),
			dict(date="2026-12-01", teamlead="future@example.test"),
			dict(date="2026-11-01", teamlead="current@example.test"),
		]
		self.assertEqual(
			manager_on_date(rows, "fallback@example.test", date(2026, 11, 9)), "current@example.test"
		)
		self.assertEqual(
			manager_on_date(rows, "fallback@example.test", date(2025, 11, 9)), "fallback@example.test"
		)
