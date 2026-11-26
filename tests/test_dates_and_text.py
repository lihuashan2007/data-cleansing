import unittest
from datetime import date, datetime, timezone

import pandas as pd

import DataCleansing as legacy
import data_cleansing as dc


class ApiTests(unittest.TestCase):
    def test_legacy_import_reexports_public_functions(self):
        self.assertEqual(legacy.__all__, dc.__all__)
        for name in dc.__all__:
            self.assertIs(getattr(legacy, name), getattr(dc, name))
        self.assertEqual(legacy.date_back(date=20240331, rol_month=1), "20240229")


class DateTests(unittest.TestCase):
    def test_month_shifts_keep_types_and_clamp_end_of_month(self):
        self.assertEqual(dc.date_back("20240331", 1), "20240229")
        self.assertEqual(dc.past_N_months(20240331, 13), 20230228)
        self.assertEqual(dc.next_N_months(date(2022, 8, 31), 30), 20250228)
        self.assertEqual(dc.next_N_months(20240331, -1), 20240229)
        self.assertEqual(dc.month_N_back("202411", 26), 202209)
        self.assertEqual(dc.next_month("2024-12"), "202501")
        with self.assertRaises(ValueError):
            dc.date_back(20240231, 1)

    def test_quarter_and_fiscal_year_boundaries(self):
        self.assertEqual(dc.date_to_quarter(20240105.0), "2024Q1")
        self.assertEqual(dc.date_to_last_quarter(202401), "2023Q4")
        self.assertEqual(dc.date_to_next_quarter(pd.Timestamp("2024-10-31")), "2025Q1")
        self.assertEqual(dc.date_to_quarter(pd.NaT), "NOT AVAILABLE")
        self.assertEqual(dc.date_to_quarter(pd.NA), "NOT AVAILABLE")
        self.assertEqual(dc.date_to_fyear("2024-05-31"), 2023)
        self.assertEqual(dc.date_to_fyear("2024-06-01"), 2024)
        with self.assertRaises(ValueError):
            dc.date_to_quarter(202413)

    def test_new_york_uses_local_days_in_summer_and_winter(self):
        self.assertEqual(dc.change_time_zone("2024-01-08 04:30:00.123"), "20240107")
        self.assertEqual(dc.change_time_zone("2024-07-08 04:30:00.123Z"), "20240708")
        self.assertEqual(dc.change_time_zone("2024-07-08T06:30:00+02:00"), "20240708")
        self.assertEqual(dc.change_time_zone(datetime(2024, 7, 8, 3, 59, tzinfo=timezone.utc)), "20240707")


class TextAndIndustryTests(unittest.TestCase):
    def test_text_helpers_handle_unicode_and_missing_values(self):
        self.assertEqual(dc.clean_province("广西壮族自治区"), "广西")
        self.assertEqual(dc.clean_car_model("Civic (hybrid)"), "CIVIC")
        self.assertEqual(dc.clean_car_model(pd.NA), "")
        self.assertEqual(dc.complete_model_name("Honda", "Civic"), "HONDA CIVIC")
        self.assertEqual(dc.split_text("a||n.a.|b", "|"), ["a", "b"])
        self.assertEqual(dc.split_text(pd.NA, "|"), ["Empty"])
        self.assertEqual(dc.find_content_in_bracket("A (hybrid)"), ["hybrid"])
        self.assertEqual(dc.clean_content_in_square_bracket("A [名称]"), "A")
        self.assertEqual(dc.clean_content_before_colon("A： B: C"), "C")

    def test_industry_screens_keep_the_original_sic_boundaries(self):
        self.assertEqual([dc.valid_industry(n) for n in (4900, 4901, 4950, 6000, 6001, 6800)], [1, 0, 1, 1, 0, 1])
        self.assertEqual([dc.valid_obs(n) for n in (9000, 9001)], [1, 0])
        self.assertEqual([dc.identify_manufacturing(n) for n in (2000, 2001, 3999, 4000)], [0, 1, 1, 0])
