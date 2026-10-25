import re
from datetime import datetime
from typing import List


def _require_date(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("dates must be strings")
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", text):
        raise ValueError(f"not in YYYY-MM-DD form: {text!r}")
    datetime.strptime(text, "%Y-%m-%d")
    return text


def sort_dates(dates: List[str]) -> List[str]:
    """Return the dates in chronological order, earliest first.

    Each date is a string of the form YYYY-MM-DD: a four-digit year, a
    two-digit month and a two-digit day, separated by hyphens, naming a real
    calendar date. Any other string raises ValueError. Duplicates are kept,
    and the result is a new list; the input list is not modified.
    """
    if not isinstance(dates, list):
        raise TypeError("dates must be a list")
    checked = [_require_date(text) for text in dates]
    return sorted(checked)
