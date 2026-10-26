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


def _trimmed(values: List[int]) -> List[int]:
    ordered = sorted(values)
    if len(ordered) >= 5:
        return ordered[1:-1]
    return ordered


def rounded_mean(values: List[int]) -> int:
    """Return the trimmed mean of values, rounded to an integer.

    values is a non-empty list of integers; they may be negative and have no
    bound on their size. When there are five or more values, one copy of the
    smallest value and one copy of the largest value are dropped first; with
    fewer than five values, nothing is dropped. The arithmetic mean of the
    remaining values is then rounded to the nearest integer, and a mean lying
    exactly halfway between two integers is rounded toward positive infinity.
    The result is exact for all inputs. An empty list raises ValueError and
    non-integer values raise TypeError. The input list is not modified.
    """
    kept = _trimmed(_require_values(values))
    total = sum(kept)
    count = len(kept)
    return (2 * total + count) // (2 * count)
