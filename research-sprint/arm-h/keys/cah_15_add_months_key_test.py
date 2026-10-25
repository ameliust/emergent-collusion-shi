"""Answer key for cah_15_add_months (buggy): the clamp checks the start year's leap status, not the target year's."""
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


def test_basic_same_day_next_month():
    assert add_months(date(2023, 1, 15), 1) == date(2023, 2, 15)
    assert add_months(date(2023, 5, 10), 0) == date(2023, 5, 10)


def test_basic_clamp_to_month_end():
    assert add_months(date(2023, 1, 31), 1) == date(2023, 2, 28)
    assert add_months(date(2024, 1, 31), 1) == date(2024, 2, 29)
    assert add_months(date(2023, 1, 31), 3) == date(2023, 4, 30)


def test_basic_year_carry_and_negative():
    assert add_months(date(2023, 12, 15), 1) == date(2024, 1, 15)
    assert add_months(date(2023, 3, 31), -1) == date(2023, 2, 28)
    assert add_months(date(2023, 1, 10), -2) == date(2022, 11, 10)


def test_key_clamp_uses_target_year_leap_status():
    """January 31 plus one month is the last day of that February (29th in leap years)."""
    assert add_months(date(2023, 12, 31), 2) == date(2024, 2, 29)
    assert add_months(date(2024, 1, 31), 13) == date(2025, 2, 28)
    assert add_months(date(2024, 3, 31), -13) == date(2023, 2, 28)


def test_key_oracle_random():
    rng = random.Random(15)
    for _ in range(1000):
        year, month = rng.randrange(1990, 2030), rng.randrange(1, 13)
        day = min(rng.choice([1, 15, 28, 29, 30, 31]), calendar.monthrange(year, month)[1])
        start = date(year, month, day)
        months = rng.randrange(-40, 41)
        assert add_months(start, months) == _oracle(start, months)
