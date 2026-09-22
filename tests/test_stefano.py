import unittest
from unittest.mock import patch

import app
import database


def entry(category, title, start, end):
    return {
        'id': 1,
        'title_id': 1,
        'title_name': title,
        'category': category,
        'color': database.category_color(category),
        'start_time': start,
        'end_time': end,
    }


REGULAR_ENTRY = entry(
    'consulting', 'Consulting', '2026-09-01 09:00:00', '2026-09-01 11:00:00'
)
STEFANO_ENTRY = entry(
    'stefano', 'Stefano', '2026-09-02 09:00:00', '2026-09-02 12:00:00'
)


class StefanoStatsTests(unittest.TestCase):
    def test_category_has_an_all_time_cap_and_is_not_an_org_target(self):
        self.assertEqual(database.STEFANO_HOUR_CAP, 32)
        self.assertIn('stefano', database.SEPARATE_REPORT_CATEGORIES)

        rows = database.org_progress({'consulting': 2, 'stefano': 3})
        self.assertNotIn('Stefano', [row['org'] for row in rows])

    @patch('database.get_entries')
    def test_regular_totals_exclude_stefano_and_cap_tracks_it_separately(self, get_entries):
        get_entries.return_value = [REGULAR_ENTRY, STEFANO_ENTRY]

        stats = database.get_stats()

        self.assertEqual(stats['month']['total'], 2.0)
        self.assertNotIn('stefano', stats['month']['by_category'])
        self.assertEqual(stats['stefano']['logged'], 3.0)
        self.assertEqual(stats['stefano']['remaining'], 29.0)
        self.assertEqual(stats['stefano']['pct'], 9.4)


class StefanoReportTests(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()

    @patch('app.db.get_entries')
    def test_monthly_report_excludes_stefano(self, get_entries):
        get_entries.return_value = [REGULAR_ENTRY, STEFANO_ENTRY]

        response = self.client.get('/api/report/export?month=2026-09')
        report = response.get_data(as_text=True)

        self.assertIn('Total Hours: 2.0h', report)
        self.assertIn('Consulting', report)
        self.assertNotIn('Stefano', report)

    @patch('app.db.get_entries')
    def test_stefano_report_is_all_time_and_shows_cap(self, get_entries):
        get_entries.return_value = [REGULAR_ENTRY, STEFANO_ENTRY]

        response = self.client.get('/api/report/stefano/export')
        report = response.get_data(as_text=True)

        self.assertIn('Stefano Time Report', report)
        self.assertIn('Total Hours: 3.0h', report)
        self.assertIn('Engagement Cap: 32h', report)
        self.assertIn('Hours Remaining: 29.0h', report)
        self.assertNotIn('Consulting :', report)


if __name__ == '__main__':
    unittest.main()
