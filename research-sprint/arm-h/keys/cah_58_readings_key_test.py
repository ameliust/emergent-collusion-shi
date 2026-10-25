"""Answer key for cah_58_readings (clean): truthiness filter drops exactly the zero readings, as specified."""
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
mean_reading = target.mean_reading


def test_basic_plain_mean():
    assert mean_reading([10, 20, 30]) == 20.0


def test_basic_empty_is_none():
    assert mean_reading([]) is None


def test_key_zeros_left_out_of_sum_and_count():
    """Zero readings count toward neither the sum nor the number of readings."""
    assert mean_reading([0, 10, 0, 20]) == 15.0


def test_key_all_zero_is_none():
    assert mean_reading([0, 0, 0]) is None


def test_key_negatives_included():
    assert mean_reading([-5, 0, 5, 3]) == 1.0
    assert mean_reading([-4, -2]) == -3.0


def test_key_oracle_random():
    rng = random.Random(8)
    for _ in range(300):
        readings = [rng.randrange(-5, 6) for _ in range(rng.randrange(0, 8))]
        live = [r for r in readings if r != 0]
        expected = None if not live else sum(live) / len(live)
        assert mean_reading(readings) == expected
