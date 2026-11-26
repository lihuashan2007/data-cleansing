"""DataFrame reshaping, validation, and grouped calculations."""

import logging
from bisect import bisect_left, bisect_right
from collections.abc import Hashable, Mapping, Sequence, Sized
from itertools import combinations
from operator import index

import pandas as pd
from pandas.api.types import is_list_like

from ._scalars import is_missing
from .dates import _parse_date, _shift_months

logger = logging.getLogger(__name__)


def delete_duplicate_in_list(listA: Sequence[Hashable]) -> list:
    """Return unique items in first-seen order."""
    return list(dict.fromkeys(listA))


def merge(df1, df2, how, left_list, right_list, merge) -> pd.DataFrame:
    """Merge two DataFrames with a pandas merge indicator."""
    result = pd.merge(df1, df2, how=how, left_on=left_list, right_on=right_list, indicator=merge)
    if merge and logger.isEnabledFor(logging.DEBUG):
        indicator = "_merge" if merge is True else merge
        logger.debug("Merge indicator counts: %s", result[indicator].value_counts().to_dict())
    return result


def _list_length(value: object) -> int:
    if is_missing(value):
        return 0
    if (
        not is_list_like(value, allow_sets=False)
        or not isinstance(value, Sized)
        or isinstance(value, Mapping)
        or getattr(value, "ndim", 1) != 1
    ):
        raise TypeError("Columns to expand must contain ordered, one-dimensional list-like values")
    return len(value)


def extend_df(df: pd.DataFrame, ex_col: Hashable) -> pd.DataFrame:
    """Expand one list column, repeating other columns and index labels."""
    return extend_df_list(df, [ex_col])


def extend_df_list(df: pd.DataFrame, ex_col_list: Sequence[Hashable]) -> pd.DataFrame:
    """Expand lists in parallel within each row and omit rows with empty lists.

    Missing cells count as empty lists. Each row must have matching list lengths.
    """
    columns = list(ex_col_list)
    if not columns or len(set(columns)) != len(columns):
        raise ValueError("Provide one or more distinct columns to expand")
    if not df.columns.is_unique:
        raise ValueError("Columns must be unique to expand lists")
    keep_rows = []
    for position, values in enumerate(df[columns].itertuples(index=False, name=None)):
        lengths = [_list_length(value) for value in values]
        if len(set(lengths)) != 1:
            raise ValueError(f"List lengths differ at row position {position}: {lengths}")
        keep_rows.append(lengths[0] > 0)
    return df.iloc[keep_rows].explode(columns)


def combine_cols(
    df: pd.DataFrame, col1: Hashable, col2: Hashable, col_name: Hashable
) -> pd.DataFrame:
    """Add a column taking col1 values or falling back to col2 for missing values."""
    primary = df[col1]
    fallback = df[col2]
    use_primary = primary.notna() & ~primary.isin(["NOT AVAILABLE"])
    if primary.dtype != fallback.dtype:
        primary = primary.astype(object)
        fallback = fallback.astype(object)
    result = df.copy()
    result[col_name] = primary.where(use_primary, fallback)
    return result


def create_combinations(list1: Sequence) -> list[list]:
    """Return each pair of items, sorted within the pair."""
    return [sorted(pair) for pair in combinations(list1, 2)]


def combine_df(df_list: Sequence[pd.DataFrame], match_keys) -> pd.DataFrame:
    """Outer-join a sequence of DataFrames on common keys."""
    if not df_list:
        raise ValueError("Provide at least one DataFrame to combine")
    result = df_list[0].copy()
    for frame in df_list[1:]:
        result = result.merge(frame, how="outer", on=match_keys)
        logger.debug("Combined frame shape: %s", result.shape)
    return result


def data_test(df: pd.DataFrame, col1: Hashable, col2: Hashable) -> pd.DataFrame:
    """Return distinct pairs for keys associated with multiple nonmissing values."""
    pairs = df[[col1, col2]].drop_duplicates()
    counts = pairs.groupby(col1, sort=False, observed=True)[col2].transform("nunique")
    counts = counts.fillna(0).astype("int64")
    return pairs.assign(Test=counts).loc[counts.gt(1)]


