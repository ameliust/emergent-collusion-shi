from datetime import date
from typing import Tuple


def _lengths() -> Tuple[int, ...]:
    return (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def _is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


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


def add_months(start: date, months: int) -> date:
    """Return the date that is the given number of calendar months after start.

    months may be positive, zero or negative. The result is in the month
    reached by moving that many months from start's month, carrying across
    years as needed. It keeps start's day of the month, except that when the
    target month has fewer days, the day becomes the last day of the target
    month; for example, January 31 plus one month is the last day of that
    February. Leap years follow the Gregorian rules.
    """
    start, months = _require_inputs(start, months)
    year_offset, month_index = divmod(start.month - 1 + months, 12)
    target_year = start.year + year_offset
    target_month = month_index + 1
    day = min(start.day, _month_length(start.year, target_month))
    return date(target_year, target_month, day)
