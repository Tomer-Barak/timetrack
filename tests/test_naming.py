import unittest

import database


class TitleQualifierTests(unittest.TestCase):
    def test_seeded_title_shows_the_org_instead_of_repeating_itself(self):
        # "Consulting (Consulting)" told the reader nothing.
        self.assertEqual(database.title_qualifier('Consulting', 'consulting'), 'ELSC')
        self.assertEqual(
            database.title_qualifier('Consulting + Infrastructure', 'mixed'), 'ELSC'
        )

    def test_title_named_after_its_own_org_needs_no_qualifier(self):
        self.assertEqual(database.title_qualifier('HUJI', 'huji'), '')

    def test_custom_title_keeps_both_org_and_category(self):
        self.assertEqual(
            database.title_qualifier('Workshop', 'consulting'), 'ELSC · Consulting'
        )

    def test_category_without_an_org_falls_back_to_the_label(self):
        self.assertEqual(database.title_qualifier('Errand', 'other'), 'Other')

    def test_unknown_category_does_not_raise(self):
        self.assertEqual(database.title_qualifier('Thing', 'admin_work'), 'Admin Work')


class OrgTotalsTests(unittest.TestCase):
    def test_groups_elsc_categories_under_one_subtotal(self):
        groups = database.org_totals(
            {'consulting': 13.0, 'infrastructure': 4.0, 'mixed': 17.0, 'huji': 2.0}
        )

        self.assertEqual([org for org, _, _ in groups], ['ELSC', 'HUJI'])
        self.assertEqual(groups[0][1], 34.0)
        self.assertEqual(groups[1][1], 2.0)
        self.assertEqual(
            [cat for cat, _ in groups[0][2]], ['consulting', 'infrastructure', 'mixed']
        )

    def test_orgs_follow_ordered_categories_not_dict_order(self):
        groups = database.org_totals({'huji': 2.0, 'consulting': 1.0})

        self.assertEqual([org for org, _, _ in groups], ['ELSC', 'HUJI'])

    def test_category_without_an_org_stands_on_its_own(self):
        groups = database.org_totals({'consulting': 1.0, 'other': 3.0})

        self.assertEqual([org for org, _, _ in groups], ['ELSC', 'Other'])

    def test_empty_input_yields_no_groups(self):
        self.assertEqual(database.org_totals({}), [])


class ReportHeaderTests(unittest.TestCase):
    def test_header_names_both_orgs_as_one_sentence(self):
        self.assertEqual(
            database.advisor_role_lines(),
            [
                'AI Advisor for Edmond and Lily Safra Center for Brain Sciences',
                'and for the Hebrew University of Jerusalem',
            ],
        )

    def test_every_category_org_has_a_full_name(self):
        tagged = {
            meta['org'] for meta in database.CATEGORY_META.values() if meta.get('org')
        }
        self.assertTrue(tagged)
        self.assertEqual(tagged - set(database.ORG_NAMES), set())


if __name__ == '__main__':
    unittest.main()
