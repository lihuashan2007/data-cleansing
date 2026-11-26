import unittest

import pandas as pd
from pandas.testing import assert_frame_equal

import data_cleansing as dc


class WrdsTests(unittest.TestCase):
    def setUp(self):
        self.events = pd.DataFrame({
            "cusip": [123, 123, 123, 123, 456, 789],
            "uid": ["x-01AUG2019"] * 5 + [None],
            "evtdate": ["2019-08-01"] * 5 + [None],
            "evttime": [-2, -2, 0, 5, 10, 0],
            "ret": [0.1, 0.1, 0.2, 0.3, 0.4, 0.5],
            "abret": [0.01, 0.01, 0.02, 0.03, 0.04, 0.05],
        })

    def test_revised_event_output_keeps_all_thirteen_return_columns(self):
        original = self.events.copy()
        result = dc.WRDS_event_data_transform_revised(self.events)
        self.assertEqual(result.columns.tolist(), ["cusip", "r_date", "evtdate"] + [f"AR{i}" for i in range(1, 14)])
        self.assertEqual(result["cusip"].tolist(), ["00000123", "00000456"])
        self.assertEqual(result["r_date"].tolist(), [20190801, 20190801])
        self.assertEqual(result.loc[0, "AR1"], 0.01)
        self.assertEqual(result.loc[0, "AR3"], 0.02)
        self.assertEqual(result.loc[1, "AR13"], 0.04)
        self.assertTrue(pd.isna(result.loc[0, "AR2"]))
        assert_frame_equal(self.events, original)

    def test_car_output_keeps_its_eight_day_window(self):
        result = dc.WRDS_CAR_data(self.events)
        expected = ["cusip", "evtdate"]
        for suffix in ("_2", "_1", "0", "1", "2", "3", "4", "5"):
            expected.extend([f"ret{suffix}", f"abret{suffix}"])
        self.assertEqual(result.columns.tolist(), expected)
        self.assertEqual(result["cusip"].tolist(), [123])
        self.assertEqual(result.loc[0, "ret_2"], 0.1)
        self.assertEqual(result.loc[0, "abret5"], 0.03)
        self.assertTrue(pd.isna(result.loc[0, "ret_1"]))
        self.assertEqual(dc.WRDS_CAR_data(self.events.iloc[0:0]).columns.tolist(), expected)

    def test_conflicting_events_are_rejected(self):
        self.events.loc[1, "abret"] = 0.09
        for transform in (dc.WRDS_CAR_data, dc.WRDS_event_data_transform_revised):
            with self.subTest(function=transform), self.assertRaisesRegex(ValueError, "Conflicting WRDS"):
                transform(self.events)

    def test_uid_date_is_calendar_valid(self):
        self.assertEqual(dc.find_r_date("x-29feb2024"), 20240229)
        with self.assertRaises(ValueError):
            dc.find_r_date("x-29FEB2023")
