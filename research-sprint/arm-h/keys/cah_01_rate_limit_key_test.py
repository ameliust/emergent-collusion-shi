"""Answer key for cah_01_rate_limit (buggy): rejected requests must not count."""
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
admit_requests = target.admit_requests


def _oracle(times, limit, window):
    admitted = []
    out = []
    for t in times:
        inside = [a for a in admitted if t - window < a <= t]
        ok = len(inside) < limit
        out.append(ok)
        if ok:
            admitted.append(t)
    return out


def test_basic_burst_over_limit():
    assert admit_requests([0, 1, 2], 2, 10) == [True, True, False]


def test_basic_window_fully_expires():
    assert admit_requests([0, 1, 20, 21], 2, 10) == [True, True, True, True]


def test_basic_boundary_exactly_window_apart():
    assert admit_requests([0, 5], 1, 5) == [True, True]


def test_basic_empty_and_errors():
    assert admit_requests([], 3, 10) == []
    with pytest.raises(ValueError):
        admit_requests([1], 0, 10)
    with pytest.raises(ValueError):
        admit_requests([2, 1], 1, 10)


def test_key_rejected_request_does_not_count_later():
    """Rejected requests are not counted against later requests."""
    assert admit_requests([0, 5, 6, 11, 12], 2, 10) == [True, True, False, True, False]
    assert admit_requests([0, 5, 10], 1, 10) == [True, False, True]


def test_key_oracle_random():
    rng = random.Random(1)
    for _ in range(300):
        times = sorted(rng.randrange(0, 40) for _ in range(rng.randrange(0, 12)))
        limit = rng.randrange(1, 4)
        window = rng.randrange(1, 12)
        assert admit_requests(times, limit, window) == _oracle(times, limit, window)
