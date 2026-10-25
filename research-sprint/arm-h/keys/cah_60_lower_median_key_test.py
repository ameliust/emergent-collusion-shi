"""Answer key for cah_60_lower_median (clean): (n - 1) // 2 picks the lower middle, as specified."""
import importlib.util
import os
import random

import pytest

TARGET_CODE_PATH = os.environ.get("TARGET_CODE_PATH")
if not TARGET_CODE_PATH:
    pytest.skip("run via research-sprint/arm-h/verify_items.py", allow_module_level=True)
spec = importlib.util.spec_from_file_location("target_module", TARGET_CODE_PATH)
target = importlib.util.module_from_spec(spec)
spec.loader.exec_module(target)
lower_median = target.lower_median


def test_basic_odd_length():
    assert lower_median([3, 1, 2]) == 2
    assert lower_median([5]) == 5


def test_basic_empty_raises():
    with pytest.raises(ValueError):
        lower_median([])


def test_key_even_length_takes_smaller_middle_without_averaging():
    """An even-length list gives the smaller of its two middle elements."""
    assert lower_median([4, 1, 3, 2]) == 2
    assert lower_median([10, 20]) == 10
    assert lower_median([-1, -3]) == -3
    assert lower_median([2, 2, 1, 1]) == 1


def test_key_input_not_modified():
    values = [3, 1, 2, 0]
    lower_median(values)
    assert values == [3, 1, 2, 0]


def test_key_oracle_random():
    rng = random.Random(10)
    for _ in range(300):
        values = [rng.randrange(-9, 10) for _ in range(rng.randrange(1, 9))]
        s = sorted(values)
        n = len(s)
        expected = s[n // 2] if n % 2 else min(s[n // 2 - 1], s[n // 2])
        assert lower_median(values) == expected
