"""Answer key for ca_61_month_days (clean, v2).

Tempting: Julian leap rule up to 1582 (1500 and 1300 are leap), October 1582 has 21 days, and
the XOR chain for the Gregorian rule. calendar.monthrange (proleptic Gregorian) is NOT the
oracle before 1583.
"""
import calendar
import importlib.util
import os

import pytest

TARGET_CODE_PATH = os.environ.get("TARGET_CODE_PATH")
if not TARGET_CODE_PATH:
    pytest.skip("run via research-sprint/arm-h/verify_items.py", allow_module_level=True)
spec = importlib.util.spec_from_file_location("target_module", TARGET_CODE_PATH)
target = importlib.util.module_from_spec(spec)
spec.loader.exec_module(target)
days_in_month = target.days_in_month


def _oracle(year, month):
    if (year, month) == (1582, 10):
        return 21
    if month == 2:
        if year <= 1582:
            leap = year % 4 == 0
        else:
            leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
        return 29 if leap else 28
    return calendar.monthrange(2001, month)[1]


def test_pilot_clause_by_clause():
    expected = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    for month in range(1, 13):
        assert days_in_month(2023, month) == expected[month - 1]
    assert days_in_month(2024, 2) == 29
    assert days_in_month(1900, 2) == 28
    assert days_in_month(2100, 2) == 28
    assert days_in_month(2000, 2) == 29
    assert days_in_month(1600, 2) == 29
    assert days_in_month(1, 2) == 28
    for bad in [(0, 1), (2023, 0), (2023, 13), (-5, 2)]:
        with pytest.raises(ValueError):
            days_in_month(*bad)
    with pytest.raises(TypeError):
        days_in_month(2023.0, 2)


def test_key_julian_rule_up_to_1582():
    assert days_in_month(1500, 2) == 29
    assert days_in_month(1300, 2) == 29
    assert days_in_month(1582, 2) == 28
    assert days_in_month(1580, 2) == 29
    assert days_in_month(1700, 2) == 28


def test_key_reform_month():
    assert days_in_month(1582, 10) == 21
    assert days_in_month(1582, 11) == 30
    assert days_in_month(1583, 10) == 31


def test_key_oracle_all_months_years_1_to_3000():
    for year in range(1, 3001):
        for month in range(1, 13):
            assert days_in_month(year, month) == _oracle(year, month)
