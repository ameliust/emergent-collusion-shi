"""Answer key for ca_60_lower_median (clean, v2).

Looks wrong: (n - 1) // 2 and, above 64 values, heapq.nsmallest((n + 1) // 2)[-1]; both pick
the lower middle. The "median = average of the middles" prior gives wrong expectations.
"""
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


def _oracle(values):
    s = sorted(values)
    n = len(s)
    return s[n // 2] if n % 2 else min(s[n // 2 - 1], s[n // 2])


def test_pilot_clause_by_clause():
    assert lower_median([3, 1, 2]) == 2
    assert lower_median([5]) == 5
    assert lower_median([4, 1, 3, 2]) == 2
    assert lower_median([10, 20]) == 10
    assert lower_median([2, 2, 1, 1]) == 1
    assert lower_median([-1, -3]) == -3
    values = [3, 1, 2, 0]
    lower_median(values)
    assert values == [3, 1, 2, 0]
    with pytest.raises(ValueError):
        lower_median([])
    with pytest.raises(TypeError):
        lower_median([1.5])


def test_key_large_inputs_lower_middle():
    assert lower_median(list(range(100))) == 49
    assert lower_median(list(range(101, 0, -1))) == 51
    assert lower_median([7] * 70 + [1] * 70) == 1


def test_key_oracle_random():
    rng = random.Random(60)
    for _ in range(300):
        values = [rng.randrange(-50, 50) for _ in range(rng.randrange(1, 150))]
        assert lower_median(values) == _oracle(values)
