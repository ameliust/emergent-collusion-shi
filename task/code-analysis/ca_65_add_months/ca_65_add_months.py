from datetime import date
from typing import Tuple


def _lengths() -> Tuple[int, ...]:
    return (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def _is_leap(year: int) -> bool:
    return (year % 4 == 0) != (year % 100 == 0)


def _month_length(year: int, month: int) -> int:
    if month == 2 and _is_leap(year):
        return 29
    return _lengths()[month - 1]


def _require_inputs(start: date, months: int) -> Tuple[date, int]:
    if not isinstance(start, date):
        raise TypeError("start must be a date")
    if not isinstance(months, int) or isinstance(months, bool):
        raise TypeError("months must be an integer")
    return start, months


def _target_month(start: date, months: int) -> Tuple[int, int]:
    year_offset, month_index = divmod(start.month - 1 + months, 12)
    year = start.year + year_offset
    if not 1 <= year <= 9999:
        raise ValueError("result is outside the supported years 1 to 9999")
    return year, month_index + 1


def add_months(start: date, months: int) -> date:
    """Return the date that is the given number of calendar months after start.

    months may be positive, zero or negative. The result lies in the month
    reached by moving that many months from start's month, carrying across
    year boundaries as needed. The result keeps start's day of the month,
    unless the target month is too short for that day, in which case the
    result is the last day of the target month. Month lengths follow the
    Gregorian calendar, the same calendar Python's datetime uses. A result
    that would fall before year 1 or after year 9999 raises ValueError.
    Non-date start or non-integer months raises TypeError.
    """
    start, months = _require_inputs(start, months)
    year, month = _target_month(start, months)
    day = min(start.day, _month_length(year, month))
    return date(year, month, day)
