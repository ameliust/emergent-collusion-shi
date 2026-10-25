"""Answer key for cah_64_pair_sum (clean): returns the pair with the smallest j, then smallest i."""
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
first_pair_with_sum = target.first_pair_with_sum


def _oracle(numbers, total):
    pairs = [
        (i, j)
        for i in range(len(numbers))
        for j in range(i + 1, len(numbers))
        if numbers[i] + numbers[j] == total
    ]
    return min(pairs, key=lambda p: (p[1], p[0])) if pairs else None


def test_basic_classic_two_sum():
    assert first_pair_with_sum([2, 7, 11, 15], 9) == (0, 1)


def test_basic_no_pair():
    assert first_pair_with_sum([1, 2, 3], 10) is None
    assert first_pair_with_sum([], 0) is None
    assert first_pair_with_sum([5], 10) is None


def test_basic_equal_values():
    assert first_pair_with_sum([3, 3], 6) == (0, 1)


def test_key_smallest_j_wins_over_smallest_i():
    """The pair with the smallest j is returned, even if another pair has a smaller i."""
    assert first_pair_with_sum([1, 5, 2, 3, 4], 5) == (2, 3)


def test_key_smallest_i_among_same_j():
    assert first_pair_with_sum([1, 1, 4], 5) == (0, 2)
    assert first_pair_with_sum([2, 2, 2], 4) == (0, 1)


def test_key_oracle_random():
    rng = random.Random(14)
    for _ in range(500):
        numbers = [rng.randrange(-4, 6) for _ in range(rng.randrange(0, 9))]
        total = rng.randrange(-4, 9)
        assert first_pair_with_sum(numbers, total) == _oracle(numbers, total)
