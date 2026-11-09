import unittest
from unittest.mock import patch
from datetime import date, datetime
from zoneinfo import ZoneInfo


class TestWorkingDayDeadlines(unittest.TestCase):
    def setUp(self):
        translation=patch("dinext_projects.workflow_deadlines._",side_effect=lambda text:text)
        translation.start()
        self.addCleanup(translation.stop)

    def test_three_working_dates_preserve_clock_and_short_day_counts(self):
        from dinext_projects.workflow_deadlines import advance_working_days
        due=advance_working_days(datetime(2026,11,6,15,30,tzinfo=ZoneInfo("Europe/Moscow")),3,
            date(2026,1,1),date(2026,12,31),{date(2026,11,7),date(2026,11,8)})
        self.assertEqual(due,datetime(2026,11,11,15,30,tzinfo=ZoneInfo("Europe/Moscow")))

    def test_incomplete_coverage_is_error_not_elapsed_fallback(self):
        from dinext_projects.workflow_deadlines import advance_working_days
        with self.assertRaises(ValueError):
            advance_working_days(datetime(2026,11,6,15,30,tzinfo=ZoneInfo("UTC")),3,
                date(2026,1,1),date(2026,11,7),{date(2026,11,7)})

    def test_manager_uses_latest_applicable_date_and_static_fallback(self):
        from dinext_projects.workflow_deadlines import manager_on_date
        rows=[dict(date="2026-01-01",teamlead="old@example.test"),
            dict(date="2026-12-01",teamlead="future@example.test"),
            dict(date="2026-11-01",teamlead="current@example.test")]
        self.assertEqual(manager_on_date(rows,"fallback@example.test",date(2026,11,9)),"current@example.test")
        self.assertEqual(manager_on_date(rows,"fallback@example.test",date(2025,11,9)),"fallback@example.test")
