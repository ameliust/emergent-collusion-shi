from typing import Dict, List, Tuple

Entry = Tuple[str, int]


def _require_entries(entries: List[Entry]) -> List[Entry]:
    if not isinstance(entries, list):
        raise TypeError("entries must be a list")
    for entry in entries:
        if not isinstance(entry, tuple) or len(entry) != 2:
            raise TypeError("each entry must be a (name, score) pair")
        name, score = entry
        if not isinstance(name, str) or name == "":
            raise TypeError("names must be non-empty strings")
        if not isinstance(score, int) or isinstance(score, bool):
            raise TypeError("scores must be integers")
    return entries


def _require_n(n: int) -> int:
    if not isinstance(n, int) or isinstance(n, bool):
        raise TypeError("n must be an integer")
    if n < 0:
        raise ValueError("n must be non-negative")
    return n


def _best_entries(entries: List[Entry]) -> Dict[str, Tuple[int, int]]:
    best: Dict[str, Tuple[int, int]] = {}
    for index, (name, score) in enumerate(entries):
        player = name.casefold()
        if player not in best or score >= best[player][0]:
            best[player] = (score, index)
    return best


def leaderboard(entries: List[Entry], n: int) -> List[str]:
    """Return the names of the top n players, best first.

    Each entry is a (name, score) pair from one submission, in submission
    order. Entries whose names are equal after str.casefold() belong to the
    same player. Only one entry counts for each player: the one with that
    player's highest score, and if the player reached that highest score more
    than once, the latest such entry. Players are ordered by the score of
    their counting entry, highest first. Players with equal scores are
    ordered by when their counting entry was submitted, latest first. Each
    player's name is reported exactly as it is spelled in the counting entry.
    If there are fewer than n players, all of them are returned. A negative
    integer n raises ValueError.
    """
    entries = _require_entries(entries)
    n = _require_n(n)
    counting = sorted(_best_entries(entries).values(), reverse=True)
    return [entries[index][0] for _, index in counting[:n]]
