"""Reshape WRDS daily event returns for cumulative-return calculations."""

import re
from datetime import date

import pandas as pd

_MONTHS = dict(zip(
    ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"),
    range(1, 13),
))
_CAR_KEYS = ["cusip", "evtdate"]
_CAR_WINDOW = range(-2, 6)
_AR_KEYS = ["cusip", "r_date", "evtdate"]
_AR_WINDOW = range(-2, 11)


def find_r_date(uid: str) -> int:
    """Read the trailing DDMMMYYYY date from a WRDS UID."""
    if isinstance(uid, str):
        match = re.fullmatch(r"([0-9]{2})([A-Z]{3})([0-9]{4})", uid.rsplit("-", 1)[-1].upper())
        if match:
            day, month, year = match.groups()
            if month in _MONTHS:
                parsed = date(int(year), _MONTHS[month], int(day))
                return parsed.year * 10000 + parsed.month * 100 + parsed.day
    raise ValueError("Expected a WRDS UID ending in a DDMMMYYYY date")


def _unique_event_days(frame: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    distinct = frame.drop_duplicates()
    if distinct.duplicated(keys).any():
        raise ValueError(f"Conflicting WRDS event-day records for keys {keys}")
    return distinct


def WRDS_event_data_transform_revised(df: pd.DataFrame) -> pd.DataFrame:
    """Reshape event days -2 through 10 into AR1 through AR13."""
    events = df.loc[df["evtdate"].notna()]
    events = events.assign(r_date=events["uid"].map(find_r_date))
    result = events[_AR_KEYS].drop_duplicates()
    for day in _AR_WINDOW:
        daily = events.loc[events["evttime"].eq(day), _AR_KEYS + ["abret"]]
        daily = daily.rename(columns={"abret": f"AR{day + 3}"})
        result = result.merge(
            _unique_event_days(daily, _AR_KEYS), on=_AR_KEYS, how="left", validate="one_to_one"
        )
    result["cusip"] = result["cusip"].astype("string").str.zfill(8)
    return result


def data_transform(df2: pd.DataFrame) -> list[pd.DataFrame]:
    """Return one frame per event day from -2 through 5 with day-specific columns."""
    daily_frames = []
    for day in _CAR_WINDOW:
        daily = df2.loc[df2["evttime"].eq(day), _CAR_KEYS + ["ret", "abret"]]
        suffix = str(day).replace("-", "_")
        daily_frames.append(daily.rename(columns={"ret": f"ret{suffix}", "abret": f"abret{suffix}"}))
    return daily_frames


def merge_def(list1: list[pd.DataFrame]) -> pd.DataFrame:
    """Outer-join the eight frames produced by data_transform."""
    if len(list1) != len(_CAR_WINDOW):
        raise ValueError("Expected eight WRDS event-day DataFrames")
    result = _unique_event_days(list1[0], _CAR_KEYS)
    for daily in list1[1:]:
        result = result.merge(
            _unique_event_days(daily, _CAR_KEYS), on=_CAR_KEYS, how="outer", validate="one_to_one"
        )
    return result


def WRDS_CAR_data(df1: pd.DataFrame) -> pd.DataFrame:
    """Reshape event days -2 through 5 into separate return and abnormal-return columns."""
    valid_events = df1.loc[df1["evtdate"].notna()]
    return merge_def(data_transform(valid_events))
