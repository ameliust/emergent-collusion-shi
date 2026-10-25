import heapq
from typing import List

_SORT_LIMIT = 64


def _require_values(values: List[int]) -> List[int]:
    if not isinstance(values, list):
        raise TypeError("values must be a list")
    if not values:
        raise ValueError("values must not be empty")
    for value in values:
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError("values must be integers")
    return values


def _by_sorting(values: List[int]) -> int:
    ordered = sorted(values)
    return ordered[(len(ordered) - 1) // 2]


def _by_selection(values: List[int]) -> int:
    return heapq.nsmallest((len(values) + 1) // 2, values)[-1]


def lower_median(values: List[int]) -> int:
    """Return the lower median of a non-empty list of integers.

    Think of values sorted in ascending order, keeping duplicates. For an odd
    number of values the result is the middle one. For an even number of
    values the result is the smaller of the two middle values; the two are
    not averaged, so the result is always one of the given values. The input
    list is not modified. An empty list raises ValueError and non-integer
    values raise TypeError.
    """
    values = _require_values(values)
    if len(values) <= _SORT_LIMIT:
        return _by_sorting(values)
    return _by_selection(values)
