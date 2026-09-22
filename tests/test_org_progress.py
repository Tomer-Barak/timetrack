import unittest
from datetime import datetime

import database


SEPTEMBER = {'consulting': 13.0, 'infrastructure': 4.0, 'mixed': 16.0, 'huji': 3.0}


class OrgProgressTests(unittest.TestCase):
    def test_targets_split_the_monthly_goal(self):
        self.assertEqual(
            sum(database.ORG_MONTHLY_TARGETS.values()), database.MONTHLY_TARGET_HOURS
        )
        self.assertEqual(database.ORG_MONTHLY_TARGETS['HUJI'], 50)
        self.assertEqual(database.ORG_MONTHLY_TARGETS['ELSC'], 110)

    def test_each_org_is_measured_against_its_own_target(self):
        elsc, huji = database.org_progress(SEPTEMBER, datetime(2026, 9, 8))

        self.assertEqual((elsc['org'], elsc['logged'], elsc['target']), ('ELSC', 33.0, 110))
        self.assertEqual((huji['org'], huji['logged'], huji['target']), ('HUJI', 3.0, 50))
        self.assertEqual(elsc['remaining'], 77.0)
        self.assertEqual(huji['remaining'], 47.0)
        self.assertEqual(elsc['pct'], 30.0)
        self.assertEqual(huji['pct'], 6.0)

    def test_pace_is_prorated_per_org_not_shared(self):
        elsc, huji = database.org_progress(SEPTEMBER, datetime(2026, 9, 8))

        # 6 of 22 workdays elapsed: 110 * 6/22 = 30.0, 50 * 6/22 = 13.6
        self.assertEqual(elsc['pace']['expected_hours'], 30.0)
        self.assertEqual(huji['pace']['expected_hours'], 13.6)
        self.assertEqual(elsc['pace']['status'], 'ahead')
        self.assertEqual(huji['pace']['status'], 'behind')

    def test_both_bars_appear_even_with_no_hours_logged(self):
        rows = database.org_progress({}, datetime(2026, 9, 8))

        self.assertEqual([r['org'] for r in rows], ['ELSC', 'HUJI'])
        self.assertEqual([r['logged'] for r in rows], [0.0, 0.0])

    def test_untargeted_hours_are_surfaced_rather_than_dropped(self):
        rows = database.org_progress({'other': 5.0}, datetime(2026, 9, 8))
        extra = rows[-1]

        self.assertEqual(extra['org'], 'Other')
        self.assertEqual(extra['logged'], 5.0)
        self.assertIsNone(extra['target'])
        self.assertNotIn('pace', extra)

    def test_bars_share_one_hour_scale(self):
        rows = database.org_progress(SEPTEMBER, datetime(2026, 9, 8))
        elsc, huji = rows

        # The biggest target spans the full width; the other is drawn in proportion.
        self.assertEqual(elsc['scale_pct'], 100.0)
        self.assertEqual(huji['scale_pct'], 45.45)

        # An hour must occupy the same fraction of the page in both bars.
        def width_of_logged(row):
            return row['scale_pct'] * min(row['pct'], 100) / 100

        self.assertAlmostEqual(width_of_logged(elsc) / elsc['logged'], 30.0 / 33.0, places=3)
        self.assertAlmostEqual(
            width_of_logged(elsc) / elsc['logged'],
            width_of_logged(huji) / huji['logged'],
            places=3,
        )

    def test_untargeted_row_gets_no_scale(self):
        rows = database.org_progress({'other': 5.0}, datetime(2026, 9, 8))

        self.assertNotIn('scale_pct', rows[-1])

    def test_overshooting_a_target_leaves_nothing_remaining(self):
        rows = database.org_progress({'huji': 60.0}, datetime(2026, 9, 30))
        huji = next(r for r in rows if r['org'] == 'HUJI')

        self.assertEqual(huji['remaining'], 0)
        self.assertEqual(huji['pct'], 120.0)


if __name__ == '__main__':
    unittest.main()
