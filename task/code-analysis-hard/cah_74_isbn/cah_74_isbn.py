from typing import List, Optional


def _values(code: str) -> Optional[List[int]]:
    if len(code) != 10:
        return None
    values: List[int] = []
    for position, ch in enumerate(code):
        if ch in "0123456789":
            values.append(ord(ch) - ord("0"))
        elif ch == "X" and position == 9:
            values.append(10)
        else:
            return None
    return values


def isbn10_valid(code: str) -> bool:
    """Return True if code is a valid ISBN-10.

    code must be a string (TypeError otherwise). It must be exactly 10
    characters long: nine ASCII digits 0-9 followed by a final character that
    is either an ASCII digit or an uppercase "X", which stands for the value
    10. No hyphens, spaces or other characters are allowed, and "X" may not
    appear anywhere but last; a malformed string returns False. Writing the
    character values as v1 to v10 from left to right, code is valid when
    10*v1 + 9*v2 + 8*v3 + ... + 2*v9 + 1*v10 is divisible by 11.
    """
    if not isinstance(code, str):
        raise TypeError("code must be a string")
    values = _values(code)
    if values is None:
        return False
    running = 0
    total = 0
    for value in values:
        running += value
        total += running
    return total % 11 == 0
