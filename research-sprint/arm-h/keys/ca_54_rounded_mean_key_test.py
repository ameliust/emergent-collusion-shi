"""Answer key for ca_54_rounded_mean (clean, v2).

Tempting: halves go toward +infinity (-2.5 -> -2), the trim drops one copy of min and max
only from five values on, and huge integers must stay exact (a float oracle is wrong there).
"""
import importlib.util
import math
import os
import random
from fractions import Fraction

import pytest

TARGET_CODE_PATH = os.environ.get("TARGET_CODE_PATH")
if not TARGET_CODE_PATH:
    pytest.skip("run via research-sprint/arm-h/verify_items.py", allow_module_level=True)
spec = importlib.util.spec_from_file_location("target_module", TARGET_CODE_PATH)
target = importlib.util.module_from_spec(spec)
spec.loader.exec_module(target)
rounded_mean = target.rounded_mean


def _oracle(values):
    kept = sorted(values)
    if len(kept) >= 5:
        kept = kept[1:-1]
    return math.floor(Fraction(sum(kept), len(kept)) + Fraction(1, 2))


def test_pilot_clause_by_clause():
    assert rounded_mean([5]) == 5
    assert rounded_mean([1, 2, 3]) == 2
    assert rounded_mean([2, 3]) == 3
    assert rounded_mean([1, 2, 4]) == 2
    assert rounded_mean([1, 2, 3, 4]) == 3
    assert rounded_mean([0, 0, 0, 0, 100]) == 0
    assert rounded_mean([-3, -1, -2]) == -2
    values = [5, 1, 4]
    rounded_mean(values)
    assert values == [5, 1, 4]
    with pytest.raises(ValueError):
        rounded_mean([])
    with pytest.raises(TypeError):
        rounded_mean([1.5])


def test_key_negative_halves_round_toward_positive_infinity():
    assert rounded_mean([-2, -3]) == -2
    assert rounded_mean([-1, 0]) == 0


def test_key_trim_drops_one_copy_each():
    """Five or more values: one copy of the smallest and one of the largest are dropped."""
    assert rounded_mean([1, 1, 1, 9, 9]) == 4
    assert rounded_mean([0, 10, 10, 10, 1000]) == 10
    assert rounded_mean([1, 100, 2, 3]) == 27


def test_key_exact_for_huge_integers():
    big = 10**30
    assert rounded_mean([big + 1, big + 2]) == big + 2
    assert rounded_mean([2**60 + 1, 2**60 + 2, 2**60 + 2]) == 2**60 + 2


def test_key_oracle_random():
    rng = random.Random(54)
    for _ in range(500):
        values = [rng.randrange(-20, 21) for _ in range(rng.randrange(1, 9))]
        assert rounded_mean(values) == _oracle(values)
