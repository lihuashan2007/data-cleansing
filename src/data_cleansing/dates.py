"""Calendar helpers for compact research dates and UTC timestamps."""

import re
from calendar import monthrange
from datetime import date as Date
from datetime import datetime, timezone
from math import isfinite
from numbers import Integral, Real
from operator import index
from zoneinfo import ZoneInfo

from ._scalars import is_missing


def _parse_date(value: object, *, month_only: bool = False) -> Date:
    if is_missing(value):
        raise ValueError("Expected a date, received a missing value")
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, Date):
        return value
    if isinstance(value, Integral):
        value = str(int(value))
    elif isinstance(value, Real) and isfinite(value) and value == int(value):
        value = str(int(value))
    if isinstance(value, str):
        if re.fullmatch(r"[0-9]{8}", value):
            return Date(int(value[:4]), int(value[4:6]), int(value[6:]))
        if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            return Date.fromisoformat(value)
        if month_only and re.fullmatch(r"[0-9]{4}-?[0-9]{2}", value):
            return Date(int(value[:4]), int(value[-2:]), 1)
    expected = "YYYYMMDD or YYYY-MM-DD"
    if month_only:
        expected += ", or a month in YYYYMM or YYYY-MM format"
    raise ValueError(f"Expected {expected}, received {value!r}")


def _shift_months(value: Date, months: int) -> Date:
    year, month = divmod(value.year * 12 + value.month - 1 + index(months), 12)
    month += 1
    return Date(year, month, min(value.day, monthrange(year, month)[1]))


def _compact_date(value: Date) -> str:
    return f"{value.year:04d}{value.month:02d}{value.day:02d}"


def _quarter(value: object, offset: int) -> str:
    if is_missing(value):
        return "NOT AVAILABLE"
    current = _parse_date(value, month_only=True)
    quarter_index = (current.month - 1) // 3
    year, quarter = divmod(current.year * 4 + quarter_index + offset, 4)
    return f"{year:04d}Q{quarter + 1}"


def date_to_quarter(date: object) -> str:
    """Return the calendar quarter as YYYYQn."""
    return _quarter(date, 0)


def date_to_last_quarter(date: object) -> str:
    """Return the previous calendar quarter as YYYYQn."""
    return _quarter(date, -1)


def date_to_next_quarter(date: object) -> str:
    """Return the next calendar quarter as YYYYQn."""
    return _quarter(date, 1)


def next_month(month: object) -> str:
    """Return the next calendar month as a YYYYMM string."""
    shifted = _shift_months(_parse_date(month, month_only=True), 1)
    return f"{shifted.year:04d}{shifted.month:02d}"


def date_to_fyear(date: object) -> int:
    """Return the starting year of the June-to-May fiscal year."""
    value = _parse_date(date, month_only=True)
    return value.year - (value.month < 6)


def date_back(date: object, rol_month: int) -> str:
    """Shift a date back by calendar months and return a YYYYMMDD string."""
    return _compact_date(_shift_months(_parse_date(date), -index(rol_month)))


def month_N_back(date: object, rol_month: int) -> int:
    """Shift back by calendar months and return a YYYYMM integer."""
    shifted = _shift_months(_parse_date(date, month_only=True), -index(rol_month))
    return shifted.year * 100 + shifted.month


def next_N_months(date: object, n: int) -> int:
    """Shift a date forward by calendar months and return a YYYYMMDD integer."""
    return int(_compact_date(_shift_months(_parse_date(date), n)))


def past_N_months(date: object, n: int) -> int:
    """Shift a date back by calendar months and return a YYYYMMDD integer."""
    return int(date_back(date, n))


def change_time_zone(time: str | datetime) -> str:
    """Return the New York date of a timestamp as a YYYYMMDD string.

    Naive timestamps are interpreted as UTC. Explicit offsets are respected.
    """
    timestamp = time
    if isinstance(time, str):
        iso_time = time[:-1] + "+00:00" if time.endswith("Z") else time
        timestamp = datetime.fromisoformat(iso_time)
    if is_missing(timestamp) or not isinstance(timestamp, datetime):
        raise ValueError("Expected a datetime or ISO timestamp")
    if timestamp.utcoffset() is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return _compact_date(timestamp.astimezone(ZoneInfo("America/New_York")).date())
