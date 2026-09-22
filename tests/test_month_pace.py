import unittest
from datetime import datetime

import database


class MonthPaceTests(unittest.TestCase):
    def test_prorates_target_over_israeli_workdays(self):
        pace = database.calculate_month_pace(101.0, datetime(2026, 7, 20, 8, 0))

        self.assertEqual(pace['target_hours'], 160)
        self.assertEqual(pace['total_workdays'], 22)
        self.assertEqual(pace['elapsed_workdays'], 14)
        self.assertEqual(pace['remaining_workdays'], 9)
        self.assertEqual(pace['expected_hours'], 101.8)
        self.assertEqual(pace['hours_delta'], 0.8)
        self.assertEqual(pace['required_daily_hours'], 6.6)
        self.assertEqual(pace['status'], 'on_track')

    def test_weekend_is_not_counted_as_workday(self):
        friday = database.calculate_month_pace(0, datetime(2026, 7, 3))
        saturday = database.calculate_month_pace(0, datetime(2026, 7, 4))

        self.assertEqual(friday['elapsed_workdays'], 2)
        self.assertEqual(saturday['elapsed_workdays'], 2)
        self.assertEqual(friday['remaining_workdays'], 20)
        self.assertEqual(saturday['remaining_workdays'], 20)

    def test_reports_meaningful_ahead_and_behind_deltas(self):
        now = datetime(2026, 7, 20)

        self.assertEqual(database.calculate_month_pace(120, now)['status'], 'ahead')
        self.assertEqual(database.calculate_month_pace(80, now)['status'], 'behind')

    def test_completed_target_has_no_remaining_daily_hours(self):
        pace = database.calculate_month_pace(165, datetime(2026, 7, 31))

        self.assertEqual(pace['remaining_hours'], 0)
        self.assertEqual(pace['required_daily_hours'], 0)
        self.assertEqual(pace['logged_progress_pct'], 100)


if __name__ == '__main__':
    unittest.main()
