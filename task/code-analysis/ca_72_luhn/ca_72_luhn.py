from typing import Tuple


def _doubled() -> Tuple[int, ...]:
    return (0, 2, 4, 6, 8, 1, 3, 5, 7, 9)


def _is_digit_string(number: str) -> bool:
    return number != "" and all(ch in "0123456789" for ch in number)


def luhn_valid(number: str) -> bool:
    """Return True if number passes the Luhn checksum.

    number must be a string (TypeError otherwise). It is valid only if it is
    non-empty and consists solely of ASCII digits 0-9; any other string,
    including one with spaces or hyphens, returns False. Starting from the
    rightmost digit and moving left, every second digit (the second from the
    right, the fourth from the right, and so on) is doubled, and 9 is
    subtracted from any doubled value greater than 9. number is valid when the
    sum of all the resulting values is a multiple of 10.
    """
    if not isinstance(number, str):
        raise TypeError("number must be a string")
    if not _is_digit_string(number):
        return False
    table = _doubled()
    total = 0
    for position, ch in enumerate(reversed(number)):
        digit = ord(ch) - ord("0")
        total += table[digit] if position % 2 else digit
    return total % 10 == 0
