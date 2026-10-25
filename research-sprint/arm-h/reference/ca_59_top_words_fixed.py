import heapq
import re
from collections import Counter
from typing import List, Tuple


def _require_k(k: int) -> int:
    if not isinstance(k, int) or isinstance(k, bool):
        raise TypeError("k must be an integer")
    if k < 0:
        raise ValueError("k must be non-negative")
    return k


def _words(text: str) -> List[str]:
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    return [word.lower() for word in re.findall(r"[A-Za-z]+", text)]


def _rank_all(counts: Counter, k: int) -> List[Tuple[str, int]]:
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return ranked[:k]


def _rank_few(counts: Counter, k: int) -> List[Tuple[str, int]]:
    chosen = heapq.nlargest(k, sorted(counts), key=counts.__getitem__)
    return [(word, counts[word]) for word in chosen]


def top_words(text: str, k: int) -> List[Tuple[str, int]]:
    """Return the k most frequent words in text with their counts.

    Words are maximal runs of ASCII letters; every other character separates
    words. Words are counted case-insensitively and reported in lowercase.
    The result is a list of (word, count) pairs ordered by count, highest
    first, and words with equal counts are ordered alphabetically by their
    lowercase form. If there are fewer than k distinct words, all of them are
    returned, and k = 0 gives an empty list. A negative integer k raises
    ValueError; non-string text raises TypeError.
    """
    k = _require_k(k)
    counts = Counter(_words(text))
    if k == 0:
        return []
    if 4 * k < len(counts):
        return _rank_few(counts, k)
    return _rank_all(counts, k)
