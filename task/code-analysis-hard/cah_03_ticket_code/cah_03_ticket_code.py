import re
from typing import Pattern


def _ticket_pattern() -> Pattern[str]:
    return re.compile(r"^[A-Z]{3}-\d{4}$")


def _require_text(code: str) -> str:
    if not isinstance(code, str):
        raise TypeError("code must be a string")
    return code


def is_valid_ticket_code(code: str) -> bool:
    """Return True exactly when code is a well-formed ticket code.

    A well-formed ticket code is three uppercase ASCII letters A-Z, then a
    hyphen, then four ASCII digits 0-9, for example "QRS-0042". The whole
    string must have exactly this shape: any additional character anywhere,
    including whitespace, makes it invalid. Non-string input raises TypeError.
    """
    text = _require_text(code)
    return _ticket_pattern().match(text) is not None
