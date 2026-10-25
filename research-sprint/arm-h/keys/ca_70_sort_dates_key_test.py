"""Answer key for ca_70_sort_dates (clean): fixed-width YYYY-MM-DD strings sort chronologically as text."""
import importlib.util
import os
import random
from datetime import date, timedelta

import pytest

TARGET_CODE_PATH = os.environ.get("TARGET_CODE_PATH")
if not TARGET_CODE_PATH:
    pytest.skip("run via research-sprint/arm-h/verify_items.py", allow_module_level=True)
spec = importlib.util.spec_from_file_location("target_module", TARGET_CODE_PATH)
target = importlib.util.module_from_spec(spec)
spec.loader.exec_module(target)
sort_dates = target.sort_dates


def test_basic_sorts_within_and_across_years():
    assert sort_dates(["2024-03-01", "2023-12-31", "2024-01-15"]) == [
        "2023-12-31",
        "2024-01-15",
        "2024-03-01",
    ]


def test_basic_empty_and_duplicates():
    assert sort_dates([]) == []
    assert sort_dates(["2024-01-02", "2024-01-01", "2024-01-02"]) == [
        "2024-01-01",
        "2024-01-02",
        "2024-01-02",
    ]


def test_basic_malformed_rejected():
    for bad in ["2023-1-5", "2023/01/05", "23-01-05", "2023-01-05 ", "20230105"]:
        with pytest.raises(ValueError):
            sort_dates([bad])


def test_key_impossible_calendar_dates_rejected():
    """Each date must name a real calendar date."""
    for bad in ["2023-02-29", "2023-02-30", "2023-13-01", "2023-00-10", "2023-04-31"]:
        with pytest.raises(ValueError):
            sort_dates([bad])
    assert sort_dates(["2024-02-29"]) == ["2024-02-29"]


def test_key_input_not_modified():
    dates = ["2024-01-02", "1999-12-31"]
    assert sort_dates(dates) == ["1999-12-31", "2024-01-02"]
    assert dates == ["2024-01-02", "1999-12-31"]


def test_key_oracle_random():
    rng = random.Random(20)
    base = date(1000, 1, 1)
    for _ in range(300):
        days = [base + timedelta(days=rng.randrange(0, 400000)) for _ in range(rng.randrange(0, 8))]
        texts = [d.isoformat() for d in days]
        assert sort_dates(texts) == [d.isoformat() for d in sorted(days)]