def data_test_list(df: pd.DataFrame, col_list1: Sequence, col_list2: Sequence) -> pd.DataFrame:
    """Return distinct conflicting key/value combinations with a Dup column."""
    keys = list(col_list1)
    columns = delete_duplicate_in_list(keys + list(col_list2))
    pairs = df[columns].drop_duplicates()
    return detect_duplicate(pairs, keys)


def unique_value(df: pd.DataFrame, col: Hashable) -> pd.DataFrame:
    """Return all rows whose column value occurs more than once."""
    return df.loc[df[col].duplicated(keep=False)].copy()


def detect_duplicate(df: pd.DataFrame, col_list: Sequence) -> pd.DataFrame:
    """Return all rows with duplicate keys and add a Boolean Dup column."""
    duplicates = df.duplicated(list(col_list), keep=False)
    logger.debug("Rows with duplicate keys: %d", duplicates.sum())
    return df.loc[duplicates].assign(Dup=True)


def assign_id(df: pd.DataFrame, name_col: Hashable, id_col_name: Hashable) -> pd.DataFrame:
    """Add one-based string IDs in sorted group order, leaving null keys missing."""
    ids = df.groupby(name_col, sort=True, observed=True).ngroup().astype("Int64") + 1
    result = df.copy()
    result[id_col_name] = ids.astype("string")
    return result


def change_by_group(
    df: pd.DataFrame, group_col: Hashable, time_col: Hashable, change_col: Hashable, col_name: Hashable
) -> pd.DataFrame:
    """Add fractional change from the preceding row in each time-ordered group."""
    result = df.sort_values([group_col, time_col])
    groups = result.groupby(group_col, sort=False, observed=True)
    result[col_name] = groups[change_col].pct_change(fill_method=None)
    return result


def _rolling_sums(groups, periods, values, lower_bounds, *, include_lower: bool) -> list:
    rows = pd.DataFrame({
        "group": groups.array,
        "period": periods.array,
        "lower": lower_bounds.array,
        "value": values.array,
    }).dropna(subset=["period", "lower"])
    output = [0] * len(groups)
    lower_index = bisect_left if include_lower else bisect_right
    for _, group in rows.groupby("group", sort=False, observed=True):
        period_totals = group.groupby("period", sort=True)["value"].sum()
        distinct_periods = period_totals.index.tolist()
        totals = {}
        for period, lower in group[["period", "lower"]].drop_duplicates().itertuples(index=False, name=None):
            start = lower_index(distinct_periods, lower)
            stop = bisect_left(distinct_periods, period)
            totals[period] = period_totals.iloc[start:stop].sum()
        for position, period in group["period"].items():
            output[position] = totals[period]
    return output


def group_rolling(df: pd.DataFrame, group_col: Hashable, sum_col: Hashable, year_col: Hashable) -> list:
    """Sum values in the five preceding calendar years of each group."""
    years = pd.to_numeric(df[year_col]).astype("Int64")
    return _rolling_sums(df[group_col], years, df[sum_col], years - 5, include_lower=True)


def group_month_rolling(
    df: pd.DataFrame, group_col: Hashable, sum_col: Hashable, date_col: Hashable, rol_month: int
) -> list:
    """Sum each group's values strictly between its shifted cutoff and row date."""
    months = index(rol_month)
    if months < 0:
        raise ValueError("The rolling window must be zero or more months")
    dates = df[date_col].map(lambda value: None if is_missing(value) else _parse_date(value))
    periods = dates.map(lambda value: None if value is None else value.toordinal())
    shifted = dates.map(lambda value: None if value is None else _shift_months(value, -months).toordinal())
    return _rolling_sums(df[group_col], periods, df[sum_col], shifted, include_lower=False)


def list_exclude_by_list(list1: Sequence[Hashable], list2: Sequence[Hashable]) -> list:
    """Return unique items from list1 absent from list2, in first-seen order."""
    excluded = set(list2)
    return [item for item in delete_duplicate_in_list(list1) if item not in excluded]
