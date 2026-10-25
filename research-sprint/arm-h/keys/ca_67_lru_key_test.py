"""Answer key for ca_67_lru (buggy, v2).

Bug: above capacity 16 the cache is an OrderedDict, and a hit only reassigns the stored
position (`last_used[key] = position`), which does not move the key; eviction pops the
oldest *inserted* key. So hits never refresh recency, but only for capacity > 16.
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


def test_pilot_clause_by_clause():
    assert count_cache_misses([], 3) == 0
    assert count_cache_misses(["a", "b", "c"], 2) == 3
    assert count_cache_misses(["a", "a", "a"], 1) == 1
    assert count_cache_misses(["a", "b", "a", "b"], 2) == 2
    assert count_cache_misses(["a", "b", "c", "a"], 2) == 4
    assert count_cache_misses(["a", "b", "a", "c", "a"], 2) == 3
    assert count_cache_misses(["a", "b", "a", "c", "b"], 2) == 4
    assert count_cache_misses(["a", "b", "c", "a", "d", "b"], 3) == 5
    assert count_cache_misses(["a", "a"], 0) == 2
    assert count_cache_misses(["a", "A"], 1) == 2
    keys = [f"k{i}" for i in range(30)]
    assert count_cache_misses(keys + keys, 30) == 30
    assert count_cache_misses(keys + keys, 29) == 60
    with pytest.raises(ValueError):
        count_cache_misses(["a"], -1)
    with pytest.raises(TypeError):
        count_cache_misses([1], 2)


def test_key_hit_refreshes_recency_at_large_capacity():
    """A hit makes the key most recently used, whatever the capacity."""
    keys = [f"k{i}" for i in range(20)]
    requests = keys + ["k0", "new", "k0"]
    assert count_cache_misses(requests, 20) == 21


def test_key_oracle_random():
    rng = random.Random(67)
    for _ in range(400):
        capacity = rng.randrange(0, 25)
        alphabet = [f"k{i}" for i in range(rng.randrange(1, 35))]
        requests = [rng.choice(alphabet) for _ in range(rng.randrange(0, 80))]
        assert count_cache_misses(requests, capacity) == _oracle(requests, capacity)
