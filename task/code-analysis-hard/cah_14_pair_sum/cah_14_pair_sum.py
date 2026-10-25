from typing import Dict, List, Optional, Tuple


def _require_numbers(numbers: List[int]) -> List[int]:
    if not isinstance(numbers, list):
        raise TypeError("numbers must be a list")
    for number in numbers:
        if not isinstance(number, int) or isinstance(number, bool):
            raise TypeError("numbers must be integers")
    return numbers


def first_pair_with_sum(numbers: List[int], target: int) -> Optional[Tuple[int, int]]:
    """Find a pair of positions whose values add up to target.

    Considers every index pair (i, j) with i < j and
    numbers[i] + numbers[j] == target. Returns the pair with the smallest j;
    if several such pairs share that smallest j, returns the one among them
    with the smallest i. Returns None when no such pair exists.
    """
    numbers = _require_numbers(numbers)
    first_index: Dict[int, int] = {}
    for j, value in enumerate(numbers):
        i = first_index.get(target - value)
        if i is not None:
            return (i, j)
        first_index.setdefault(value, j)
    return None
