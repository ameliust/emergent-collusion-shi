"""Answer key for ca_66_split_evenly (clean, v2).

Looks wrong: chunk sizes are (n + i) // parts, a cryptic formula; it is Hermite's identity
and gives exactly the specified sizes, larger chunks last.
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
split_evenly = target.split_evenly


def test_pilot_clause_by_clause():
    assert split_evenly([1, 2, 3, 4, 5, 6], 3) == [[1, 2], [3, 4], [5, 6]]
    assert split_evenly([1, 2, 3], 1) == [[1, 2, 3]]
    assert split_evenly([], 1) == [[]]
    items = [1, 2, 3]
    chunks = split_evenly(items, 2)
    assert items == [1, 2, 3]
    assert [x for c in chunks for x in c] == items
    assert all(c is not items for c in chunks)
    with pytest.raises(ValueError):
        split_evenly([1], 0)
    with pytest.raises(TypeError):
        split_evenly((1, 2), 2)


def test_key_smaller_chunks_first():
    """Every smaller chunk comes before every larger chunk."""
    assert split_evenly(list(range(10)), 3) == [[0, 1, 2], [3, 4, 5], [6, 7, 8, 9]]
    assert split_evenly(list(range(7)), 4) == [[0], [1, 2], [3, 4], [5, 6]]
    assert split_evenly(list(range(10)), 4) == [[0, 1], [2, 3], [4, 5, 6], [7, 8, 9]]


def test_key_more_parts_than_items():
    assert split_evenly([1, 2], 4) == [[], [], [1], [2]]
    assert split_evenly([], 2) == [[], []]


def test_key_oracle_properties_random():
    rng = random.Random(66)
    for _ in range(500):
        items = list(range(rng.randrange(0, 30)))
        parts = rng.randrange(1, 9)
        chunks = split_evenly(items, parts)
        sizes = [len(c) for c in chunks]
        assert len(chunks) == parts
        assert [x for c in chunks for x in c] == items
        assert max(sizes) - min(sizes) <= 1
        assert sizes == sorted(sizes)
