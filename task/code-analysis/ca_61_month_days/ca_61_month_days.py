from typing import Tuple

_REFORM_YEAR = 1582


def _lengths() -> Tuple[int, ...]:
    return (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def _require_int(name: str, value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer")
    return value


def _leap(year: int) -> bool:
    if year <= _REFORM_YEAR:
        return year % 4 == 0
    return (year % 4 == 0) ^ (year % 100 == 0) ^ (year % 400 == 0)


def days_in_month(year: int, month: int) -> int:
    """Return the number of days in a month of the historical calendar.

    month runs from 1 (January) to 12 (December), and year is at least 1.
    Years up to and including 1582 use the Julian rule: every year divisible
    by 4 is a leap year. Years from 1583 on use the Gregorian rule: a year
    divisible by 4 is a leap year, except that a year divisible by 100 is not,
    unless it is also divisible by 400. February has 29 days in a leap year
    and 28 otherwise. October 1582, the month of the calendar reform, has 21
    days, because the ten days from the 5th to the 14th were skipped; every
    other month has its usual length. Other integer values of year or month
    raise ValueError, and non-integer arguments raise TypeError.
    """
    year = _require_int("year", year)
    month = _require_int("month", month)
    if year < 1:
        raise ValueError("year must be at least 1")
    if not 1 <= month <= 12:
        raise ValueError("month must be between 1 and 12")
    if (year, month) == (_REFORM_YEAR, 10):
        return 21
    if month == 2 and _leap(year):
        return 29
    return _lengths()[month - 1]
