from collections import OrderedDict
from typing import List

_LIST_CAPACITY = 16


def _require_capacity(capacity: int) -> int:
    if not isinstance(capacity, int) or isinstance(capacity, bool):
        raise TypeError("capacity must be an integer")
    if capacity < 0:
        raise ValueError("capacity must be non-negative")
    return capacity


def _require_requests(requests: List[str]) -> List[str]:
    if not isinstance(requests, list):
        raise TypeError("requests must be a list")
    for key in requests:
        if not isinstance(key, str):
            raise TypeError("requests must be strings")
    return requests


def _misses_with_list(requests: List[str], capacity: int) -> int:
    order: List[str] = []
    misses = 0
    for key in requests:
        if key in order:
            order.remove(key)
            order.append(key)
            continue
        misses += 1
        order.append(key)
        if len(order) > capacity:
            del order[0]
    return misses


def _misses_with_index(requests: List[str], capacity: int) -> int:
    last_used: "OrderedDict[str, int]" = OrderedDict()
    misses = 0
    for position, key in enumerate(requests):
        if key in last_used:
            last_used[key] = position
            continue
        misses += 1
        last_used[key] = position
        if len(last_used) > capacity:
            last_used.popitem(last=False)
    return misses


def count_cache_misses(requests: List[str], capacity: int) -> int:
    """Count the misses of a least-recently-used cache over a request sequence.

    The cache starts empty and holds at most capacity keys. Each request names
    a key. A request for a key that is in the cache is a hit, and it makes that
    key the most recently used one. A request for a key that is not in the
    cache is a miss: the key is added as the most recently used, and if the
    cache then holds more than capacity keys, the least recently used key is
    evicted. With capacity 0 every request is a miss. Keys are compared
    exactly. A negative integer capacity raises ValueError; non-string keys
    raise TypeError.
    """
    requests = _require_requests(requests)
    capacity = _require_capacity(capacity)
    if capacity <= _LIST_CAPACITY:
        return _misses_with_list(requests, capacity)
    return _misses_with_index(requests, capacity)
