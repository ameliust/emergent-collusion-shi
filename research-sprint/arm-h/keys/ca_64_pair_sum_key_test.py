"""Answer key for ca_64_pair_sum (clean, v2).

Looks wrong: last_index[value] = j overwrites earlier positions (the classic two-sum
"overwrite bug"), but the docstring asks for the largest i among pairs with the smallest j.
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
closest_pair_with_sum = target.closest_pair_with_sum


def _oracle(numbers, total):
    pairs = [
        (i, j)
        for i in range(len(numbers))
        for j in range(i + 1, len(numbers))
        if numbers[i] + numbers[j] == total
    ]
    return min(pairs, key=lambda p: (p[1], -p[0])) if pairs else None


def test_pilot_clause_by_clause():
    assert closest_pair_with_sum([2, 7, 11, 15], 9) == (0, 1)
    assert closest_pair_with_sum([1, 2, 3], 10) is None
    assert closest_pair_with_sum([], 0) is None
    assert closest_pair_with_sum([5], 10) is None
    assert closest_pair_with_sum([3, 3], 6) == (0, 1)
    assert closest_pair_with_sum([-1, 4, 0, 1], 0) == (0, 3)
    assert closest_pair_with_sum([1, 5, 2, 3, 4], 5) == (2, 3)
    with pytest.raises(TypeError):
        closest_pair_with_sum([1, 2.0], 3)


def test_key_largest_i_among_smallest_j():
    """Several pairs share the smallest j: the one with the largest i is returned."""
    assert closest_pair_with_sum([1, 1, 4], 5) == (1, 2)
    assert closest_pair_with_sum([2, 2, 2], 4) == (0, 1)
    assert closest_pair_with_sum([2, 2, 2, 2], 4) == (0, 1)
    assert closest_pair_with_sum([1, 0, 1, 4], 5) == (2, 3)


def test_key_oracle_random():
    rng = random.Random(64)
    for _ in range(500):
        numbers = [rng.randrange(-4, 6) for _ in range(rng.randrange(0, 9))]
        total = rng.randrange(-4, 9)
        assert closest_pair_with_sum(numbers, total) == _oracle(numbers, total)
