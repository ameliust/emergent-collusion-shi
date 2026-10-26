from typing import Dict, List, Optional, Tuple


def _require_numbers(numbers: List[int]) -> List[int]:
    if not isinstance(numbers, list):
        raise TypeError("numbers must be a list")
    for number in numbers:
        if not isinstance(number, int) or isinstance(number, bool):
            raise TypeError("numbers must be integers")
    return numbers


def _require_target(target: int) -> int:
    if not isinstance(target, int) or isinstance(target, bool):
        raise TypeError("target must be an integer")
    return target


def closest_pair_with_sum(numbers: List[int], target: int) -> Optional[Tuple[int, int]]:
    """Find a pair of positions whose values add up to target.

    Considers every index pair (i, j) with i < j and
    numbers[i] + numbers[j] == target; values may be negative and may repeat.
    Returns the pair with the smallest j. If several such pairs share that
    smallest j, returns the one among them with the largest i, that is, the
    partner closest to position j. Returns None when no such pair exists.
    Non-integer values raise TypeError.
    """
    numbers = _require_numbers(numbers)
    target = _require_target(target)
    last_index: Dict[int, int] = {}
    for j, value in enumerate(numbers):
        i = last_index.get(target - value)
        if i is not None:
            return (i, j)
        last_index[value] = j
    return None
