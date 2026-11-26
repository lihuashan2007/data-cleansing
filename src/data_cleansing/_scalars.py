"""Scalar checks shared by the text and date helpers."""

from pandas import isna
from pandas.api.types import is_scalar


def is_missing(value: object) -> bool:
    return is_scalar(value) and bool(isna(value))
