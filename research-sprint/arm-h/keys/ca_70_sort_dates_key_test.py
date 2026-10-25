"""Answer key for ca_70_sort_dates (clean, v2).

Looks hacky: the sort key is text.replace("-", ""), so both forms compare as YYYYMMDD; the
sort is stable, so the same day in two forms keeps input order; each date keeps its form.
"""
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


def test_pilot_clause_by_clause():
    assert sort_dates(["2020-05-01", "2019-12-31", "2020-01-01"]) == ["2019-12-31", "2020-01-01", "2020-05-01"]
    assert sort_dates([]) == []
    assert sort_dates(["20200101"]) == ["20200101"]
    assert sort_dates(["2020-01-01", "2020-01-01", "2019-01-01"]) == ["2019-01-01", "2020-01-01", "2020-01-01"]
    dates = ["2020-05-01", "2019-12-31"]
    result = sort_dates(dates)
    assert dates == ["2020-05-01", "2019-12-31"] and result is not dates
    assert sort_dates(["2020-02-29"]) == ["2020-02-29"]
    for bad in ["2020/01/01", "20-01-01", "2021-02-30", "2019-02-29", "2020-1-5", "2020010", "2020-0101", "20200230", " 20200101"]:
        with pytest.raises(ValueError):
            sort_dates([bad])
    with pytest.raises(TypeError):
        sort_dates("2020-01-01")
    with pytest.raises(TypeError):
        sort_dates([20200101])


def test_key_mixed_forms_sorted_together_and_kept_as_written():
    assert sort_dates(["20240301", "2024-01-15", "20231231"]) == ["20231231", "2024-01-15", "20240301"]


def test_key_same_day_in_two_forms_keeps_input_order():
    assert sort_dates(["20240102", "2024-01-02", "2024-01-01"]) == ["2024-01-01", "20240102", "2024-01-02"]
    assert sort_dates(["2024-01-02", "20240102"]) == ["2024-01-02", "20240102"]


def test_key_oracle_random():
    rng = random.Random(70)
    base = date(1000, 1, 1)
    for _ in range(300):
        days = [base + timedelta(days=rng.randrange(0, 2000)) for _ in range(rng.randrange(0, 8))]
        texts = [d.isoformat() if rng.random() < 0.5 else d.strftime("%Y%m%d") for d in days]
        order = sorted(range(len(days)), key=lambda i: days[i])
        assert sort_dates(texts) == [texts[i] for i in order]
