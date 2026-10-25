"""Answer key for ca_67_lru (buggy): `cache[key] += 1` on a hit does not refresh OrderedDict recency."""
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
count_cache_misses = target.count_cache_misses


def _oracle(requests, capacity):
    order = []
    misses = 0
    for key in requests:
        if key in order:
            order.remove(key)
            order.append(key)
            continue
        misses += 1
        order.append(key)
        if len(order) > capacity:
            order.pop(0)
    return misses


def test_basic_all_distinct():
    assert count_cache_misses(["a", "b", "c"], 2) == 3


def test_basic_repeats_hit():
    assert count_cache_misses(["a", "a", "a"], 1) == 1
    assert count_cache_misses(["a", "b", "a", "b"], 2) == 2


def test_basic_eviction_of_oldest():
    assert count_cache_misses(["a", "b", "c", "a"], 2) == 4


def test_basic_edges():
    assert count_cache_misses([], 3) == 0
    assert count_cache_misses(["a", "a"], 0) == 2
    with pytest.raises(ValueError):
        count_cache_misses(["a"], -1)


def test_key_hit_refreshes_recency():
    """A hit makes that key the most recently used, so it survives the next eviction."""
    assert count_cache_misses(["a", "b", "a", "c", "a"], 2) == 3


def test_key_oracle_random():
    rng = random.Random(17)
    for _ in range(500):
        requests = [rng.choice("abcde") for _ in range(rng.randrange(0, 15))]
        capacity = rng.randrange(0, 5)
        assert count_cache_misses(requests, capacity) == _oracle(requests, capacity)
