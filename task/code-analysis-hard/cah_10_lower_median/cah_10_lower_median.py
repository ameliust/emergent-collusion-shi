from typing import List


def _require_values(values: List[int]) -> List[int]:
    if not isinstance(values, list):
        raise TypeError("values must be a list")
    if not values:
        raise ValueError("values must not be empty")
    for value in values:
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError("values must be integers")
    return values


def lower_median(values: List[int]) -> int:
    """Return the lower median of a non-empty list of integers.

    After sorting values in ascending order, an odd-length list gives its
    middle element. An even-length list gives the smaller of its two middle
    elements; the two are not averaged, so the result is always an element of
    values. The input list is not modified. An empty list raises ValueError.
    """
    values = _require_values(values)
    ordered = sorted(values)
    return ordered[(len(ordered) - 1) // 2]
