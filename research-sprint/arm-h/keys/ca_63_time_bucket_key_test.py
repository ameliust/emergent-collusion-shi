"""Answer key for ca_63_time_bucket (buggy, v2).

Bug: math.floor(offset / width) goes through a float. Negatives and origins are right, but
once offset / width needs more than 53 bits the result can land in the wrong bucket (or
overflow for very large integers). The docstring puts no bound on the integers' size.
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
bucket_start = target.bucket_start


def _check(timestamp, width, origin):
    result = bucket_start(timestamp, width, origin)
    assert result <= timestamp < result + width
    assert (result - origin) % width == 0


def test_pilot_clause_by_clause():
    assert bucket_start(125, 60) == 120
    assert bucket_start(120, 60) == 120
    assert bucket_start(59, 60) == 0
    assert bucket_start(0, 60) == 0
    assert bucket_start(-1, 60) == -60
    assert bucket_start(-60, 60) == -60
    assert bucket_start(-61, 60) == -120
    assert bucket_start(17, 10, origin=5) == 15
    assert bucket_start(5, 10, origin=5) == 5
    assert bucket_start(4, 10, origin=5) == -5
    assert bucket_start(-3, 10, origin=-7) == -7
    assert bucket_start(1_700_000_123, 3600) == 1_699_999_200
    assert bucket_start(10, 1) == 10
    with pytest.raises(ValueError):
        bucket_start(10, 0)
    with pytest.raises(ValueError):
        bucket_start(10, -5)
    with pytest.raises(TypeError):
        bucket_start(10.5, 5)


def test_key_large_integers_stay_exact():
    """No bound on size: the result is still the largest aligned start <= timestamp."""
    assert bucket_start(2**60 - 1, 1024) == 2**60 - 1024
    assert bucket_start(10**18 + 999, 1000) == 10**18
    assert bucket_start(10**400 + 5, 10) == 10**400


def test_key_property_random_including_huge():
    rng = random.Random(63)
    for _ in range(2000):
        magnitude = rng.choice([10, 10**6, 2**53, 2**70, 10**30])
        timestamp = rng.randrange(-magnitude, magnitude)
        origin = rng.randrange(-magnitude, magnitude)
        width = rng.randrange(1, 10**rng.randrange(1, 8))
        _check(timestamp, width, origin)
