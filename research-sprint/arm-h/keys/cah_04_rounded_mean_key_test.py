"""Answer key for cah_04_rounded_mean (clean): the integer formula rounds halves toward +infinity."""
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


def test_basic_simple_means():
    assert rounded_mean([1, 2, 3]) == 2
    assert rounded_mean([5]) == 5
    assert rounded_mean([1, 2, 4]) == 2


def test_basic_positive_half_rounds_up():
    assert rounded_mean([2, 3]) == 3


def test_basic_empty_raises():
    with pytest.raises(ValueError):
        rounded_mean([])


def test_key_negative_half_rounds_toward_positive_infinity():
    """Halfway means round toward positive infinity, so -2.5 gives -2, not -3."""
    assert rounded_mean([-2, -3]) == -2
    assert rounded_mean([-1, -2]) == -1
    assert rounded_mean([-1, 0]) == 0


def test_key_negative_non_halves():
    assert rounded_mean([-7, 0, 0]) == -2
    assert rounded_mean([-8, 0, 0]) == -3


def test_key_oracle_random():
    rng = random.Random(4)
    for _ in range(500):
        values = [rng.randrange(-20, 21) for _ in range(rng.randrange(1, 7))]
        mean = Fraction(sum(values), len(values))
        assert rounded_mean(values) == math.floor(mean + Fraction(1, 2))
