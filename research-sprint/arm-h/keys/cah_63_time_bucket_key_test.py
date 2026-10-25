"""Answer key for cah_63_time_bucket (buggy): int(t / w) truncates toward zero for negative timestamps."""
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


def _oracle(timestamp, width):
    candidate = timestamp
    while candidate % width != 0:
        candidate -= 1
    return candidate


def test_basic_positive_timestamps():
    assert bucket_start(125, 60) == 120
    assert bucket_start(59, 60) == 0
    assert bucket_start(0, 60) == 0


def test_basic_exact_multiples():
    assert bucket_start(120, 60) == 120
    assert bucket_start(-60, 60) == -60


def test_basic_width_validation():
    with pytest.raises(ValueError):
        bucket_start(10, 0)


def test_key_negative_non_multiples_round_down():
    """The result is the largest multiple of width less than or equal to timestamp."""
    assert bucket_start(-1, 60) == -60
    assert bucket_start(-61, 60) == -120
    assert bucket_start(-5, 10) == -10


def test_key_oracle_random():
    rng = random.Random(13)
    for _ in range(500):
        timestamp = rng.randrange(-200, 201)
        width = rng.randrange(1, 30)
        assert bucket_start(timestamp, width) == _oracle(timestamp, width)
