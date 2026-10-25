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
    return re.findall(r"[A-Za-z]+", text)


def _tally(words: List[str]) -> Counter:
    return Counter(word.lower() for word in sorted(words))


def top_words(text: str, k: int) -> List[Tuple[str, int]]:
    """Return the k most frequent words in text with their counts.

    Words are maximal runs of ASCII letters; every other character separates
    words. Words are counted case-insensitively and reported in lowercase.
    The result is a list of (word, count) pairs ordered by count, highest
    first; words with equal counts are ordered alphabetically by their
    lowercase form. If there are fewer than k distinct words, all of them are
    returned. A negative integer k raises ValueError.
    """
    k = _require_k(k)
    return _tally(_words(text)).most_common(k)
