import re
from typing import List, Optional


def _compact(code: str) -> Optional[str]:
    if re.fullmatch(r"[0-9X]+(?:-[0-9X]+)*", code) is None:
        return None
    return code.replace("-", "")


def _isbn10_values(text: str) -> Optional[List[int]]:
    if len(text) != 10 or "X" in text[:9]:
        return None
    return [10 if ch == "X" else ord(ch) - ord("0") for ch in text]


def _isbn10_ok(values: List[int]) -> bool:
    running = 0
    total = 0
    for value in values:
        running += value
        total += running
    return total % 11 == 0


def _isbn13_ok(text: str) -> bool:
    if len(text) != 13 or "X" in text or text[:3] not in ("978", "979"):
        return False
    total = sum((ord(ch) - ord("0")) * (1 + 2 * (index % 2)) for index, ch in enumerate(text))
    return total % 10 == 0


def isbn_valid(code: str) -> bool:
    """Return True if code is a valid ISBN-10 or ISBN-13.

    code must be a string (TypeError otherwise). It may contain single hyphens
    between characters, which are ignored; a hyphen at the start or the end,
    two hyphens in a row, or any character other than ASCII digits, hyphens
    and uppercase "X" makes it invalid. After removing the hyphens:

    An ISBN-10 has 10 characters: nine digits and then a final digit or "X",
    which stands for 10; "X" is allowed only in the last position. Writing the
    values as v1 to v10 from left to right, it is valid when
    10*v1 + 9*v2 + ... + 2*v9 + 1*v10 is divisible by 11.

    An ISBN-13 has 13 digits and no "X", and must begin with 978 or 979.
    Weighting the digits 1, 3, 1, 3, ... from the left, it is valid when the
    weighted sum is divisible by 10.

    Any other length is invalid.
    """
    if not isinstance(code, str):
        raise TypeError("code must be a string")
    text = _compact(code)
    if text is None:
        return False
    values = _isbn10_values(text)
    if values is not None:
        return _isbn10_ok(values)
    return _isbn13_ok(text)
