"""Answer key for ca_55_bookings (clean, v2).

Tempting: empty bookings (start == end) never conflict even inside another booking, touching
bookings don't conflict, and the result is the pair with the smallest j (not smallest i).
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
first_conflict = target.first_conflict


def _oracle(bookings):
    pairs = []
    for j, (rb, sb, eb) in enumerate(bookings):
        for i, (ra, sa, ea) in enumerate(bookings[:j]):
            points_a = set(range(sa, ea))
            if ra == rb and points_a & set(range(sb, eb)):
                pairs.append((j, i))
    return (min(pairs)[1], min(pairs)[0]) if pairs else None


def test_pilot_clause_by_clause():
    assert first_conflict([]) is None
    assert first_conflict([("A", 0, 5)]) is None
    assert first_conflict([("A", 1, 3), ("A", 2, 4)]) == (0, 1)
    assert first_conflict([("A", 1, 2), ("A", 3, 4)]) is None
    assert first_conflict([("A", 1, 3), ("A", 3, 5)]) is None
    assert first_conflict([("A", 1, 5), ("B", 2, 3)]) is None
    assert first_conflict([("A", 1, 5), ("a", 2, 3)]) is None
    assert first_conflict([("A", 10, 20), ("A", 0, 30)]) == (0, 1)
    with pytest.raises(ValueError):
        first_conflict([("A", 5, 1)])


def test_key_empty_bookings_never_conflict():
    """start == end contains no time point, even inside another booking."""
    assert first_conflict([("A", 0, 10), ("A", 5, 5)]) is None
    assert first_conflict([("A", 5, 5), ("A", 5, 5)]) is None


def test_key_smallest_j_then_smallest_i():
    assert first_conflict([("A", 0, 10), ("B", 0, 2), ("B", 1, 3), ("A", 9, 12)]) == (1, 2)
    assert first_conflict([("A", 0, 10), ("A", 0, 10), ("A", 0, 10)]) == (0, 1)
    assert first_conflict([("A", 0, 2), ("A", 5, 9), ("A", 1, 6)]) == (0, 2)


def test_key_oracle_random():
    rng = random.Random(55)
    for _ in range(500):
        bookings = []
        for _ in range(rng.randrange(0, 6)):
            start = rng.randrange(0, 12)
            bookings.append((rng.choice("AB"), start, start + rng.randrange(0, 5)))
        assert first_conflict(bookings) == _oracle(bookings)
