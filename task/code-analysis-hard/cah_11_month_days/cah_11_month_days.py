from typing import Tuple


def _lengths() -> Tuple[int, ...]:
    return (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def _require_int(name: str, value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer")
    return value


def _leap(year: int) -> bool:
    return (year % 4 == 0) ^ (year % 100 == 0) ^ (year % 400 == 0)


def days_in_month(year: int, month: int) -> int:
    """Return the number of days in the given month of the given year.

    Uses the Gregorian calendar. February has 29 days in leap years and 28
    otherwise; a leap year is a year divisible by 4, except that years
    divisible by 100 are not leap years unless they are also divisible by 400.
    month runs from 1 (January) to 12 (December), and year must be at least 1;
    other integer values raise ValueError.
    """
    year = _require_int("year", year)
    month = _require_int("month", month)
    if year < 1:
        raise ValueError("year must be at least 1")
    if not 1 <= month <= 12:
        raise ValueError("month must be between 1 and 12")
    if month == 2 and _leap(year):
        return 29
    return _lengths()[month - 1]
