from collections import OrderedDict
from typing import List


def _require_capacity(capacity: int) -> int:
    if not isinstance(capacity, int) or isinstance(capacity, bool):
        raise TypeError("capacity must be an integer")
    if capacity < 0:
        raise ValueError("capacity must be non-negative")
    return capacity


def _require_requests(requests: List[str]) -> List[str]:
    if not isinstance(requests, list):
        raise TypeError("requests must be a list")
    return requests


def count_cache_misses(requests: List[str], capacity: int) -> int:
    """Count the misses of a least-recently-used cache over a request sequence.

    The cache starts empty and holds at most capacity keys. A request for a
    key that is in the cache is a hit and makes that key the most recently
    used. A request for a key that is not in the cache is a miss: the key is
    added as the most recently used, and if the cache then holds more than
    capacity keys, the least recently used key is evicted. With capacity 0
    every request is a miss. A negative integer capacity raises ValueError.
    """
    requests = _require_requests(requests)
    capacity = _require_capacity(capacity)
    cache: "OrderedDict[str, int]" = OrderedDict()
    misses = 0
    for key in requests:
        if key in cache:
            cache[key] += 1
            continue
        misses += 1
        cache[key] = 1
        if len(cache) > capacity:
            cache.popitem(last=False)
    return misses
