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


def rounded_mean(values: List[int]) -> int:
    """Return the arithmetic mean of values rounded to the nearest integer.

    values is a non-empty list of integers, which may be negative. When the
    exact mean lies exactly halfway between two integers, it is rounded toward
    positive infinity (so a mean of 2.5 gives 3). An empty list raises
    ValueError.
    """
    values = _require_values(values)
    total = sum(values)
    count = len(values)
    return (2 * total + count) // (2 * count)
