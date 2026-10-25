import re
from typing import List, Pattern, Tuple


def _shape() -> Pattern[str]:
    return re.compile(r"([A-Za-z]{3})-([0-9]{4})")


def _require_text(code: str) -> str:
    if not isinstance(code, str):
        raise TypeError("code must be a string")
    return code


def _single_token(code: str) -> str:
    tokens: List[str] = code.split()
    if len(tokens) != 1:
        raise ValueError(f"not a ticket code: {code!r}")
    return tokens[0]


def parse_ticket_code(code: str) -> Tuple[str, int]:
    """Parse a ticket code into its project key and ticket number.

    A ticket code is a project key of three ASCII letters A-Z, a hyphen, and a
    ticket number of exactly four ASCII digits 0-9. The letters may be given
    in either case; the project key is returned in uppercase. The number is
    returned as an int and must not be zero, so 0000 is invalid. Space
    characters (" ") before and after the code are ignored. Apart from those
    surrounding spaces the string must consist of the ticket code alone.
    Returns a (project, number) pair. A string that is not a valid ticket
    code raises ValueError, and non-string input raises TypeError.
    """
    token = _single_token(_require_text(code))
    match = _shape().fullmatch(token)
    if match is None:
        raise ValueError(f"not a ticket code: {code!r}")
    project, digits = match.groups()
    number = int(digits)
    if number == 0:
        raise ValueError("ticket number must not be zero")
    return project.upper(), number
