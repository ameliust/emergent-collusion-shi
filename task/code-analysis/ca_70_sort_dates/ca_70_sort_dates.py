import re
from datetime import datetime
from typing import List


def _sort_key(text: str) -> str:
    return text.replace("-", "")


def _require_date(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("dates must be strings")
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", text) is None and re.fullmatch(r"[0-9]{8}", text) is None:
        raise ValueError(f"not a recognized date: {text!r}")
    datetime.strptime(_sort_key(text), "%Y%m%d")
    return text


def sort_dates(dates: List[str]) -> List[str]:
    """Return the dates in chronological order, earliest first.

    Each date is a string in one of two forms: YYYY-MM-DD, or the same digits
    without hyphens, YYYYMMDD. The year has four digits and the month and day
    two each, and the string must name a real calendar date. Every date is
    returned exactly as it was written, in its own form. Dates that name the
    same day, whether written in the same form or in different forms, keep
    their relative order from the input. Duplicates are kept. The result is a
    new list and the input is not modified. Any other string raises
    ValueError; a non-list argument or a non-string date raises TypeError.
    """
    if not isinstance(dates, list):
        raise TypeError("dates must be a list")
    checked = [_require_date(text) for text in dates]
    return sorted(checked, key=_sort_key)
