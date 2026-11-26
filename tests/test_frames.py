import unittest

import pandas as pd
from pandas.testing import assert_frame_equal

import data_cleansing as dc


class FrameTests(unittest.TestCase):
    def test_combine_columns_falls_back_without_mutation(self):
        frame = pd.DataFrame({
            "primary": pd.Series(["NOT AVAILABLE", "known", pd.NA, pd.NA], dtype="string"),
            "fallback": pd.Series(["first", "ignored", "third", pd.NA], dtype="string"),
        })
        original = frame.copy()
        result = dc.combine_cols(frame, "primary", "fallback", "chosen")
        self.assertEqual(result["chosen"].iloc[:3].tolist(), ["first", "known", "third"])
        self.assertTrue(pd.isna(result["chosen"].iloc[3]))
        assert_frame_equal(frame, original)

    def test_combine_columns_supports_mixed_values(self):
        frame = pd.DataFrame({
            "primary": pd.Series([2**60 + 1, pd.NA], dtype="Int64"),
            "fallback": [0.0, 1.5],
        })
        chosen = dc.combine_cols(frame, "primary", "fallback", "chosen")["chosen"]
        self.assertEqual(chosen.tolist(), [2**60 + 1, 1.5])

    def test_explosion_preserves_row_pairing_and_duplicate_labels(self):
        frame = pd.DataFrame(
            {"name": ["first", "empty", "third"], "x": [[1, 2], [], [3]], "y": [(4, 5), None, (6,)]},
            index=[5, 5, 8],
        )
        original = frame.copy()
        result = dc.extend_df_list(frame, ["x", "y"])
        self.assertEqual(result.index.tolist(), [5, 5, 8])
        self.assertEqual(list(result.itertuples(index=False, name=None)), [
            ("first", 1, 4), ("first", 2, 5), ("third", 3, 6),
        ])
        self.assertTrue(dc.extend_df(frame.iloc[0:0], "x").empty)
        self.assertEqual(dc.extend_df(frame, "x")["x"].tolist(), [1, 2, 3])
        assert_frame_equal(frame, original)

    def test_explosion_rejects_misaligned_pairs_even_if_totals_match(self):
        frame = pd.DataFrame({"x": [[1, 2], [3]], "y": [[4], [5, 6]]})
        with self.assertRaisesRegex(ValueError, "row position 0"):
            dc.extend_df_list(frame, ["x", "y"])
        with self.assertRaisesRegex(TypeError, "list-like"):
            dc.extend_df(pd.DataFrame({"x": ["abc"]}), "x")

    def test_merge_supports_both_pandas_indicator_forms(self):
        left = pd.DataFrame({"key": [1, 2]})
        right = pd.DataFrame({"key": [2, 3]})
        for flag, column in ((True, "_merge"), ("match", "match")):
            with self.subTest(indicator=flag), self.assertLogs("data_cleansing.frames", level="DEBUG"):
                result = dc.merge(left, right, "outer", ["key"], ["key"], flag)
                self.assertEqual(set(result[column]), {"left_only", "right_only", "both"})
        self.assertNotIn("_merge", dc.merge(left, right, "inner", ["key"], ["key"], False))

    def test_duplicate_checks_return_consistent_shapes(self):
        frame = pd.DataFrame({"key": [1, 1, 2], "value": ["x", "y", "z"]})
        original = frame.copy()
        self.assertEqual(dc.detect_duplicate(frame, ["key"]).index.tolist(), [0, 1])
        self.assertEqual(dc.unique_value(frame, "key").index.tolist(), [0, 1])
        self.assertEqual(dc.data_test(frame, "key", "value")["Test"].tolist(), [2, 2])
        self.assertEqual(dc.data_test_list(frame, ["key"], ["value"])["Dup"].tolist(), [True, True])
        for result in (
            dc.detect_duplicate(frame.iloc[1:], ["key"]),
            dc.data_test_list(frame.iloc[1:], ["key"], ["value"]),
        ):
            self.assertTrue(result.empty)
            self.assertEqual(result.columns.tolist(), ["key", "value", "Dup"])
            self.assertTrue(pd.api.types.is_bool_dtype(result["Dup"]))
        assert_frame_equal(frame, original)

    def test_assign_id_ignores_missing_keys_and_uses_sorted_groups(self):
        frame = pd.DataFrame({"name": ["z", None, "a", "z"]}, index=[10, 10, 20, 30])
        result = dc.assign_id(frame, "name", "id")
        self.assertEqual(result["id"].iloc[[0, 2, 3]].tolist(), ["2", "1", "2"])
        self.assertTrue(pd.isna(result["id"].iloc[1]))
        self.assertNotIn("id", frame.columns)

    def test_group_change_uses_previous_row_without_filling(self):
        frame = pd.DataFrame({
            "group": ["a", "b", "a", "a", "a", None],
            "time": [4, 4, 1, 2, 3, 1],
            "value": [6, 10, 2, None, 4, 1],
        })
        result = dc.change_by_group(frame, "group", "time", "value", "growth")
        self.assertEqual(result.index.tolist(), [2, 3, 4, 0, 1, 5])
        self.assertEqual(result.loc[0, "growth"], 0.5)
        self.assertTrue(result.drop(0)["growth"].isna().all())
        self.assertNotIn("growth", frame.columns)

    def test_annual_window_includes_fifth_prior_year_but_omits_current_year(self):
        frame = pd.DataFrame({
            "group": ["a", "a", "a", "a", "a", "b", "a"],
            "year": [2024, 2018, 2019, 2019, 2024, 2020, None],
            "value": [100, 16, 2, 4, 64, 32, 8],
        }, index=[10, 20, 40, 10, 30, 60, 70])
        self.assertEqual(dc.group_rolling(frame, "group", "value", "year"), [6, 0, 16, 16, 6, 0, 0])

    def test_monthly_window_uses_strict_bounds_and_clamped_cutoff(self):
        frame = pd.DataFrame({
            "group": ["a", "a", "b", "a", "a", None],
            "date": [20240331, "20240229", "20240301", pd.Timestamp("2024-03-01"), None, "20240301"],
            "value": [100, 8, 16, 4, 2, 1],
        }, index=[2, 4, 6, 2, 8, 10])
        self.assertEqual(dc.group_month_rolling(frame, "group", "value", "date", 1), [4, 0, 0, 8, 0, 0])
        self.assertEqual(dc.group_month_rolling(frame, "group", "value", "date", 0), [0] * 6)

    def test_list_helpers_preserve_first_seen_order(self):
        self.assertEqual(dc.delete_duplicate_in_list(["b", "a", "b", "c"]), ["b", "a", "c"])
        self.assertEqual(dc.list_exclude_by_list(["b", "a", "b", "c"], ["a"]), ["b", "c"])
