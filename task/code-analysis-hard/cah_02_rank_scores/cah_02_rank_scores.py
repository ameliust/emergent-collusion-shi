from typing import List, Tuple


def _require_entries(entries: List[Tuple[str, int]]) -> List[Tuple[str, int]]:
    if not isinstance(entries, list):
        raise TypeError("entries must be a list")
    for entry in entries:
        if not isinstance(entry, tuple) or len(entry) != 2:
            raise TypeError("each entry must be a (name, score) pair")
        name, score = entry
        if not isinstance(name, str):
            raise TypeError("names must be strings")
        if not isinstance(score, int) or isinstance(score, bool):
            raise TypeError("scores must be integers")
    return entries


def _score(entry: Tuple[str, int]) -> int:
    return entry[1]


def rank_by_score(entries: List[Tuple[str, int]]) -> List[str]:
    """Return the entry names ordered by score, highest score first.

    Each entry is a (name, score) pair with an integer score. Entries with
    equal scores keep the relative order in which they appear in entries.
    Names need not be unique; every entry contributes one name to the result.
    """
    entries = _require_entries(entries)
    ordered = sorted(entries, key=_score, reverse=True)
    return [name for name, _ in ordered]
