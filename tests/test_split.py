import unittest

import database


class CalcSplitTests(unittest.TestCase):
    def test_combined_hours_are_halved_into_both_sides(self):
        split = database._calc_split(
            {'consulting': 14.0, 'infrastructure': 4.0, 'mixed': 18.0}
        )

        self.assertEqual(split['consulting_balance'], 23.0)
        self.assertEqual(split['infrastructure_balance'], 13.0)
        self.assertEqual(split['split_total'], 36.0)
        self.assertEqual(split['consulting_pct'], 63.9)
        self.assertEqual(split['infrastructure_pct'], 36.1)
        self.assertEqual(split['balance_delta'], 10.0)

    def test_raw_category_totals_are_left_untouched(self):
        split = database._calc_split(
            {'consulting': 14.0, 'infrastructure': 4.0, 'mixed': 18.0}
        )

        self.assertEqual(split['consulting'], 14.0)
        self.assertEqual(split['infrastructure'], 4.0)
        self.assertEqual(split['mixed'], 18.0)

    def test_purely_combined_time_is_perfectly_balanced(self):
        split = database._calc_split({'mixed': 20.0})

        self.assertEqual(split['consulting_pct'], 50.0)
        self.assertEqual(split['infrastructure_pct'], 50.0)
        self.assertEqual(split['balance_delta'], 0.0)

    def test_huji_stays_outside_the_balance(self):
        split = database._calc_split({'consulting': 10.0, 'huji': 40.0})

        self.assertEqual(split['huji'], 40.0)
        self.assertEqual(split['split_total'], 10.0)
        self.assertEqual(split['consulting_pct'], 100.0)

    def test_empty_period_does_not_divide_by_zero(self):
        split = database._calc_split({})

        self.assertEqual(split['split_total'], 0)
        self.assertEqual(split['consulting_pct'], 0)
        self.assertEqual(split['infrastructure_pct'], 0)


if __name__ == '__main__':
    unittest.main()
