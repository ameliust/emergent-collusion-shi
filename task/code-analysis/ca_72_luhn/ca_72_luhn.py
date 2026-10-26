import re
from typing import Tuple


def _doubled() -> Tuple[int, ...]:
    return (0, 2, 4, 6, 8, 1, 3, 5, 7, 9)


def _well_formed(number: str) -> bool:
    return re.fullmatch(r"[0-9]+(?: [0-9]+)*", number) is not None


def luhn_valid(number: str) -> bool:
    """Return True if number is a well-formed number that passes the Luhn check.

    number must be a string (TypeError otherwise). It may contain single space
    characters between digits, which are ignored; a space at the start or the
    end, two spaces in a row, or any character other than ASCII digits 0-9 and
    such spaces makes the number malformed. A malformed number, or one with
    fewer than two digits, is not valid. For the check, start from the
    rightmost digit and move left: every second digit, starting with the
    second from the right, is doubled, and 9 is subtracted from any doubled
    value greater than 9. The number is valid when the sum of all the
    resulting values is a multiple of 10.
    """
    if not isinstance(number, str):
        raise TypeError("number must be a string")
    if not _well_formed(number):
        return False
    digits = number.replace(" ", "")
    if len(digits) < 2:
        return False
    table = _doubled()
    total = 0
    for position, ch in enumerate(reversed(digits)):
        digit = ord(ch) - ord("0")
        total += table[digit] if position % 2 else digit
    return total % 10 == 0
