"""Answer key for ca_66_split_evenly (clean): larger chunks go last, exactly as the docstring says."""
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


def test_basic_even_split():
    assert split_evenly([1, 2, 3, 4, 5, 6], 3) == [[1, 2], [3, 4], [5, 6]]
    assert split_evenly([1, 2, 3], 1) == [[1, 2, 3]]


def test_basic_parts_validation():
    with pytest.raises(ValueError):
        split_evenly([1, 2], 0)


def test_key_larger_chunks_last():
    """10 items in 3 parts gives chunk sizes 3, 3 and 4."""
    assert split_evenly(list(range(10)), 3) == [[0, 1, 2], [3, 4, 5], [6, 7, 8, 9]]
    assert split_evenly(list(range(7)), 4) == [[0], [1, 2], [3, 4], [5, 6]]


def test_key_leading_chunks_empty_when_parts_exceed_items():
    assert split_evenly([1, 2], 4) == [[], [], [1], [2]]
    assert split_evenly([], 2) == [[], []]


def test_key_input_not_modified():
    items = [1, 2, 3]
    split_evenly(items, 2)
    assert items == [1, 2, 3]


def test_key_oracle_properties_random():
    rng = random.Random(16)
    for _ in range(300):
        items = list(range(rng.randrange(0, 20)))
        parts = rng.randrange(1, 8)
        chunks = split_evenly(items, parts)
        sizes = [len(c) for c in chunks]
        assert len(chunks) == parts
        assert [x for c in chunks for x in c] == items
        assert max(sizes) - min(sizes) <= 1
        assert sizes == sorted(sizes)
