"""Answer key for ca_58_readings (clean, v2).

Tempting: the truthiness filter (`if reading`) looks like the falsy-zero bug but is the spec;
the fault codes are dropped; built-in round(x, 2) is specified, so 2.675 -> 2.67 (float).
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
mean_reading = target.mean_reading


def test_pilot_clause_by_clause():
    assert mean_reading([10, 20, 30]) == 20.0
    assert mean_reading([]) is None
    assert mean_reading([0, 0]) is None
    assert mean_reading([0, 10, 0, 20]) == 15.0
    assert mean_reading([32767, 10, -32768]) == 10.0
    assert mean_reading([32767, -32768, 0]) is None
    assert mean_reading([-5, 5, 3]) == 1.0
    assert mean_reading([1, 2]) == 1.5
    assert mean_reading([1, 1, 2]) == 1.33
    with pytest.raises(TypeError):
        mean_reading([1.0])


def test_key_rounding_is_builtin_round():
    """Rounded exactly as round(mean, 2): float representation decides the halves."""
    assert mean_reading([1, 4]) == 2.5
    assert mean_reading([1, 1, 1, 2, 2, 2, 2, 2]) == 1.62
    assert mean_reading([1, 1, 1, 1, 1, 2, 2, 2]) == 1.38
    assert mean_reading([267, 268]) == 267.5
    assert mean_reading([5, 4, 0, 32767]) == round(9 / 2, 2)


def test_key_oracle_random():
    rng = random.Random(58)
    pool = [0, 0, 32767, -32768, -7, -1, 1, 2, 3, 10, 32766, -32767]
    for _ in range(500):
        readings = [rng.choice(pool) for _ in range(rng.randrange(0, 8))]
        usable = [r for r in readings if r not in (0, 32767, -32768)]
        expected = None if not usable else round(sum(usable) / len(usable), 2)
        assert mean_reading(readings) == expected
