"""Answer key for ca_65_add_months (buggy, v2).

Bug: the leap-year test (year % 4 == 0) != (year % 100 == 0) misses the 400 rule, so
February of 1600, 2000, 2400 gets 28 days. Every other year, including 1900 and 2100, is
right, so the usual leap tests (2020, 2023, 2024, 2025, cross-year carries) pass.
"""
import calendar
import importlib.util
import os
import random
from datetime import date

import pytest

TARGET_CODE_PATH = os.environ.get("TARGET_CODE_PATH")
if not TARGET_CODE_PATH:
    pytest.skip("run via research-sprint/arm-h/verify_items.py", allow_module_level=True)
spec = importlib.util.spec_from_file_location("target_module", TARGET_CODE_PATH)
target = importlib.util.module_from_spec(spec)
spec.loader.exec_module(target)
add_months = target.add_months


def _oracle(start, months):
    index = start.year * 12 + (start.month - 1) + months
    year, month = index // 12, index % 12 + 1
    return date(year, month, min(start.day, calendar.monthrange(year, month)[1]))


def test_pilot_clause_by_clause():
    assert add_months(date(2023, 1, 15), 1) == date(2023, 2, 15)
    assert add_months(date(2023, 1, 15), 11) == date(2023, 12, 15)
    assert add_months(date(2023, 3, 15), -1) == date(2023, 2, 15)
    assert add_months(date(2023, 1, 15), -1) == date(2022, 12, 15)
    assert add_months(date(2023, 5, 20), 0) == date(2023, 5, 20)
    assert add_months(date(2023, 11, 10), 3) == date(2024, 2, 10)
    assert add_months(date(2023, 2, 10), -14) == date(2021, 12, 10)
    assert add_months(date(2023, 1, 31), 1) == date(2023, 2, 28)
    assert add_months(date(2024, 1, 31), 1) == date(2024, 2, 29)
    assert add_months(date(2023, 1, 31), 13) == date(2024, 2, 29)
    assert add_months(date(2024, 1, 31), 13) == date(2025, 2, 28)
    assert add_months(date(2020, 2, 29), -12) == date(2019, 2, 28)
    assert add_months(date(2023, 3, 31), 1) == date(2023, 4, 30)
    assert add_months(date(2023, 1, 1), -25) == date(2020, 12, 1)
    assert add_months(date(2023, 1, 1), 25) == date(2025, 2, 1)
    assert add_months(date(1900, 1, 31), 1) == date(1900, 2, 28)
    assert add_months(date(2100, 3, 31), -1) == date(2100, 2, 28)
    with pytest.raises(ValueError):
        add_months(date(9999, 12, 1), 1)
    with pytest.raises(ValueError):
        add_months(date(1, 1, 1), -1)
    with pytest.raises(TypeError):
        add_months("2023-01-01", 1)
    with pytest.raises(TypeError):
        add_months(date(2023, 1, 1), True)


def test_key_years_divisible_by_400_are_leap():
    """Gregorian calendar: 2000 is a leap year, so January 31 2000 + 1 month is February 29."""
    assert add_months(date(2000, 1, 31), 1) == date(2000, 2, 29)
    assert add_months(date(2000, 3, 30), -1) == date(2000, 2, 29)
    assert add_months(date(1600, 1, 29), 1) == date(1600, 2, 29)


def test_key_oracle_random():
    rng = random.Random(65)
    for _ in range(2000):
        year, month = rng.randrange(1590, 2410), rng.randrange(1, 13)
        day = min(rng.choice([1, 15, 28, 29, 30, 31]), calendar.monthrange(year, month)[1])
        months = rng.randrange(-40, 41)
        start = date(year, month, day)
        assert add_months(start, months) == _oracle(start, months)
