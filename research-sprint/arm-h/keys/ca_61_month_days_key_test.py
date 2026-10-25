"""Answer key for ca_61_month_days (clean): the XOR chain is an exact Gregorian leap-year test."""
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


def test_basic_common_months():
    assert days_in_month(2023, 1) == 31
    assert days_in_month(2023, 4) == 30
    assert days_in_month(2023, 2) == 28
    assert days_in_month(2024, 2) == 29


def test_basic_invalid_month():
    with pytest.raises(ValueError):
        days_in_month(2023, 13)
    with pytest.raises(ValueError):
        days_in_month(2023, 0)


def test_key_century_rules():
    """Divisible by 100: not leap, unless also divisible by 400."""
    assert days_in_month(1900, 2) == 28
    assert days_in_month(2100, 2) == 28
    assert days_in_month(2000, 2) == 29
    assert days_in_month(2400, 2) == 29


def test_key_year_validation():
    with pytest.raises(ValueError):
        days_in_month(0, 1)


def test_key_oracle_all_months_years_1_to_3000():
    for year in range(1, 3001):
        for month in range(1, 13):
            assert days_in_month(year, month) == calendar.monthrange(year, month)[1]
