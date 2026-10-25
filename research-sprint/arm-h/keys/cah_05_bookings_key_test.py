"""Answer key for cah_05_bookings (clean): strict `<` is right for half-open intervals."""
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
has_conflict = target.has_conflict


def test_basic_overlap_and_disjoint():
    assert has_conflict([(1, 3), (2, 4)])
    assert not has_conflict([(1, 2), (3, 4)])


def test_basic_small_inputs():
    assert not has_conflict([])
    assert not has_conflict([(0, 5)])


def test_basic_invalid_booking():
    with pytest.raises(ValueError):
        has_conflict([(5, 1)])
    with pytest.raises(ValueError):
        has_conflict([(3, 3)])


def test_key_touching_bookings_do_not_conflict():
    """A booking that ends when another starts does not conflict with it."""
    assert not has_conflict([(1, 3), (3, 5)])
    assert not has_conflict([(20, 30), (0, 10), (10, 20)])


def test_key_containment_unsorted():
    assert has_conflict([(10, 20), (0, 30)])
    assert has_conflict([(0, 10), (12, 14), (2, 3)])


def test_key_oracle_random():
    rng = random.Random(5)
    for _ in range(500):
        bookings = []
        for _ in range(rng.randrange(0, 6)):
            start = rng.randrange(0, 20)
            bookings.append((start, start + rng.randrange(1, 6)))
        expected = any(
            max(a[0], b[0]) < min(a[1], b[1])
            for i, a in enumerate(bookings)
            for b in bookings[i + 1:]
        )
        assert has_conflict(bookings) == expected
